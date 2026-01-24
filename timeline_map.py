"""Streamlit map: tick-by-tick visualization of dispatch on a tiny scenario.

Run:
    streamlit run timeline_map.py

Shows drivers and orders on a map with a time slider for baseline/sequential/combinatorial.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Dict, List

import streamlit as st
import pydeck as pdk

from src import config, utils
from src.models import Driver, DriverStatus, Order
from src.simulation import Simulation

# -----------------------------------------------------------------------------
# Hard-coded scenario demonstrating bundling benefits
# Scenario: 5 orders, 3 drivers
# O1 & O2: Same restaurant (The Pearl), close deliveries → SHOULD BUNDLE
# O3: Nearby restaurant (Katara), separate delivery → MIGHT BUNDLE with O1/O2
# O4 & O5: Far restaurants (West Bay), separate area → separate driver
# -----------------------------------------------------------------------------
ORDERS: List[Order] = [
    # Order 1: The Pearl restaurant to nearby customer
    Order(
        order_id="O1",
        pickup_lat=25.3713,
        pickup_lng=51.5373,
        dropoff_lat=25.3650,
        dropoff_lng=51.5420,
        created_time=datetime.strptime("17:00:00", "%H:%M:%S").time(),
        deadline=datetime.strptime("17:45:00", "%H:%M:%S").time(),
        estimated_delivery_time_min=30,
    ),
    # Order 2: Same restaurant as O1, nearby delivery → BUNDLEABLE with O1
    Order(
        order_id="O2",
        pickup_lat=25.3715,  # 20m from O1 pickup
        pickup_lng=51.5375,
        dropoff_lat=25.3680,  # Close to O1 dropoff
        dropoff_lng=51.5410,
        created_time=datetime.strptime("17:01:00", "%H:%M:%S").time(),
        deadline=datetime.strptime("17:46:00", "%H:%M:%S").time(),
        estimated_delivery_time_min=30,
    ),
    # Order 3: Katara Cultural Village - 1.5km away, might bundle
    Order(
        order_id="O3",
        pickup_lat=25.3550,
        pickup_lng=51.5200,
        dropoff_lat=25.3500,
        dropoff_lng=51.5150,
        created_time=datetime.strptime("17:02:00", "%H:%M:%S").time(),
        deadline=datetime.strptime("17:47:00", "%H:%M:%S").time(),
        estimated_delivery_time_min=30,
    ),
    # Order 4: West Bay area - far from others
    Order(
        order_id="O4",
        pickup_lat=25.3200,
        pickup_lng=51.5300,
        dropoff_lat=25.3150,
        dropoff_lng=51.5250,
        created_time=datetime.strptime("17:04:00", "%H:%M:%S").time(),
        deadline=datetime.strptime("17:49:00", "%H:%M:%S").time(),
        estimated_delivery_time_min=30,
    ),
    # Order 5: Another West Bay order - should bundle with O4
    Order(
        order_id="O5",
        pickup_lat=25.3210,  # 100m from O4
        pickup_lng=51.5310,
        dropoff_lat=25.3180,
        dropoff_lng=51.5280,
        created_time=datetime.strptime("17:05:00", "%H:%M:%S").time(),
        deadline=datetime.strptime("17:50:00", "%H:%M:%S").time(),
        estimated_delivery_time_min=30,
    ),
]

DRIVERS: List[Driver] = [
    # Driver 1: Near The Pearl (close to O1/O2)
    Driver(
        driver_id="D1",
        start_lat=25.3700,
        start_lng=51.5350,
        vehicle_type="motorbike",
        capacity=2,
        available_from=datetime.strptime("17:00:00", "%H:%M:%S").time(),
    ),
    # Driver 2: Near Katara (close to O3)
    Driver(
        driver_id="D2",
        start_lat=25.3540,
        start_lng=51.5180,
        vehicle_type="motorbike",
        capacity=2,
        available_from=datetime.strptime("17:00:00", "%H:%M:%S").time(),
    ),
    # Driver 3: In West Bay (close to O4/O5)
    Driver(
        driver_id="D3",
        start_lat=25.3190,
        start_lng=51.5280,
        vehicle_type="motorbike",
        capacity=2,
        available_from=datetime.strptime("17:00:00", "%H:%M:%S").time(),
    ),
]


# -----------------------------------------------------------------------------
# Trace engine
# -----------------------------------------------------------------------------

def run_with_trace(strategy: str) -> List[Dict]:
    sim = Simulation(copy.deepcopy(DRIVERS), copy.deepcopy(ORDERS))
    timeline: List[Dict] = []

    while (
        sim.current_time < sim.end_time
        and len(sim.completed_missions) < len(sim.orders_map)
        and len(timeline) < 60
    ):
        sim._update_driver_states()
        sim._inject_new_orders()

        assigned_in_tick: List[str] = []
        distance_in_tick: float = 0.0

        if sim.pending_orders:
            should_dispatch = (strategy == "baseline") or sim._should_dispatch_batch()
            if should_dispatch:
                dispatch_orders = list(sim.pending_orders)
                if strategy == "baseline":
                    assigned_in_tick, distance_in_tick = sim.dispatch_engine.run_baseline(
                        sim.drivers, dispatch_orders, sim.current_time
                    )
                elif strategy == "sequential":
                    assigned_in_tick, distance_in_tick = sim.dispatch_engine.run_sequential(
                        sim.drivers, dispatch_orders, sim.current_time
                    )
                elif strategy == "combinatorial":
                    assigned_in_tick, distance_in_tick = sim.dispatch_engine.run_combinatorial(
                        sim.drivers, dispatch_orders, sim.current_time
                    )
                sim.batch_start_time = None

        sim.total_distance_traveled += distance_in_tick

        for order in assigned_in_tick:
            if order in sim.pending_orders:
                sim.pending_orders.remove(order)

        for driver in sim.drivers:
            if len(driver.assigned_orders) > 0 or driver.status != DriverStatus.IDLE:
                sim.drivers_activated.add(driver.driver_id)
                sim._record_driver_position(driver)

        driver_snap = []
        for d in sim.drivers:
            remaining_stops = []
            if d.route and 0 <= d.current_stop_index < len(d.route):
                remaining_stops = [f"{s.stop_type}:{s.order_id}" for s in d.route[d.current_stop_index:]]
            driver_snap.append(
                {
                    "id": d.driver_id,
                    "lat": d.current_lat,
                    "lng": d.current_lng,
                    "status": d.status.value,
                    "assigned": [o.order_id for o in d.assigned_orders],
                    "plan": remaining_stops,
                }
            )

        timeline.append(
            {
                "time": sim.current_time.strftime("%H:%M"),
                "assigned": [{"order": o.order_id, "driver": next((d.driver_id for d in sim.drivers if o in d.assigned_orders), "?")} for o in assigned_in_tick],
                "pending": [o.order_id for o in sim.pending_orders],
                "completed": [o.order_id for o in sim.orders_map.values() if o.status.name == "DELIVERED"],
                "in_progress": [o.order_id for o in sim.orders_map.values() if o.status.name != "DELIVERED" and o not in sim.pending_orders],
                "drivers": driver_snap,
            }
        )

        sim.current_time = utils.add_minutes_to_time(sim.current_time, config.SIMULATION_SPEED_MINUTES)

        if len(sim.completed_missions) >= len(sim.orders_map):
            break

    return timeline


@st.cache_data(show_spinner=False)
def get_timeline(strategy: str) -> List[Dict]:
    return run_with_trace(strategy)


# -----------------------------------------------------------------------------
# Map helpers
# -----------------------------------------------------------------------------

def driver_layer(drivers: List[Dict]) -> pdk.Layer:
    color_map = {
        "IDLE": [100, 116, 139],
        "ACCRUING": [59, 130, 246],
        "DELIVERING": [16, 185, 129],
    }
    data = [
        {
            "position": [d["lng"], d["lat"]],
            "status": d["status"],
            "color": color_map.get(d["status"], [148, 163, 184]),
            "label": d["id"],
        }
        for d in drivers
    ]
    return pdk.Layer(
        "ScatterplotLayer",
        data,
        get_position="position",
        get_fill_color="color",
        get_radius=90,
        pickable=True,
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
    )


def order_layer(orders: List[Order], pending_ids: List[str], completed_ids: List[str]) -> pdk.Layer:
    data = []
    for o in orders:
        if o.order_id in completed_ids:
            status = "completed"
            color = [16, 185, 129]
        elif o.order_id in pending_ids:
            status = "pending"
            color = [251, 191, 36]
        else:
            status = "in_flight"
            color = [59, 130, 246]
        data.append({"position": [o.pickup_lng, o.pickup_lat], "status": status, "label": f"{o.order_id} pickup", "color": color})
        data.append({"position": [o.dropoff_lng, o.dropoff_lat], "status": status, "label": f"{o.order_id} dropoff", "color": color})
    return pdk.Layer(
        "ScatterplotLayer",
        data,
        get_position="position",
        get_fill_color="color",
        get_radius=70,
        opacity=0.6,
        pickable=True,
    )


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Dispatch Map Timeline", page_icon="🗺️", layout="wide")
st.title("🗺️ Dispatch Timeline on a Map")
st.write("**Demo:** 5 orders / 3 drivers in Doha. Watch how different strategies bundle orders.")

strategy = st.radio("Strategy", ["baseline", "sequential", "combinatorial"], index=1, horizontal=True)

timeline = get_timeline(strategy)
if not timeline:
    st.error("No timeline produced.")
    st.stop()

max_tick = len(timeline) - 1
idx = st.slider("Tick", 0, max_tick, 0, help="Scrub through time (minutes)")
current = timeline[idx]

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown(f"**Time:** {current['time']}")
    if current["assigned"]:
        st.markdown("**Assignments this tick:**")
        for a in current["assigned"]:
            st.markdown(f"- {a['order']} → {a['driver']}")
    else:
        st.markdown("**Assignments this tick:** (none)")

with col2:
    st.markdown("**Order Status**")
    st.markdown(
        f"<div style='padding:0.75rem; background:#0f172a; color:#e2e8f0; border-radius:12px;'>"
        f"<b>Pending:</b> {', '.join(current['pending']) or '—'}<br>"
        f"<b>In-Flight:</b> {', '.join(current['in_progress']) or '—'}<br>"
        f"<b>Completed:</b> {', '.join(current['completed']) or '—'}"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("**Drivers & Plans**")
driver_cols = st.columns(len(current["drivers"]) or 1)
for i, d in enumerate(current["drivers"]):
    with driver_cols[i % len(driver_cols)]:
        st.markdown(
            f"<div style='padding:0.75rem; background:#0b1220; color:#e2e8f0; border-radius:12px; margin-bottom:0.5rem;'>"
            f"<b>{d['id']}</b> · {d['status']}<br>"
            f"<span style='color:#cbd5e1;'>Assigned:</span> {', '.join(d['assigned']) or '—'}<br>"
            f"<span style='color:#cbd5e1;'>Plan:</span> { ' → '.join(d['plan']) if d['plan'] else '—' }"
            f"</div>",
            unsafe_allow_html=True,
        )

center_lat = sum(o.pickup_lat for o in ORDERS) / len(ORDERS)
center_lng = sum(o.pickup_lng for o in ORDERS) / len(ORDERS)

view_state = pdk.ViewState(latitude=center_lat, longitude=center_lng, zoom=13)

layers = [
    order_layer(ORDERS, current["pending"], current["completed"]),
    driver_layer(current["drivers"]),
]

st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state, tooltip={"text": "{label}"}))

st.markdown("---")
st.markdown("#### Timeline Table")
rows = []
for step in timeline:
    rows.append(
        {
            "time": step["time"],
            "assigned": ", ".join(f"{a['order']}→{a['driver']}" for a in step["assigned"]) or "—",
            "pending": ", ".join(step["pending"]) or "—",
            "in_flight": ", ".join(step["in_progress"]) or "—",
            "completed": ", ".join(step["completed"]) or "—",
        }
    )
st.dataframe(rows, use_container_width=True, hide_index=True)
