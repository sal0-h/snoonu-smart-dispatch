# snoonu-smart-dispatch/src/dispatch.py
"""
Dispatch Engine for the Snoonu Last-Mile Delivery Simulation.

This module implements bidding-based dispatch strategies for order-to-driver matching.
Four dispatch strategies are available:

1. **Baseline (Greedy)**: Assigns each order to the nearest idle driver.
   Simple but inefficient - no bundling, no optimization.

2. **Sequential**: For each order, eligible drivers bid based on marginal cost.
   Lowest bidder wins. Enables dynamic re-routing as new orders arrive.

3. **Combinatorial**: Uses spatial clustering (graph-cut) to generate order bundles.
   Drivers bid on bundles. Explicitly prioritizes multi-order bundles.

4. **Adaptive**: Monitors order arrival rate and switches between Sequential
   (low load) and Combinatorial (high load) dynamically.
"""

from __future__ import annotations

from itertools import permutations, combinations
from typing import List, Tuple, Optional, Set, Dict, FrozenSet
from functools import lru_cache
import random

from . import utils, scoring, config
from .models import Driver, Order, Bundle, DriverStatus, OrderStatus, Stop


# =============================================================================
# CACHING FOR TSP ROUTES
# =============================================================================
# Cache for TSP route calculations within a single dispatch cycle.
# Key: (rounded_start_loc, frozenset_of_order_ids, frozenset_of_already_picked_up_ids)
# Cleared at the start of each dispatch call to avoid stale data.

_tsp_cache: Dict[Tuple[Tuple[float, float], FrozenSet[str], FrozenSet[str]], Tuple[List[Stop], float]] = {}


def _clear_tsp_cache() -> None:
    """Clear the TSP route cache. Call at start of each dispatch cycle."""
    global _tsp_cache
    _tsp_cache.clear()


def _round_loc(loc: Tuple[float, float], precision: int = 4) -> Tuple[float, float]:
    """Round location to reduce cache misses from floating point differences."""
    return (round(loc[0], precision), round(loc[1], precision))


def _build_distance_matrix(orders: List[Order]) -> Dict[Tuple[str, str], float]:
    """
    Build a distance matrix between order pickup locations.
    
    Returns dict mapping (order_id_1, order_id_2) -> distance in km.
    """
    distances: Dict[Tuple[str, str], float] = {}
    for i, o1 in enumerate(orders):
        for j, o2 in enumerate(orders):
            if i < j:
                dist = utils.get_distance(
                    o1.pickup_lat, o1.pickup_lng,
                    o2.pickup_lat, o2.pickup_lng
                )
                distances[(o1.order_id, o2.order_id)] = dist
                distances[(o2.order_id, o1.order_id)] = dist
    return distances


def _greedy_max_cut(
    orders: List[Order], 
    distances: Dict[Tuple[str, str], float]
) -> Tuple[List[Order], List[Order]]:
    """
    Greedy approximation of max-cut to split orders into two groups.
    
    Max-cut maximizes the sum of distances between the two groups,
    meaning orders within each group are spatially close.
    
    This is a 0.5-approximation algorithm (guaranteed at least half of optimal).
    """
    if len(orders) <= 1:
        return orders, []
    
    # Start with random assignment
    group_a: List[Order] = []
    group_b: List[Order] = []
    
    # Greedy: for each order, put it in the group that maximizes cut value
    for order in orders:
        # Calculate sum of distances to each group
        dist_to_a = sum(
            distances.get((order.order_id, o.order_id), 0) 
            for o in group_a
        )
        dist_to_b = sum(
            distances.get((order.order_id, o.order_id), 0) 
            for o in group_b
        )
        
        # Put in group that maximizes cut (opposite of where it's closest)
        if dist_to_a >= dist_to_b:
            group_a.append(order)
        else:
            group_b.append(order)
    
    return group_a, group_b


