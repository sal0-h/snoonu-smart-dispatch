# snoonu-smart-dispatch/src/simulation.py
"""
Simulation Engine for the Snoonu Last-Mile Delivery Simulation.

This module implements a discrete-event simulation of food delivery operations.
Key responsibilities:
- Time management (tick-based simulation)
- Order injection based on creation times
- Driver state machine updates
- Dispatch strategy orchestration
- KPI calculation and reporting

The simulation compares different dispatch strategies to demonstrate
the efficiency gains of the Smart AI (combinatorial) over baseline (greedy).

KEY METRIC: Active Driver Efficiency = Deliveries / Active Drivers
This is the winning metric that shows how bundling reduces fleet size needs.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, time
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

from . import config, utils
from .models import Order, Driver, OrderStatus, DriverStatus
from .dispatch import DispatchEngine


@dataclass
class SimulationResults:
    """
    Container for simulation results and KPIs.
    
    All the metrics needed to evaluate dispatch strategy performance.
    """
    total_deliveries: int
    avg_delivery_time_min: float
    total_distance_km: float
    late_deliveries: int
    fleet_utilization_pct: float
    drivers_used: int
    total_drivers: int
    
    # THE KEY METRIC: Active Driver Efficiency
    active_driver_efficiency: float
    
    # Route data for visualization
    driver_routes: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "Total Deliveries": self.total_deliveries,
            "Avg Delivery Time": f"{self.avg_delivery_time_min:.2f} min",
            "Total Fleet Distance": f"{self.total_distance_km:.2f} km",
            "Late Deliveries (>60m)": self.late_deliveries,
            "Fleet Utilization": f"{self.fleet_utilization_pct:.2f}%",
            "Drivers Used": self.drivers_used,
            "Active Driver Efficiency": f"{self.active_driver_efficiency:.2f}",
        }


class Simulation:
    """
    Discrete-event simulation of last-mile delivery operations.
    
    The simulation advances time in discrete ticks (default: 1 minute each).
    At each tick:
    1. Update driver positions and handle stop arrivals
    2. Inject new orders based on their creation time
    3. Dispatch pending orders using the selected strategy
    4. Track KPIs
    
    Attributes:
        drivers: List of all drivers in the fleet
        orders_map: Quick lookup of orders by ID
        current_time: Current simulation time
        completed_missions: List of completed deliveries (for KPI calculation)
        drivers_activated: Set of driver IDs that handled at least one order
    """
    
    def __init__(self, drivers: List[Driver], orders: List[Order]) -> None:
        """
        Initialize the simulation with fleet and orders.
        
        Args:
            drivers: List of all available drivers
            orders: List of all orders to be delivered
        """
        self.start_time: time = config.START_TIME
        self.end_time: time = config.SIMULATION_END_TIME
        self.current_time: time = self.start_time

        # Sort orders by creation time for proper injection
        self.master_orders_list: List[Order] = sorted(orders, key=lambda o: o.created_time)
        self.drivers: List[Driver] = drivers
        self.orders_map: Dict[str, Order] = {o.order_id: o for o in orders}
        
        self.pending_orders: List[Order] = []
        self.completed_missions: List[Dict] = []
        
        # KPI Tracking
        self.total_distance_traveled: float = 0.0
        self.total_busy_driver_ticks: int = 0
        self.total_driver_ticks: int = 0
        self.drivers_activated: set = set()  # Driver IDs who handled orders
        
        # Route history for visualization
        self.driver_route_history: Dict[str, List[Tuple[float, float]]] = {}

        self.dispatch_engine = DispatchEngine()
        self.recent_order_times: List[time] = []
        
        # Batching state
        self.batch_start_time: Optional[time] = None
        
        # Precompute road distances for all locations (much faster than individual calls)
        self._precompute_distances(drivers, orders)

    def _precompute_distances(self, drivers: List[Driver], orders: List[Order]) -> None:
        """
        Precompute all pairwise distances using OSRM Table API.
        
        This is called once at initialization and populates the distance cache
        with all driver and order locations. Much faster than individual API calls
        during simulation (1 API call instead of N^2).
        """
        if not config.USE_ROAD_DISTANCE:
            return  # Skip if using Haversine
        
        # Collect all unique locations
        locations = set()
        
        # Driver starting positions
        for driver in drivers:
            locations.add((driver.start_lat, driver.start_lng))
        
        # Order pickup and dropoff locations
        for order in orders:
            locations.add(order.pickup_loc)
            locations.add(order.dropoff_loc)
        
        locations_list = list(locations)
        
        if len(locations_list) < 2:
            return
        
        # Use batch API to precompute all distances
        print(f"Precomputing road distances for {len(locations_list)} locations...")
        utils.precompute_distances(locations_list)
        print(f"Distance cache populated: {utils.get_osrm_cache_stats()['size']} entries")

    @staticmethod
    def load_data(order_file: str, courier_file: str) -> Tuple[List[Driver], List[Order]]:
        """
        Load simulation data from CSV files.
        
        Args:
            order_file: Path to orders CSV
            courier_file: Path to couriers CSV
            
        Returns:
            Tuple of (drivers, orders) lists
            
        Raises:
            FileNotFoundError: If files don't exist
            ValueError: If file format is invalid
        """
        # Validate file existence
        if not os.path.exists(order_file):
            raise FileNotFoundError(f"Order file not found: {order_file}")
        if not os.path.exists(courier_file):
            raise FileNotFoundError(f"Courier file not found: {courier_file}")
        
        orders: List[Order] = []
        with open(order_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Handle both datetime and time-only formats
                    created_time_str = row['created_time']
                    if ' ' in created_time_str:
                        # Full datetime format: '2025-01-15 18:07:14'
                        created_time = datetime.strptime(created_time_str, '%Y-%m-%d %H:%M:%S').time()
                    else:
                        # Time-only format: '18:07:14'
                        created_time = datetime.strptime(created_time_str, '%H:%M:%S').time()
                    estimated_time = int(row['estimated_delivery_time_min'])
                    deadline = utils.add_minutes_to_time(created_time, estimated_time)
                    orders.append(Order(
                        order_id=row['order_id'],
                        pickup_lat=float(row['pickup_lat']),
                        pickup_lng=float(row['pickup_lng']),
                        dropoff_lat=float(row['dropoff_lat']),
                        dropoff_lng=float(row['dropoff_lng']),
                        created_time=created_time,
                        deadline=deadline,
                        estimated_delivery_time_min=estimated_time
                    ))
                except (KeyError, ValueError) as e:
                    raise ValueError(f"Invalid order data in {order_file}: {e}")

        drivers: List[Driver] = []
        with open(courier_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Handle both datetime and time-only formats
                    available_from_str = row['available_from']
                    if ' ' in available_from_str:
                        # Full datetime format: '2025-01-15 17:08:00'
                        available_from = datetime.strptime(available_from_str, '%Y-%m-%d %H:%M:%S').time()
                    else:
                        # Time-only format: '17:08:00'
                        available_from = datetime.strptime(available_from_str, '%H:%M:%S').time()
                    drivers.append(Driver(
                        driver_id=row['courier_id'],
                        start_lat=float(row['courier_lat']),
                        start_lng=float(row['courier_lng']),
                        vehicle_type=row['vehicle_type'],
                        capacity=int(row['bundle_capacity']),
                        available_from=available_from
                    ))
                except (KeyError, ValueError) as e:
                    raise ValueError(f"Invalid courier data in {courier_file}: {e}")
                    
        return drivers, orders

    def _record_driver_position(self, driver: Driver) -> None:
        """Record driver's current position for route visualization."""
        if driver.driver_id not in self.driver_route_history:
            self.driver_route_history[driver.driver_id] = []
        
        current_pos = (driver.current_lat, driver.current_lng)
        history = self.driver_route_history[driver.driver_id]
        
        # Only add if position changed
        if not history or history[-1] != current_pos:
            history.append(current_pos)

    def _update_driver_states(self) -> None:
        """
        Process driver movements and state changes for the current tick.
        
        This is the core state machine logic:
        - IDLE -> ACCRUING: When orders are assigned
        - ACCRUING -> DELIVERING: When all pickups complete
        - DELIVERING -> IDLE: When route complete
        
        Handles multiple stop arrivals per tick if they occur within the time window.
        """
        for driver in self.drivers:
            if driver.status == DriverStatus.IDLE:
                continue

            # Process all stops the driver has arrived at
            while (driver.status != DriverStatus.IDLE and 
                   0 <= driver.current_stop_index < len(driver.route) and
                   self.current_time >= driver.arrival_time_at_next_stop):
                
                current_stop = driver.route[driver.current_stop_index]
                order = self.orders_map[current_stop.order_id]

                # Update position
                driver.current_lat, driver.current_lng = current_stop.location
                self._record_driver_position(driver)
                
                # Process stop type
                if current_stop.stop_type == 'PICKUP':
                    order.status = OrderStatus.PICKED_UP
                    order.pickup_time = self.current_time
                elif current_stop.stop_type == 'DROPOFF':
                    order.status = OrderStatus.DELIVERED
                    order.dropoff_time = self.current_time
                    self.completed_missions.append({
                        "order_id": order.order_id,
                        "driver_id": driver.driver_id,
                        "created_time": order.created_time,
                        "delivered_time": self.current_time,
                    })
                    if order in driver.assigned_orders:
                        driver.assigned_orders.remove(order)

                # Advance to next stop
                driver.current_stop_index += 1
                
                if driver.current_stop_index >= len(driver.route):
                    # Route complete - return to IDLE
                    driver.status = DriverStatus.IDLE
                    driver.route = []
                    driver.current_stop_index = -1
                    driver.assigned_orders = []
                else:
                    # Calculate arrival at next stop using road travel time
                    next_stop = driver.route[driver.current_stop_index]
                    travel_time = utils.get_travel_time(
                        driver.current_lat, driver.current_lng, 
                        next_stop.location[0], next_stop.location[1]
                    )
                    total_time = travel_time + config.SERVICE_TIME_MINS
                    driver.arrival_time_at_next_stop = utils.add_minutes_to_time(
                        self.current_time, total_time
                    )

                    # Transition to DELIVERING if only dropoffs remain
                    remaining_stops = driver.route[driver.current_stop_index:]
                    if all(s.stop_type == 'DROPOFF' for s in remaining_stops):
                        driver.status = DriverStatus.DELIVERING

    def _inject_new_orders(self) -> None:
        """Add orders to pending queue based on their creation time."""
        orders_to_move: List[Order] = []
        for order in self.master_orders_list:
            if order.created_time <= self.current_time:
                orders_to_move.append(order)
            else:
                break  # Orders are sorted by creation time
        
        for order in orders_to_move:
            self.pending_orders.append(order)
            self.master_orders_list.remove(order)
            self.recent_order_times.append(order.created_time)
            
            # Track batch window start
            if self.batch_start_time is None:
                self.batch_start_time = self.current_time

    def _get_dispatch_mode(self) -> str:
        """
        Determine dispatch mode based on current order load.
        
        Returns:
            'combinatorial' for high load, 'sequential' for low load
        """
        five_mins_ago = utils.add_minutes_to_time(
            self.current_time, -config.COMBINATORIAL_WINDOW_MINS
        )
        recent_orders = [t for t in self.recent_order_times if t > five_mins_ago]
        order_rate = len(recent_orders) / config.COMBINATORIAL_WINDOW_MINS
        return "combinatorial" if order_rate >= config.HIGH_LOAD_THRESHOLD else "sequential"
    
    def _should_dispatch_batch(self) -> bool:
        """
        Determine if pending orders should be dispatched now.
        
        Conditions:
        - Batch window elapsed since first order arrived
        - An order is urgent (close to deadline)
        
        Returns:
            True if dispatch should occur, False to continue batching
        """
        if not self.pending_orders:
            return False
        
        # Check if batch window has elapsed
        if self.batch_start_time is not None:
            dummy_date = datetime.now().date()
            batch_start_dt = datetime.combine(dummy_date, self.batch_start_time)
            current_dt = datetime.combine(dummy_date, self.current_time)
            elapsed_mins = (current_dt - batch_start_dt).total_seconds() / 60
            
            if elapsed_mins >= config.BATCH_WINDOW_MINS:
                return True
        
        # Check for urgent orders
        for order in self.pending_orders:
            dummy_date = datetime.now().date()
            current_dt = datetime.combine(dummy_date, self.current_time)
            deadline_dt = datetime.combine(dummy_date, order.deadline)
            time_to_deadline = (deadline_dt - current_dt).total_seconds() / 60
            
            # Urgent if less than 1/3 of estimated time remains
            if time_to_deadline <= order.estimated_delivery_time_min / 3:
                return True
        
        return False

    def tick(self, strategy: str, verbose: bool = True) -> None:
        """
        Execute a single simulation tick.
        
        Args:
            strategy: Dispatch strategy ('baseline', 'sequential', 'combinatorial', 'adaptive')
            verbose: Whether to print progress
        """
        self._update_driver_states()
        self._inject_new_orders()

        assigned_in_tick: List[Order] = []
        distance_in_tick: float = 0.0

        if self.pending_orders:
            # Baseline dispatches immediately; others use batching
            should_dispatch = (strategy == "baseline") or self._should_dispatch_batch()
            
            if should_dispatch:
                dispatch_orders = list(self.pending_orders)
                
                if strategy == "baseline":
                    assigned_in_tick, distance_in_tick = self.dispatch_engine.run_baseline(
                        self.drivers, dispatch_orders, self.current_time
                    )
                elif strategy == "adaptive":
                    mode = self._get_dispatch_mode()
                    if mode == "sequential":
                        assigned_in_tick, distance_in_tick = self.dispatch_engine.run_sequential(
                            self.drivers, dispatch_orders, self.current_time
                        )
                    else:
                        assigned_in_tick, distance_in_tick = self.dispatch_engine.run_combinatorial(
                            self.drivers, dispatch_orders, self.current_time
                        )
                elif strategy == "sequential":
                    assigned_in_tick, distance_in_tick = self.dispatch_engine.run_sequential(
                        self.drivers, dispatch_orders, self.current_time
                    )
                elif strategy == "combinatorial":
                    assigned_in_tick, distance_in_tick = self.dispatch_engine.run_combinatorial(
                        self.drivers, dispatch_orders, self.current_time
                    )
                
                # Reset batch timer
                self.batch_start_time = None
                
        # Update distance KPI
        self.total_distance_traveled += distance_in_tick
        
        # Remove assigned orders from pending
        for order in assigned_in_tick:
            if order in self.pending_orders:
                self.pending_orders.remove(order)
        
        # Track activated drivers
        for driver in self.drivers:
            if len(driver.assigned_orders) > 0 or driver.status != DriverStatus.IDLE:
                self.drivers_activated.add(driver.driver_id)
                self._record_driver_position(driver)

        # Progress logging
        if verbose and (len(assigned_in_tick) > 0 or self.current_time.minute % 10 == 0):
            print(f"[{self.current_time.strftime('%H:%M')}] "
                  f"Assigned: {len(assigned_in_tick)}, "
                  f"Pending: {len(self.pending_orders)}, "
                  f"Completed: {len(self.completed_missions)}")

        # Fleet utilization tracking
        self.total_driver_ticks += len(self.drivers)
        self.total_busy_driver_ticks += sum(
            1 for d in self.drivers if d.status != DriverStatus.IDLE
        )
        
        # Advance simulation time
        self.current_time = utils.add_minutes_to_time(
            self.current_time, config.SIMULATION_SPEED_MINUTES
        )

    def run(self, strategy: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Run the full simulation.
        
        Args:
            strategy: Dispatch strategy to use
            verbose: Whether to print progress
            
        Returns:
            Dictionary of KPI results
        """
        if verbose:
            print(f"======== Starting Simulation: {strategy.upper()} ========")
        
        total_orders = len(self.master_orders_list) + len(self.pending_orders)
        
        while (self.current_time < self.end_time and 
               len(self.completed_missions) < total_orders):
            self.tick(strategy, verbose)
        
        if verbose:
            print("Simulation complete. Calculating results...")
        
        return self.get_results()

    def get_results(self) -> Dict[str, Any]:
        """
        Calculate and return comprehensive KPI results (30+ metrics).
        
        THE KEY METRIC: Active Driver Efficiency
        = Total Deliveries / Number of Active Drivers
        
        This metric directly measures how well the dispatch strategy
        bundles orders to minimize fleet size needs.
        
        Returns:
            Dictionary with all KPIs and route data for visualization
        """
        import statistics
        
        total_deliveries = len(self.completed_missions)
        total_orders = len(self.orders_map)
        total_drivers = len(self.drivers)
        drivers_used = len(self.drivers_activated)
        
        if total_deliveries == 0:
            return self._empty_results(total_orders, total_drivers)

        # Calculate delivery times
        delivery_times: List[float] = []
        late_deliveries_30m: int = 0
        late_deliveries_45m: int = 0
        late_deliveries_60m: int = 0
        on_time_deliveries: int = 0
        early_deliveries: int = 0
        
        dummy_date = datetime.now().date()
        for mission in self.completed_missions:
            created_dt = datetime.combine(dummy_date, mission['created_time'])
            delivered_dt = datetime.combine(dummy_date, mission['delivered_time'])
            delivery_duration = (delivered_dt - created_dt).total_seconds() / 60
            delivery_times.append(delivery_duration)
            
            if delivery_duration > 60:
                late_deliveries_60m += 1
            if delivery_duration > 45:
                late_deliveries_45m += 1
            if delivery_duration > 30:
                late_deliveries_30m += 1
            if delivery_duration <= 30:
                on_time_deliveries += 1
            if delivery_duration < 15:
                early_deliveries += 1
        
        # Basic delivery time stats
        avg_delivery_time = statistics.mean(delivery_times)
        median_delivery_time = statistics.median(delivery_times)
        min_delivery_time = min(delivery_times)
        max_delivery_time = max(delivery_times)
        std_delivery_time = statistics.stdev(delivery_times) if len(delivery_times) > 1 else 0
        
        # Percentiles
        sorted_times = sorted(delivery_times)
        p90_delivery_time = sorted_times[int(len(sorted_times) * 0.90)] if delivery_times else 0
        p95_delivery_time = sorted_times[int(len(sorted_times) * 0.95)] if delivery_times else 0
        p99_delivery_time = sorted_times[int(len(sorted_times) * 0.99)] if delivery_times else 0
        
        # Fleet metrics
        fleet_utilization: float = 0.0
        if self.total_driver_ticks > 0:
            fleet_utilization = (self.total_busy_driver_ticks / self.total_driver_ticks) * 100

        drivers_idle = total_drivers - drivers_used
        driver_utilization_rate = (drivers_used / total_drivers) * 100 if total_drivers > 0 else 0
        
        # Distance metrics
        avg_distance_per_order = self.total_distance_traveled / total_deliveries if total_deliveries > 0 else 0
        orders_per_driver = total_deliveries / drivers_used if drivers_used > 0 else 0
        distance_per_driver = self.total_distance_traveled / drivers_used if drivers_used > 0 else 0
        
        # Efficiency metrics
        delivery_success_rate = (total_deliveries / total_orders) * 100 if total_orders > 0 else 0
        on_time_rate = (on_time_deliveries / total_deliveries) * 100 if total_deliveries > 0 else 0
        late_rate_45m = (late_deliveries_45m / total_deliveries) * 100 if total_deliveries > 0 else 0
        late_rate_60m = (late_deliveries_60m / total_deliveries) * 100 if total_deliveries > 0 else 0
        
        # Time efficiency ratio
        time_efficiency = avg_delivery_time / avg_distance_per_order if avg_distance_per_order > 0 else 0

        # Active Driver Efficiency (key metric)
        active_driver_efficiency: float = 0.0
        if drivers_used > 0:
            active_driver_efficiency = total_deliveries / drivers_used

        return {
            # Delivery counts
            "orders_delivered": total_deliveries,
            "total_orders": total_orders,
            "delivery_success_rate_pct": round(delivery_success_rate, 2),
            
            # Driver metrics
            "drivers_used": drivers_used,
            "total_drivers": total_drivers,
            "drivers_idle": drivers_idle,
            "driver_utilization_rate_pct": round(driver_utilization_rate, 2),
            "orders_per_driver": round(orders_per_driver, 2),
            "fleet_utilization_pct": round(fleet_utilization, 2),
            
            # Delivery time stats (minutes)
            "avg_delivery_time_min": round(avg_delivery_time, 2),
            "median_delivery_time_min": round(median_delivery_time, 2),
            "min_delivery_time_min": round(min_delivery_time, 2),
            "max_delivery_time_min": round(max_delivery_time, 2),
            "std_delivery_time_min": round(std_delivery_time, 2),
            "p90_delivery_time_min": round(p90_delivery_time, 2),
            "p95_delivery_time_min": round(p95_delivery_time, 2),
            "p99_delivery_time_min": round(p99_delivery_time, 2),
            
            # Distance metrics (km)
            "total_fleet_distance_km": round(self.total_distance_traveled, 2),
            "avg_distance_per_order_km": round(avg_distance_per_order, 2),
            "distance_per_driver_km": round(distance_per_driver, 2),
            
            # On-time performance
            "on_time_deliveries": on_time_deliveries,
            "on_time_rate_pct": round(on_time_rate, 2),
            "early_deliveries_under_15m": early_deliveries,
            "late_deliveries_over_30m": late_deliveries_30m,
            "late_deliveries_over_45m": late_deliveries_45m,
            "late_deliveries_over_60m": late_deliveries_60m,
            "late_rate_45m_pct": round(late_rate_45m, 2),
            "late_rate_60m_pct": round(late_rate_60m, 2),
            
            # Efficiency scores
            "time_efficiency_ratio": round(time_efficiency, 4),
            "active_driver_efficiency": round(active_driver_efficiency, 2),
            
            # Legacy format for backward compatibility with app.py
            "Total Deliveries": total_deliveries,
            "Avg Delivery Time": f"{avg_delivery_time:.2f} min",
            "Total Fleet Distance": f"{self.total_distance_traveled:.2f} km",
            "Late Deliveries (>60m)": late_deliveries_60m,
            "Fleet Utilization": f"{fleet_utilization:.2f}%",
            "Drivers Used": drivers_used,
            "Active Driver Efficiency": f"{active_driver_efficiency:.2f}",
            "Orders Delivered": f"{total_deliveries}/{total_orders}",
            "Min Delivery Time": f"{min_delivery_time:.2f} min",
            "Max Delivery Time": f"{max_delivery_time:.2f} min",
            "Avg Distance/Order": f"{avg_distance_per_order:.2f} km",
            "Late Deliveries (>45m)": late_deliveries_45m,
            "Orders/Driver": f"{orders_per_driver:.2f}",
            
            # Route data for visualization
            "driver_routes": self.driver_route_history,
        }
    
    def _empty_results(self, total_orders: int, total_drivers: int) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            "orders_delivered": 0,
            "total_orders": total_orders,
            "delivery_success_rate_pct": 0,
            "drivers_used": 0,
            "total_drivers": total_drivers,
            "drivers_idle": total_drivers,
            "driver_utilization_rate_pct": 0,
            "orders_per_driver": 0,
            "fleet_utilization_pct": 0,
            "avg_delivery_time_min": 0,
            "median_delivery_time_min": 0,
            "min_delivery_time_min": 0,
            "max_delivery_time_min": 0,
            "std_delivery_time_min": 0,
            "p90_delivery_time_min": 0,
            "p95_delivery_time_min": 0,
            "p99_delivery_time_min": 0,
            "total_fleet_distance_km": 0,
            "avg_distance_per_order_km": 0,
            "distance_per_driver_km": 0,
            "on_time_deliveries": 0,
            "on_time_rate_pct": 0,
            "early_deliveries_under_15m": 0,
            "late_deliveries_over_30m": 0,
            "late_deliveries_over_45m": 0,
            "late_deliveries_over_60m": 0,
            "late_rate_45m_pct": 0,
            "late_rate_60m_pct": 0,
            "time_efficiency_ratio": 0,
            "active_driver_efficiency": 0,
            # Legacy format
            "Total Deliveries": 0,
            "Avg Delivery Time": "0.00 min",
            "Total Fleet Distance": "0.00 km",
            "Late Deliveries (>60m)": 0,
            "Fleet Utilization": "0.00%",
            "Drivers Used": 0,
            "Active Driver Efficiency": "0.00",
            "Orders Delivered": f"0/{total_orders}",
            "Min Delivery Time": "0.00 min",
            "Max Delivery Time": "0.00 min",
            "Avg Distance/Order": "0.00 km",
            "Late Deliveries (>45m)": 0,
            "Orders/Driver": "0.00",
            "driver_routes": {},
        }

    def get_route_visualization_data(self) -> Dict[str, Any]:
        """
        Get data formatted for map visualization.
        
        Returns:
            Dictionary with driver routes and order locations
        """
        # Get order locations
        pickup_locations = []
        dropoff_locations = []
        
        for order in self.orders_map.values():
            pickup_locations.append({
                "order_id": order.order_id,
                "lat": order.pickup_lat,
                "lng": order.pickup_lng,
                "type": "pickup"
            })
            dropoff_locations.append({
                "order_id": order.order_id,
                "lat": order.dropoff_lat,
                "lng": order.dropoff_lng,
                "type": "dropoff"
            })
        
        # Get driver routes
        driver_routes = []
        for driver_id, route in self.driver_route_history.items():
            if route:  # Only include drivers who moved
                driver_routes.append({
                    "driver_id": driver_id,
                    "route": route
                })
        
        return {
            "pickups": pickup_locations,
            "dropoffs": dropoff_locations,
            "routes": driver_routes,
            "drivers_used": len(self.drivers_activated),
            "total_drivers": len(self.drivers)
        }
