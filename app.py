"""
Snoonu Smart Dispatch - Executive Dashboard
======================================

Dashboard for comparing dispatch strategies in last-mile delivery simulation.

Features:
- KPI comparison across strategies
- Folium maps with color-coded routes
- Strategy comparison tables
- Configurable simulation parameters
"""

import streamlit as st
import pandas as pd
import copy
import os
import sys
from typing import Dict, Any, List, Tuple, Optional

# Ensure src is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.simulation import Simulation
from src import config

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Snoonu Smart Dispatch",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM STYLING
# =============================================================================

st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        transition: transform 0.3s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-5px);
    }
    
    .kpi-card.green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 10px 40px rgba(17, 153, 142, 0.3);
    }
    
    .kpi-card.orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 10px 40px rgba(245, 87, 108, 0.3);
    }
    
    .kpi-value {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .kpi-label {
        font-size: 0.9rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .kpi-delta {
        font-size: 1rem;
        font-weight: 600;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        background: rgba(255,255,255,0.2);
        display: inline-block;
        margin-top: 0.5rem;
    }
    
    /* Section headers */
    .section-header {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    
    /* Comparison table styling */
    .comparison-table {
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        overflow: hidden;
    }
    
    /* Winner highlight */
    .winner {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }
    
    /* Map container */
    .map-container {
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.1);
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 12px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA LOADING
# =============================================================================

# Available datasets
DATASETS: Dict[str, Dict[str, str]] = {
    "Clean Urban (100 orders)": {
        "orders": "data/doha_orders_clean_100.csv",
        "couriers": "data/doha_couriers_clean_100.csv",
    },
    "Clean Urban (Full)": {
        "orders": "data/doha_orders_clean.csv",
        "couriers": "data/doha_couriers_clean.csv",
    },
    "Hybrid Urban/Suburban (100)": {
        "orders": "data/doha_orders_hybrid_100.csv",
        "couriers": "data/doha_couriers_hybrid_100.csv",
    },
    "Geographically Spread (100)": {
        "orders": "data/doha_orders_spread_100.csv",
        "couriers": "data/doha_couriers_spread_100.csv",
    },
    "Stress Test (High Volume)": {
        "orders": "data/doha_orders_stress.csv",
        "couriers": "data/doha_couriers_stress.csv",
    },
    "Quick Test (50 orders)": {
        "orders": "data/doha_test_orders_50.csv",
        "couriers": "data/doha_couriers_50.csv",
    },
}


def get_available_datasets() -> Dict[str, Dict[str, str]]:
    """Return only datasets that exist on disk."""
    available = {}
    for name, paths in DATASETS.items():
        if os.path.exists(paths["orders"]) and os.path.exists(paths["couriers"]):
            available[name] = paths
    return available


@st.cache_data(show_spinner=False)
def load_simulation_data(order_file: str, courier_file: str) -> Tuple[list, list]:
    """Load and cache simulation data."""
    drivers, orders = Simulation.load_data(order_file, courier_file)
    return drivers, orders


def run_simulation(drivers, orders, strategy: str) -> Dict[str, Any]:
    """Run a simulation with the given strategy."""
    sim = Simulation(copy.deepcopy(drivers), copy.deepcopy(orders))
    return sim.run(strategy=strategy, verbose=False)


# =============================================================================
# MAP VISUALIZATION
# =============================================================================

def create_route_map(
    baseline_routes: Dict[str, List[Tuple[float, float]]],
    optimized_routes: Dict[str, List[Tuple[float, float]]],
    orders: list,
    center_lat: float = 25.2854,
    center_lng: float = 51.5310
) -> Any:
    """
    Create a Folium map with color-coded routes.
    
    - Baseline routes: Red
    - Optimized (Combinatorial/Sequential) routes: Green
    """
    try:
        import folium
        from folium import plugins
    except ImportError:
        return None
    
    # Create base map centered on Doha
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=12,
        tiles='cartodbpositron'
    )
    
    # Add baseline routes (RED)
    baseline_group = folium.FeatureGroup(name="Baseline Routes")
    for driver_id, route in baseline_routes.items():
        if len(route) >= 2:
            folium.PolyLine(
                locations=route,
                weight=3,
                color='#ff4444',
                opacity=0.7,
                popup=f"Baseline: Driver {driver_id}"
            ).add_to(baseline_group)
    baseline_group.add_to(m)
    
    # Add optimized routes (GREEN)
    optimized_group = folium.FeatureGroup(name="Optimized Routes")
    for driver_id, route in optimized_routes.items():
        if len(route) >= 2:
            folium.PolyLine(
                locations=route,
                weight=3,
                color='#00cc66',
                opacity=0.8,
                popup=f"Optimized: Driver {driver_id}"
            ).add_to(optimized_group)
    optimized_group.add_to(m)
    
    # Add pickup markers
    pickup_group = folium.FeatureGroup(name="Pickup Locations")
    for order in orders[:50]:  # Limit markers for performance
        folium.CircleMarker(
            location=[order.pickup_lat, order.pickup_lng],
            radius=5,
            color='#3498db',
            fill=True,
            fillColor='#3498db',
            fillOpacity=0.7,
            popup=f"Pickup: {order.order_id}"
        ).add_to(pickup_group)
    pickup_group.add_to(m)
    
    # Add dropoff markers
    dropoff_group = folium.FeatureGroup(name="Dropoff Locations")
    for order in orders[:50]:  # Limit markers for performance
        folium.CircleMarker(
            location=[order.dropoff_lat, order.dropoff_lng],
            radius=5,
            color='#9b59b6',
            fill=True,
            fillColor='#9b59b6',
            fillOpacity=0.7,
            popup=f"Dropoff: {order.order_id}"
        ).add_to(dropoff_group)
    dropoff_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m


def render_map_comparison(
    baseline_routes: Dict[str, List],
    optimized_routes: Dict[str, List],
    orders: list
) -> None:
    """Render map comparison between baseline and optimized strategies."""
    try:
        import folium
        from streamlit_folium import st_folium
        
        # Calculate center from order locations
        if orders:
            center_lat = sum(o.pickup_lat for o in orders) / len(orders)
            center_lng = sum(o.pickup_lng for o in orders) / len(orders)
        else:
            center_lat, center_lng = 25.2854, 51.5310
        
        # Create combined map
        combined_map = create_route_map(
            baseline_routes, optimized_routes, orders, center_lat, center_lng
        )
        
        if combined_map:
            st_folium(combined_map, width=None, height=500, use_container_width=True)
        else:
            st.warning("Folium not available. Install with: pip install folium streamlit-folium")
            
    except ImportError:
        st.warning("Map visualization requires folium and streamlit-folium. Install with:")
        st.code("pip install folium streamlit-folium")


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar() -> Optional[Tuple[list, list, List[str]]]:
    """Render the sidebar configuration panel."""
    st.sidebar.markdown("## 🎛️ Configuration")
    st.sidebar.markdown("---")
    
    # Dataset selection
    st.sidebar.markdown("### 📊 Dataset")
    available_datasets = get_available_datasets()
    
    if not available_datasets:
        st.sidebar.error("No datasets found in data/ folder!")
        st.sidebar.info("Please ensure CSV files are present in the data/ directory.")
        return None
    
    selected_dataset = st.sidebar.selectbox(
        "Select Dataset",
        options=list(available_datasets.keys()),
        index=0,
        help="Choose the scenario to simulate"
    )
    
    dataset_info = available_datasets[selected_dataset]
    
    # Simulation parameters
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Parameters")
    
    speed = st.sidebar.slider(
        "Average Speed (km/h)",
        min_value=20,
        max_value=60,
        value=int(config.AVG_SPEED_KMH),
        step=5,
        help="Average vehicle speed in the city"
    )
    
    batch_window = st.sidebar.slider(
        "Batch Window (minutes)",
        min_value=0.5,
        max_value=5.0,
        value=float(config.BATCH_WINDOW_MINS),
        step=0.5,
        help="Time to accumulate orders before dispatching"
    )
    
    # Update config dynamically
    config.AVG_SPEED_KMH = float(speed)
    config.BATCH_WINDOW_MINS = batch_window
    
    # Strategy selection
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🧠 Strategies")
    
    strategies = st.sidebar.multiselect(
        "Compare Strategies",
        options=["baseline", "combinatorial", "sequential", "adaptive"],
        default=["baseline", "combinatorial"],
        help="Select strategies to compare"
    )
    
    if len(strategies) < 2:
        st.sidebar.warning("Select at least 2 strategies to compare")
        return None
    
    # Run button
    st.sidebar.markdown("---")
    run_clicked = st.sidebar.button("🚀 Run Simulation", use_container_width=True)
    
    if run_clicked:
        # Load data and store in session state for persistence
        try:
            drivers, orders = load_simulation_data(
                dataset_info["orders"],
                dataset_info["couriers"]
            )
            st.sidebar.success(f"Loaded {len(orders)} orders, {len(drivers)} drivers")
            # Store in session state to trigger simulation
            st.session_state["run_simulation"] = True
            st.session_state["drivers"] = drivers
            st.session_state["orders"] = orders
            st.session_state["strategies"] = strategies
            # Clear old results when new simulation requested
            if "simulation_results" in st.session_state:
                del st.session_state["simulation_results"]
            return drivers, orders, strategies
        except Exception as e:
            st.sidebar.error(f"Failed to load data: {e}")
            return None
    
    # Check if we have cached results in session state (persist across re-runs)
    if "simulation_results" in st.session_state:
        return st.session_state["drivers"], st.session_state["orders"], st.session_state["strategies"]
    
    # Info section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📖 About")
    st.sidebar.info("""
    Compares dispatch strategies:
    
    **Baseline**: Greedy nearest-neighbor
    **Sequential**: Per-order bidding
    **Combinatorial**: Bundle-based bidding
    **Adaptive**: Dynamic switching
    
    Key metric: **Drivers Used**
    """)
    
    return None


# =============================================================================
# KPI DISPLAY
# =============================================================================

def render_kpi_row(baseline_results: Dict, optimized_results: Dict, optimized_name: str) -> None:
    """Render the top KPI cards."""
    
    # Extract values
    baseline_drivers = baseline_results.get("Drivers Used", 0)
    optimized_drivers = optimized_results.get("Drivers Used", 0)
    drivers_saved = baseline_drivers - optimized_drivers
    pct_saved = (drivers_saved / baseline_drivers * 100) if baseline_drivers > 0 else 0
    
    total_orders = baseline_results.get("Total Deliveries", 0)
    
    # Parse efficiency
    baseline_eff_str = baseline_results.get("Active Driver Efficiency", "0.00")
    optimized_eff_str = optimized_results.get("Active Driver Efficiency", "0.00")
    try:
        baseline_eff = float(str(baseline_eff_str).split()[0])
        optimized_eff = float(str(optimized_eff_str).split()[0])
        eff_gain = ((optimized_eff - baseline_eff) / baseline_eff * 100) if baseline_eff > 0 else 0
    except (ValueError, IndexError):
        baseline_eff = optimized_eff = eff_gain = 0
    
    # Create 4 columns for KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Total Orders Delivered</div>
            <div class="kpi-value">{total_orders}</div>
            <div class="kpi-delta">Completed</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kpi-card green">
            <div class="kpi-label">Drivers Saved</div>
            <div class="kpi-value">{drivers_saved}</div>
            <div class="kpi-delta">↓ {pct_saved:.1f}% Reduction</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="kpi-card orange">
            <div class="kpi-label">Efficiency Gain</div>
            <div class="kpi-value">+{eff_gain:.0f}%</div>
            <div class="kpi-delta">{optimized_eff:.2f} del/driver</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{optimized_name.title()} Drivers</div>
            <div class="kpi-value">{optimized_drivers}</div>
            <div class="kpi-delta">vs {baseline_drivers} Baseline</div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# COMPARISON TABLE
# =============================================================================

def render_comparison_table(all_results: Dict[str, Dict]) -> None:
    """Render the strategy comparison table."""
    
    st.markdown('<div class="section-header">📊 Strategy Comparison</div>', unsafe_allow_html=True)
    
    # Prepare data for table
    metrics = [
        "Total Deliveries",
        "Drivers Used",
        "Active Driver Efficiency",
        "Avg Delivery Time",
        "Total Fleet Distance",
        "Late Deliveries (>60m)",
        "Fleet Utilization",
    ]
    
    strategies = list(all_results.keys())
    
    # Build dataframe
    table_data = []
    for metric in metrics:
        row = {"Metric": metric}
        for strat in strategies:
            val = all_results[strat].get(metric, "N/A")
            if isinstance(val, dict):
                val = "N/A"
            row[strat.title()] = val
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    
    # Highlight the winner column
    def highlight_winner(row):
        """Style the row to highlight the winning strategy."""
        styles = [''] * len(row)
        
        metric = row['Metric']
        
        # For "Drivers Used" - lower is better
        if metric == 'Drivers Used':
            try:
                values = [int(row[s.title()]) for s in strategies if s.title() in row.index]
                if values:
                    min_val = min(values)
                    for i, s in enumerate(strategies):
                        if s.title() in row.index and int(row[s.title()]) == min_val:
                            col_idx = list(row.index).index(s.title())
                            styles[col_idx] = 'background-color: #d4edda; font-weight: bold;'
            except (ValueError, TypeError):
                pass
        
        # For "Active Driver Efficiency" - higher is better
        elif metric == 'Active Driver Efficiency':
            try:
                values = []
                for s in strategies:
                    if s.title() in row.index:
                        val_str = str(row[s.title()]).split()[0]
                        values.append(float(val_str))
                if values:
                    max_val = max(values)
                    for i, s in enumerate(strategies):
                        if s.title() in row.index:
                            val_str = str(row[s.title()]).split()[0]
                            if float(val_str) == max_val:
                                col_idx = list(row.index).index(s.title())
                                styles[col_idx] = 'background-color: #d4edda; font-weight: bold;'
            except (ValueError, TypeError):
                pass
        
        return styles
    
    # Style and display table
    styled_df = df.style.apply(highlight_winner, axis=1)
    styled_df = styled_df.set_properties(**{
        'text-align': 'center',
        'font-size': '14px',
        'padding': '12px',
    })
    styled_df = styled_df.set_properties(subset=['Metric'], **{
        'text-align': 'left',
        'font-weight': 'bold',
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Highlight the key insight
    if "baseline" in all_results and "combinatorial" in all_results:
        baseline_drivers = all_results["baseline"].get("Drivers Used", 0)
        comb_drivers = all_results["combinatorial"].get("Drivers Used", 0)
        
        if baseline_drivers > comb_drivers:
            st.success(f"""
            **Combinatorial uses {baseline_drivers - comb_drivers} fewer drivers** 
            ({((baseline_drivers - comb_drivers) / baseline_drivers * 100):.1f}% reduction) 
            compared to Baseline.
            """)


# =============================================================================
# EXPLAINER SECTION
# =============================================================================

def render_explainer() -> None:
    """Render the strategy explainer section."""
    
    with st.expander("How the Strategies Work", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### Baseline (Greedy)
            Assigns each order to the nearest idle driver immediately.
            No bundling, no optimization.
            
            ### Sequential
            For each order, all eligible drivers compute a bid (cost).
            Lowest bidder wins. Drivers can accept multiple orders if
            they have capacity.
            """)
        
        with col2:
            st.markdown("""
            ### Combinatorial
            1. Accumulates orders for 1-2 minutes (batching)
            2. Generates all feasible order bundles
            3. Drivers bid on bundles
            4. Greedy assignment, preferring larger bundles
            
            ### Adaptive
            Monitors order arrival rate and switches between
            Sequential (low load) and Combinatorial (high load).
            """)
        
        st.markdown("---")
        st.markdown("""
        **Key Metric: Active Driver Efficiency** = Deliveries / Active Drivers
        
        Higher efficiency means fewer drivers needed for the same order volume.
        """)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    
    # Header
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 3rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">
            Snoonu Smart Dispatch
        </h1>
        <p style="font-size: 1.2rem; color: #666; max-width: 700px; margin: 0 auto;">
            Last-Mile Delivery Dispatch Strategy Comparison
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    sidebar_result = render_sidebar()
    
    # Check if simulation should run
    if sidebar_result is None:
        # Show landing page
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 3rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 20px; margin: 2rem 0;">
                <h2 style="color: #1a1a2e; margin-bottom: 1rem;">👈 Configure & Run</h2>
                <p style="color: #555; font-size: 1.1rem;">
                    Select a dataset and parameters from the sidebar,<br>
                    then click <strong>Run Simulation</strong> to see the results.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        render_explainer()
        return
    
    # Unpack results
    drivers, orders, strategies = sidebar_result
    
    # Run simulations
    st.markdown("---")
    
    # Check if we have cached results in session state
    if "simulation_results" in st.session_state:
        all_results = st.session_state["simulation_results"]
        st.success("Simulation complete!")
    else:
        # Run fresh simulation
        all_results: Dict[str, Dict] = {}
        
        with st.spinner("Running simulations... This may take a moment."):
            progress_bar = st.progress(0)
            
            for i, strategy in enumerate(strategies):
                progress_bar.progress((i + 1) / len(strategies), text=f"Running {strategy}...")
                results = run_simulation(drivers, orders, strategy)
                all_results[strategy] = results
            
            progress_bar.empty()
        
        # Store results in session state for persistence across re-runs
        st.session_state["simulation_results"] = all_results
        st.success("Simulation complete!")
    
    # Determine baseline and best optimized results
    baseline_key = "baseline" if "baseline" in all_results else list(all_results.keys())[0]
    optimized_key = "combinatorial" if "combinatorial" in all_results else (
        "sequential" if "sequential" in all_results else list(all_results.keys())[-1]
    )
    
    # KPI Row
    render_kpi_row(all_results[baseline_key], all_results[optimized_key], optimized_key)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Map Visualization
    st.markdown('<div class="section-header">🗺️ Route Visualization</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <p style="color: #666; margin-bottom: 1rem;">
        <span style="color: #ff4444;">●</span> <strong>Red</strong>: Baseline routes
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color: #00cc66;">●</span> <strong>Green</strong>: {optimized_key.title()} routes
    </p>
    """, unsafe_allow_html=True)
    
    # Get route data
    baseline_routes = all_results[baseline_key].get("driver_routes", {})
    optimized_routes = all_results[optimized_key].get("driver_routes", {})
    
    render_map_comparison(baseline_routes, optimized_routes, orders)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Comparison Table
    render_comparison_table(all_results)
    
    # Explainer
    st.markdown("<br>", unsafe_allow_html=True)
    render_explainer()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; padding: 1rem;">
        Snoonu Smart Dispatch | Hackathon 2026
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