def generate_spatial_bundles(
    orders: List[Order],
    max_bundle_size: int = None,
    prebuilt_distances: Optional[Dict[Tuple[str, str], float]] = None
) -> List[List[Order]]:
    """
    Generate bundles using recursive graph-cut spatial clustering.
    
    This is a domain-dependent bundle generation strategy that exploits
    the spatial relationship between orders. Instead of generating all
    O(n choose k) combinations, this generates O(n log n) bundles that
    are more likely to be profitable.
    
    Procedure (GRAPH-CUT):
    1. Start with bundle containing all orders
    2. Add this bundle to candidate list
    3. Build distance graph between orders (pickup locations)
    4. Split using max-cut approximation
    5. Add resulting sub-bundles
    6. Recursively repeat until bundles are small enough
    
    Args:
        orders: List of orders to bundle
        max_bundle_size: Maximum bundle size to generate (default from config)
        prebuilt_distances: Optional pre-computed distance matrix (optimization)
        
    Returns:
        List of order bundles (each bundle is a list of orders)
    """
    if max_bundle_size is None:
        max_bundle_size = config.MAX_BUNDLE_SIZE
    
    if not orders:
        return []
    
    # Use prebuilt distance matrix or build one
    if prebuilt_distances is not None:
        distances = prebuilt_distances
    else:
        distances = _build_distance_matrix(orders)
    
    # Generate bundles recursively
    bundles: List[List[Order]] = []
    
    # Track seen bundle signatures for O(1) duplicate detection
    seen_bundle_ids: Set[FrozenSet[str]] = set()
    
    def add_bundle_if_new(bundle: List[Order]) -> None:
        """Add bundle only if not already seen."""
        bundle_sig = frozenset(o.order_id for o in bundle)
        if bundle_sig not in seen_bundle_ids:
            seen_bundle_ids.add(bundle_sig)
            bundles.append(bundle)
    
    def recursive_split(order_group: List[Order], depth: int = 0):
        """Recursively split and generate bundles."""
        if not order_group:
            return
        
        # Always add individual orders as bundles (size 1)
        if len(order_group) == 1:
            add_bundle_if_new(order_group)
            return
        
        # Add current group if within size limit
        if len(order_group) <= max_bundle_size:
            add_bundle_if_new(order_group)
        
        # Split into two groups using max-cut
        group_a, group_b = _greedy_max_cut(order_group, distances)
        
        # Add the split groups if within size limit
        if 1 < len(group_a) <= max_bundle_size:
            add_bundle_if_new(group_a)
        if 1 < len(group_b) <= max_bundle_size:
            add_bundle_if_new(group_b)
        
        # Recurse on larger groups (but limit depth to avoid explosion)
        if depth < 5:  # Max recursion depth
            if len(group_a) > max_bundle_size:
                recursive_split(group_a, depth + 1)
            if len(group_b) > max_bundle_size:
                recursive_split(group_b, depth + 1)
    
    # Start recursion
    recursive_split(orders)
    
    # Also add pairs of nearby orders (important for small bundles)
    # This ensures we don't miss good 2-order bundles
    # Now uses O(1) duplicate detection via seen_bundle_ids
    for i, o1 in enumerate(orders):
        for j, o2 in enumerate(orders):
            if i < j:
                dist = distances.get((o1.order_id, o2.order_id), float('inf'))
                if dist <= config.MAX_PICKUP_DISTANCE_KM:
                    add_bundle_if_new([o1, o2])
    
    # Add all single orders if not already present (using O(1) lookup)
    for order in orders:
        add_bundle_if_new([order])
    
    return bundles


def find_optimal_route(
    start_loc: Tuple[float, float], 
    orders: List[Order], 
    already_picked_up: Optional[List[Order]] = None,
    use_cache: bool = True
) -> Tuple[List[Stop], float]:
    """
    Find the shortest route for a driver to complete a set of orders.
    
    This solves the Traveling Salesperson Problem with Precedence Constraints (TSP-PC).
    For each order, pickup must occur before dropoff.
    
    Algorithm: Held-Karp Dynamic Programming
    - State: dp[visited_mask][last_node] = minimum distance
    - Handles precedence constraints by checking if pickup visited before dropoff
    - Complexity: O(n² * 2^n) where n = number of stops
    
    This is MUCH faster than brute-force O(n!) for larger bundles:
    - 4 stops: 256 vs 24 operations
    - 6 stops: 2,304 vs 720 operations  
    - 8 stops: 16,384 vs 40,320 operations (2.5x faster)
    - 10 stops: 102,400 vs 3,628,800 operations (35x faster)
    
    Caching:
    - Results are cached by (rounded_start_loc, order_ids, already_picked_up_ids)
    - Cache is cleared at the start of each dispatch cycle via _clear_tsp_cache()
    
    Args:
        start_loc: Driver's current (lat, lng) position
        orders: All orders to be delivered
        already_picked_up: Orders already in vehicle (skip pickup stop)
        use_cache: Whether to use TSP cache (default True)
        
    Returns:
        Tuple of (optimal_stop_sequence, total_distance_km)
        Returns ([], 0.0) if no orders provided
    """
    global _tsp_cache
    
    if not orders:
        return [], 0.0
    
    if already_picked_up is None:
        already_picked_up = []
    
    already_picked_up_ids: Set[str] = {o.order_id for o in already_picked_up}
    order_ids: FrozenSet[str] = frozenset(o.order_id for o in orders)
    picked_up_frozen: FrozenSet[str] = frozenset(already_picked_up_ids)
    
    # Check cache
    if use_cache:
        rounded_start = _round_loc(start_loc)
        cache_key = (rounded_start, order_ids, picked_up_frozen)
        if cache_key in _tsp_cache:
            return _tsp_cache[cache_key]

    # Create all required stops and track pickup indices for precedence checking
    all_stops: List[Stop] = []
    pickup_idx: Dict[str, int] = {}  # order_id -> index of its pickup stop
    
    for order in orders:
        # Only add pickup stop if not already in vehicle
        if order.order_id not in already_picked_up_ids:
            pickup_idx[order.order_id] = len(all_stops)
            all_stops.append(Stop(
                location=order.pickup_loc, 
                stop_type='PICKUP', 
                order_id=order.order_id
            ))
        all_stops.append(Stop(
            location=order.dropoff_loc, 
            stop_type='DROPOFF', 
            order_id=order.order_id
        ))
    
    n = len(all_stops)
    if n == 0:
        return [], 0.0
    
    # Precompute all distances (avoid repeated get_distance calls)
    dist_from_start: List[float] = []
    for stop in all_stops:
        dist_from_start.append(utils.get_distance(
            start_loc[0], start_loc[1],
            stop.location[0], stop.location[1]
        ))
    
    dist: List[List[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = utils.get_distance(
                all_stops[i].location[0], all_stops[i].location[1],
                all_stops[j].location[0], all_stops[j].location[1]
            )
            dist[i][j] = d
            dist[j][i] = d
    
    # Precompute which stops are dropoffs and their required pickup indices
    # -1 means no pickup required (either it's a pickup, or already picked up)
    required_pickup: List[int] = []
    for i, stop in enumerate(all_stops):
        if stop.stop_type == 'PICKUP':
            required_pickup.append(-1)  # Pickups have no prerequisite
        else:
            # Dropoff: need to check if pickup was visited
            order_id = stop.order_id
            if order_id in already_picked_up_ids:
                required_pickup.append(-1)  # Already picked up, no constraint
            else:
                required_pickup.append(pickup_idx[order_id])
    
    # ============================================================
    # HELD-KARP DYNAMIC PROGRAMMING
    # ============================================================
    # dp[mask][i] = minimum distance to visit all stops in 'mask', ending at stop i
    # mask is a bitmask where bit j is set if stop j has been visited
    
    INF = float('inf')
    full_mask = (1 << n) - 1
    
    # Initialize DP table
    dp: List[List[float]] = [[INF] * n for _ in range(1 << n)]
    parent: List[List[int]] = [[-1] * n for _ in range(1 << n)]
    
    # Base case: visit first stop directly from start
    for i in range(n):
        req = required_pickup[i]
        if req == -1:  # Can visit this stop first (no prerequisite)
            dp[1 << i][i] = dist_from_start[i]
    
    # Fill DP table in order of increasing mask size
    for mask in range(1, 1 << n):
        for last in range(n):
            if dp[mask][last] == INF:
                continue
            if not (mask & (1 << last)):
                continue  # 'last' must be in mask
            
            # Try extending to each unvisited stop
            for nxt in range(n):
                if mask & (1 << nxt):
                    continue  # Already visited
                
                # Check precedence constraint
                req = required_pickup[nxt]
                if req != -1 and not (mask & (1 << req)):
                    continue  # Pickup not yet visited, can't do this dropoff
                
                new_mask = mask | (1 << nxt)
                new_dist = dp[mask][last] + dist[last][nxt]
                
                if new_dist < dp[new_mask][nxt]:
                    dp[new_mask][nxt] = new_dist
                    parent[new_mask][nxt] = last
    
    # Find the best final state (all stops visited)
    best_dist = INF
    best_last = -1
    for i in range(n):
        if dp[full_mask][i] < best_dist:
            best_dist = dp[full_mask][i]
            best_last = i
    
    if best_last == -1 or best_dist == INF:
        return [], 0.0
    
    # Reconstruct the optimal path by following parent pointers
    path_indices: List[int] = []
    mask = full_mask
    curr = best_last
    
    while curr != -1:
        path_indices.append(curr)
        prev = parent[mask][curr]
        mask = mask ^ (1 << curr)  # Remove curr from mask
        curr = prev
    
    path_indices.reverse()
    best_route_stops = [all_stops[i] for i in path_indices]
    
    # Cache the result
    if use_cache:
        _tsp_cache[cache_key] = (best_route_stops, best_dist)
    
    return best_route_stops, best_dist


class DispatchEngine:
    """
    Orchestrates order-to-driver assignment using various strategies.
    
    The dispatch engine is the "auctioneer" in our Market-Based Task Allocation system:
    - It announces orders (or bundles) to eligible drivers
    - Drivers submit bids (costs)
    - The engine awards orders to the lowest bidder
    
    Strategies:
        baseline: Simple nearest-neighbor greedy assignment
        sequential: Sequential bidding on individual orders
        combinatorial: Bidding on optimized order bundles 
    """

    def _assign_bundle_to_driver(
        self, 
        driver: Driver, 
        bundle: Bundle, 
        current_time
    ) -> None:
        """
        Assign a bundle of orders to a driver.
        
        Updates driver state:
        - Sets assigned orders
        - Updates route and stop index
        - Calculates arrival time at first stop
        - Marks orders as ASSIGNED
        
        Args:
            driver: The driver receiving the assignment
            bundle: The bundle of orders being assigned
            current_time: Current simulation time
        """
        # Update driver's orders (replace to avoid duplicates)
        driver.assigned_orders = list(bundle.orders)
        driver.status = DriverStatus.ACCRUING
        driver.route = bundle.route_sequence
        driver.current_stop_index = 0

        # Calculate arrival at first stop using road travel time
        first_stop = driver.route[0]
        travel_time = utils.get_travel_time(
            driver.current_loc[0], driver.current_loc[1],
            first_stop.location[0], first_stop.location[1]
        )
        driver.arrival_time_at_next_stop = utils.add_minutes_to_time(current_time, travel_time)
        
        # Mark all orders as assigned
        for order in bundle.orders:
            order.status = OrderStatus.ASSIGNED

    def run_baseline(
        self, 
        drivers: List[Driver], 
        orders: List[Order], 
        current_time
    ) -> Tuple[List[Order], float]:
        """
        Baseline greedy dispatch: assign each order to nearest idle driver.
        
        This is the "dumb" strategy for comparison:
        - No bundling - each order gets its own driver
        - No optimization - just nearest neighbor
        - No dynamic re-routing
        
        Args:
            drivers: Available fleet
            orders: Orders to dispatch
            current_time: Current simulation time
            
        Returns:
            Tuple of (assigned_orders, total_distance_km)
        """
        assigned_orders: List[Order] = []
        total_distance_in_tick: float = 0.0
        
        # Only consider idle, available drivers
        idle_drivers = [
            d for d in drivers 
            if d.status == DriverStatus.IDLE and d.available_from <= current_time
        ]
        
        for order in orders:
            if not idle_drivers:
                break  # No available drivers

            # Find nearest driver
            best_driver: Optional[Driver] = None
            min_dist_to_pickup: float = float('inf')

            for driver in idle_drivers:
                dist = utils.get_distance(
                    driver.current_loc[0], driver.current_loc[1],
                    order.pickup_loc[0], order.pickup_loc[1]
                )
                if dist < min_dist_to_pickup:
                    min_dist_to_pickup = dist
                    best_driver = driver
            
            if best_driver is not None:
                # Create simple P1 -> D1 route
                pickup_stop = Stop(
                    location=order.pickup_loc, 
                    stop_type='PICKUP', 
                    order_id=order.order_id
                )
                dropoff_stop = Stop(
                    location=order.dropoff_loc, 
                    stop_type='DROPOFF', 
                    order_id=order.order_id
                )
                route = [pickup_stop, dropoff_stop]

                dist_pickup_to_dropoff = utils.get_distance(
                    order.pickup_loc[0], order.pickup_loc[1],
                    order.dropoff_loc[0], order.dropoff_loc[1]
                )
                full_route_dist = min_dist_to_pickup + dist_pickup_to_dropoff
                
                bundle = Bundle(
                    orders=[order], 
                    route_sequence=route, 
                    total_distance=full_route_dist
                )
                
                self._assign_bundle_to_driver(best_driver, bundle, current_time)
                
                assigned_orders.append(order)
                total_distance_in_tick += full_route_dist
                idle_drivers.remove(best_driver)

        return assigned_orders, total_distance_in_tick

    def run_sequential(
        self, 
        drivers: List[Driver], 
        new_orders: List[Order], 
        current_time
    ) -> Tuple[List[Order], float]:
        """
        Sequential market-based dispatch with MARGINAL COST bidding.
        
        For each order, eligible drivers bid based on marginal cost of
        adding the order to their current route. Lowest bidder wins.
        
        Key Innovation: Drivers bid on MARGINAL cost (additional distance),
        not total cost. This makes bundling attractive when orders are nearby.
        
        Eligible drivers:
        - IDLE: Available and waiting for orders
        - ACCRUING: Already has orders but still picking up. Can take more.
        - DELIVERING: Route locked, cannot participate
        
        Args:
            drivers: Available fleet
            new_orders: New orders to dispatch
            current_time: Current simulation time
            
        Returns:
            Tuple of (assigned_orders, total_marginal_distance_km)
        """
        # Clear TSP cache at start of dispatch cycle (fresh state)
        _clear_tsp_cache()
        
        assigned_orders: List[Order] = []
        total_distance_in_tick: float = 0.0
        
        # Track existing route distances for marginal cost calculation
        driver_existing_distances: Dict[str, float] = {}
        for driver in drivers:
            if driver.status != DriverStatus.IDLE and driver.assigned_orders:
                already_picked_up = [o for o in driver.assigned_orders if o.status == OrderStatus.PICKED_UP]
                _, existing_dist = find_optimal_route(driver.current_loc, driver.assigned_orders, already_picked_up)
                driver_existing_distances[driver.driver_id] = existing_dist
            else:
                driver_existing_distances[driver.driver_id] = 0.0
        
        # Build eligible driver list
        eligible_drivers: List[Driver] = []
        for d in drivers:
            if d.status == DriverStatus.DELIVERING:
                continue  # Locked route
            
            if d.status == DriverStatus.IDLE:
                if d.available_from <= current_time:
                    eligible_drivers.append(d)
            elif d.status == DriverStatus.ACCRUING:
                if len(d.assigned_orders) < d.capacity:
                    eligible_drivers.append(d)

        for order in new_orders:
            best_bid: float = float('inf')
            best_driver_for_order: Optional[Driver] = None
            best_bundle_for_order: Optional[Bundle] = None
            best_marginal_distance: float = 0.0

            for driver in eligible_drivers:
                # Check capacity
                potential_orders = driver.assigned_orders + [order]
                if len(potential_orders) > driver.capacity:
                    continue

                # Determine already picked up orders
                already_picked_up = [
                    o for o in driver.assigned_orders 
                    if o.status == OrderStatus.PICKED_UP
                ]
                
                # Calculate optimal route from current location
                route_sequence, total_distance = find_optimal_route(
                    driver.current_loc, potential_orders, already_picked_up
                )
                if not route_sequence:
                    continue

                new_bundle = Bundle(
                    orders=potential_orders, 
                    route_sequence=route_sequence, 
                    total_distance=total_distance
                )
                
                # Pass existing route distance for MARGINAL cost calculation
                existing_dist = driver_existing_distances.get(driver.driver_id, 0.0)
                bid = scoring.calculate_trip_cost(driver, new_bundle, current_time, existing_dist)
                marginal_dist = total_distance - existing_dist

                if bid < best_bid:
                    best_bid = bid
                    best_driver_for_order = driver
                    best_bundle_for_order = new_bundle
                    best_marginal_distance = marginal_dist
            
            if best_driver_for_order and best_bundle_for_order:
                driver = best_driver_for_order
                
                self._assign_bundle_to_driver(driver, best_bundle_for_order, current_time)
                
                order.status = OrderStatus.ASSIGNED
                assigned_orders.append(order)
                
                # Track marginal distance added
                total_distance_in_tick += best_marginal_distance
                driver_existing_distances[driver.driver_id] = best_bundle_for_order.total_distance

                # Remove from eligible if at capacity
                if len(driver.assigned_orders) >= driver.capacity:
                    if driver in eligible_drivers:
                        eligible_drivers.remove(driver)
            else:
                # FALLBACK: If no valid bid (all return inf due to time constraint),
                # assign to nearest IDLE driver anyway (better late than never)
                idle_drivers = [d for d in eligible_drivers if d.status == DriverStatus.IDLE]
                if idle_drivers:
                    best_fallback_driver: Optional[Driver] = None
                    min_dist: float = float('inf')
                    for driver in idle_drivers:
                        dist = utils.get_distance(
                            driver.current_loc[0], driver.current_loc[1],
                            order.pickup_loc[0], order.pickup_loc[1]
                        )
                        if dist < min_dist:
                            min_dist = dist
                            best_fallback_driver = driver
                    
                    if best_fallback_driver:
                        pickup_stop = Stop(location=order.pickup_loc, stop_type='PICKUP', order_id=order.order_id)
                        dropoff_stop = Stop(location=order.dropoff_loc, stop_type='DROPOFF', order_id=order.order_id)
                        route = [pickup_stop, dropoff_stop]
                        
                        dist_pickup_to_dropoff = utils.get_distance(
                            order.pickup_loc[0], order.pickup_loc[1],
                            order.dropoff_loc[0], order.dropoff_loc[1]
                        )
                        full_route_dist = min_dist + dist_pickup_to_dropoff
                        
                        bundle = Bundle(orders=[order], route_sequence=route, total_distance=full_route_dist)
                        self._assign_bundle_to_driver(best_fallback_driver, bundle, current_time)
                        
                        order.status = OrderStatus.ASSIGNED
                        assigned_orders.append(order)
                        total_distance_in_tick += full_route_dist
                        driver_existing_distances[best_fallback_driver.driver_id] = full_route_dist
                        
                        if len(best_fallback_driver.assigned_orders) >= best_fallback_driver.capacity:
                            if best_fallback_driver in eligible_drivers:
                                eligible_drivers.remove(best_fallback_driver)

        return assigned_orders, total_distance_in_tick

    def run_combinatorial(
        self, 
        drivers: List[Driver], 
        orders: List[Order], 
        current_time
    ) -> Tuple[List[Order], float]:
        """
        Combinatorial dispatch using spatial clustering for bundle generation.
        
        Uses graph-cut based spatial clustering to generate bundles efficiently:
        1. Generate bundles using recursive max-cut on order locations
        2. This produces O(n log n) bundles instead of O(n choose k)
        3. Bundles are spatially coherent (nearby pickups grouped together)
        4. Drivers bid on generated bundles using MARGINAL cost
        5. Greedy assignment preferring larger bundles
        
        Args:
            drivers: Available fleet
            orders: Orders to dispatch
            current_time: Current simulation time
            
        Returns:
            Tuple of (assigned_orders, total_marginal_distance_km)
        """
        # Clear TSP cache at start of dispatch cycle (fresh state)
        _clear_tsp_cache()
        
        assigned_orders_in_cycle: List[Order] = []
        total_distance_in_tick: float = 0.0
        
        # Track existing route distances for marginal cost calculation
        driver_existing_distances: Dict[str, float] = {}
        for driver in drivers:
            if driver.status != DriverStatus.IDLE and driver.assigned_orders:
                already_picked_up = [o for o in driver.assigned_orders if o.status == OrderStatus.PICKED_UP]
                _, existing_dist = find_optimal_route(driver.current_loc, driver.assigned_orders, already_picked_up)
                driver_existing_distances[driver.driver_id] = existing_dist
            else:
                driver_existing_distances[driver.driver_id] = 0.0
        
        # Build eligible driver list
        eligible_drivers: List[Driver] = []
        for d in drivers:
            if d.status == DriverStatus.DELIVERING:
                continue
            if d.status == DriverStatus.IDLE:
                if d.available_from <= current_time:
                    eligible_drivers.append(d)
            elif d.status == DriverStatus.ACCRUING:
                if len(d.assigned_orders) < d.capacity:
                    eligible_drivers.append(d)
        
        pending_orders = list(orders)
        
        # Build distance matrix ONCE for all pending orders (optimization)
        all_order_distances = _build_distance_matrix(pending_orders) if pending_orders else {}

        while eligible_drivers and pending_orders:
            # Generate bundles using spatial clustering (pass prebuilt distances)
            candidate_bundles = generate_spatial_bundles(
                pending_orders, 
                max_bundle_size=config.MAX_BUNDLE_SIZE,
                prebuilt_distances=all_order_distances
            )
            
            # Collect all possible (cost, driver, bundle, new_orders, marginal_dist) tuples
            all_possible_assignments: List[Tuple[float, Driver, Bundle, List[Order], float]] = []

            for order_combo in candidate_bundles:
                # Have each eligible driver bid on this bundle
                for driver in eligible_drivers:
                    # Check capacity
                    total_orders = len(driver.assigned_orders) + len(order_combo)
                    if total_orders > driver.capacity:
                        continue

                    # Combine existing and new orders
                    all_orders = driver.assigned_orders + list(order_combo)
                    
                    # Handle already picked up orders
                    already_picked_up = [
                        o for o in driver.assigned_orders 
                        if o.status == OrderStatus.PICKED_UP
                    ]

                    route_sequence, total_distance = find_optimal_route(
                        driver.current_loc, all_orders, already_picked_up
                    )
                    if not route_sequence:
                        continue

                    bundle = Bundle(
                        orders=all_orders, 
                        route_sequence=route_sequence, 
                        total_distance=total_distance
                    )
                    
                    # Pass existing route distance for MARGINAL cost calculation
                    existing_dist = driver_existing_distances.get(driver.driver_id, 0.0)
                    cost = scoring.calculate_trip_cost(driver, bundle, current_time, existing_dist)
                    marginal_distance = total_distance - existing_dist
                    
                    if cost != float('inf'):
                        all_possible_assignments.append(
                            (cost, driver, bundle, list(order_combo), marginal_distance)
                        )

            if not all_possible_assignments:
                # FALLBACK: Assign remaining orders to ANY eligible driver
                # This handles cases where time constraint rejects all bundles
                orders_assigned_in_fallback: List[Order] = []
                
                for order in pending_orders[:]:
                    if not eligible_drivers:
                        break
                    
                    best_fallback_driver: Optional[Driver] = None
                    min_dist: float = float('inf')
                    
                    # First try IDLE drivers
                    idle_drivers = [d for d in eligible_drivers if d.status == DriverStatus.IDLE]
                    for driver in idle_drivers:
                        if len(driver.assigned_orders) >= driver.capacity:
                            continue
                        dist = utils.get_distance(
                            driver.current_loc[0], driver.current_loc[1],
                            order.pickup_loc[0], order.pickup_loc[1]
                        )
                        if dist < min_dist:
                            min_dist = dist
                            best_fallback_driver = driver
                    
                    # If no IDLE driver, try ACCRUING drivers
                    if not best_fallback_driver:
                        accruing_drivers = [d for d in eligible_drivers if d.status == DriverStatus.ACCRUING]
                        for driver in accruing_drivers:
                            if len(driver.assigned_orders) >= driver.capacity:
                                continue
                            dist = utils.get_distance(
                                driver.current_loc[0], driver.current_loc[1],
                                order.pickup_loc[0], order.pickup_loc[1]
                            )
                            if dist < min_dist:
                                min_dist = dist
                                best_fallback_driver = driver
                    
                    if best_fallback_driver:
                        if best_fallback_driver.status == DriverStatus.IDLE:
                            # Create simple P->D route
                            pickup_stop = Stop(location=order.pickup_loc, stop_type='PICKUP', order_id=order.order_id)
                            dropoff_stop = Stop(location=order.dropoff_loc, stop_type='DROPOFF', order_id=order.order_id)
                            route = [pickup_stop, dropoff_stop]
                            
                            dist_pickup_to_dropoff = utils.get_distance(
                                order.pickup_loc[0], order.pickup_loc[1],
                                order.dropoff_loc[0], order.dropoff_loc[1]
                            )
                            full_route_dist = min_dist + dist_pickup_to_dropoff
                            
                            bundle = Bundle(orders=[order], route_sequence=route, total_distance=full_route_dist)
                            self._assign_bundle_to_driver(best_fallback_driver, bundle, current_time)
                            total_distance_in_tick += full_route_dist
                        else:
                            # For ACCRUING drivers, add order to their existing route
                            all_orders = best_fallback_driver.assigned_orders + [order]
                            already_picked_up = [o for o in best_fallback_driver.assigned_orders if o.status == OrderStatus.PICKED_UP]
                            
                            route_sequence, total_distance = find_optimal_route(
                                best_fallback_driver.current_loc, all_orders, already_picked_up
                            )
                            
                            if route_sequence:
                                existing_dist = driver_existing_distances.get(best_fallback_driver.driver_id, 0.0)
                                marginal_dist = total_distance - existing_dist
                                
                                bundle = Bundle(orders=all_orders, route_sequence=route_sequence, total_distance=total_distance)
                                self._assign_bundle_to_driver(best_fallback_driver, bundle, current_time)
                                total_distance_in_tick += marginal_dist
                                driver_existing_distances[best_fallback_driver.driver_id] = total_distance
                            else:
                                continue
                        
                        order.status = OrderStatus.ASSIGNED
                        assigned_orders_in_cycle.append(order)
                        orders_assigned_in_fallback.append(order)
                        
                        if len(best_fallback_driver.assigned_orders) >= best_fallback_driver.capacity:
                            if best_fallback_driver in eligible_drivers:
                                eligible_drivers.remove(best_fallback_driver)
                
                # Remove assigned orders from pending
                for order in orders_assigned_in_fallback:
                    if order in pending_orders:
                        pending_orders.remove(order)
                
                if not orders_assigned_in_fallback:
                    break
                else:
                    continue

            # GREEDY SELECTION with BUNDLE SIZE TIE-BREAKER
            # Primary: lowest cost per order
            # Secondary: prefer LARGER bundles (reduces drivers needed)
            best_cost, best_driver, best_bundle, new_orders_in_bundle, marginal_dist = min(
                all_possible_assignments, 
                key=lambda x: (x[0], -len(x[3]))  # (cost, -bundle_size)
            )

            self._assign_bundle_to_driver(best_driver, best_bundle, current_time)
            
            # Track only marginal distance added
            total_distance_in_tick += marginal_dist
            driver_existing_distances[best_driver.driver_id] = best_bundle.total_distance

            # Remove assigned orders from pending
            for order in new_orders_in_bundle:
                assigned_orders_in_cycle.append(order)
                if order in pending_orders:
                    pending_orders.remove(order)
            
            # Remove driver if at capacity
            if len(best_driver.assigned_orders) >= best_driver.capacity:
                if best_driver in eligible_drivers:
                    eligible_drivers.remove(best_driver)
        
        return assigned_orders_in_cycle, total_distance_in_tick
