# snoonu-smart-dispatch/src/scoring.py
"""
Scoring functions for the Market-Based Task Allocation bidding system.

This module implements the cost function that drivers use to bid on orders.
The bidding system enables:
- Competitive allocation of orders to the most suitable drivers
- Intelligent bundling through cost incentives
- Fair workload distribution across the fleet

Key Design Principles:
1. Lower score = better bid = higher priority
2. Bundled orders are cheaper per-order than single orders
3. Time-sensitive orders have higher costs if delayed
"""

from __future__ import annotations

from datetime import time, datetime, timedelta
from typing import Dict

from . import config, utils
from .models import Driver, Bundle, Order, DriverStatus


# Vehicle penalty lookup table
VEHICLE_PENALTIES: Dict[str, float] = {
    "motorbike": config.PENALTY_MOTORBIKE,
    "bike": config.PENALTY_BIKE,
    "car": config.PENALTY_CAR,
}


def get_vehicle_penalty(vehicle_type: str) -> float:
    """
    Get the cost penalty multiplier for a vehicle type.
    
    Motorbikes are preferred for food delivery due to:
    - Faster navigation through traffic
    - Easier parking at pickup/dropoff
    - Lower operating costs
    
    Args:
        vehicle_type: One of 'motorbike', 'bike', 'car'
        
    Returns:
        Penalty multiplier (1.0 for motorbike, higher for others)
    """
    return VEHICLE_PENALTIES.get(vehicle_type.lower(), 1.0)


def calculate_trip_cost(
    driver: Driver, 
    bundle: Bundle, 
    current_time: time,
    existing_route_distance: float = 0.0
) -> float:
    """
    Calculate the cost for a driver to take on a bundle of orders.
    
    This is the core bidding function in our Market-Based Task Allocation system.
    Drivers "bid" by computing their cost to complete a bundle. The dispatcher
    assigns bundles to the lowest-cost bidder.
    
    CRITICAL: Uses MARGINAL cost (not total cost) for bundling to work properly.
    Marginal cost = new route distance - existing route distance.
    This rewards drivers who are already on route nearby.
    
    The cost function considers:
    1. Distance: MARGINAL travel distance (key for bundling!)
    2. Delay: Penalties for late deliveries (capped)
    3. Fixed Cost: Fleet management overhead (encourages bundling)
    4. Vehicle Type: Preference for efficient vehicles
    5. Bundle Size: Discounts for multi-order bundles
    
    Args:
        driver: The driver submitting the bid
        bundle: The bundle of orders being bid on
        current_time: Current simulation time
        existing_route_distance: Distance of driver's current route (for marginal calc)
        
    Returns:
        Cost score (lower is better), or float('inf') if infeasible
    """
    # 1. Capacity Constraint
    if bundle.num_orders > driver.capacity:
        return float('inf')

    # 2. Determine trip start time and location
    # Always calculate from driver's current position
    dummy_date = datetime.now().date()
    start_datetime = datetime.combine(dummy_date, current_time)
    start_loc = driver.current_loc
    
    # 3. Traverse the proposed route, calculating arrival times and delays
    total_delay_mins: float = 0.0
    time_at_current_loc = start_datetime
    last_loc = start_loc

    # Map order_id -> Order for deadline checking
    order_map: Dict[str, Order] = {order.order_id: order for order in bundle.orders}

    for stop in bundle.route_sequence:
        # Calculate travel time from last location using road network
        travel_time = utils.get_travel_time(
            last_loc[0], last_loc[1], 
            stop.location[0], stop.location[1]
        )
        time_at_current_loc += timedelta(minutes=travel_time)

        # Add service time at stop
        time_at_current_loc += timedelta(minutes=config.SERVICE_TIME_MINS)
        
        # Check delays for dropoff stops
        if stop.stop_type == 'DROPOFF':
            order = order_map[stop.order_id]
            
            # Calculate actual delivery duration
            order_created_datetime = datetime.combine(dummy_date, order.created_time)
            actual_delivery_duration = (time_at_current_loc - order_created_datetime).total_seconds() / 60
            
            # HARD CONSTRAINT: Reject if delivery would exceed MAX_DELIVERY_TIME_MINS
            if actual_delivery_duration > config.MAX_DELIVERY_TIME_MINS:
                return float('inf')
            
            # Delay vs estimated time (capped to prevent extreme values)
            delay = actual_delivery_duration - order.estimated_delivery_time_min
            if delay > 0:
                capped_delay = min(delay, 20)  # Cap at 20 min
                total_delay_mins += capped_delay

        last_loc = stop.location

    # 4. Calculate MARGINAL distance (key innovation for bundling!)
    # For idle drivers: marginal = total (no existing route)
    # For busy drivers: marginal = additional distance only
    marginal_distance = bundle.total_distance - existing_route_distance
    
    # 5. Calculate base score using marginal distance
    distance_cost = config.W_DISTANCE * marginal_distance
    delay_cost = config.W_DELAY * total_delay_mins

    base_score = distance_cost + delay_cost

    # 6. Apply vehicle penalty
    score_with_vehicle = base_score * get_vehicle_penalty(driver.vehicle_type)
    
    # 7. Normalize by number of orders - makes bundles more attractive
    # This makes a 2-order bundle at 10km = 5km/order vs 1-order at 6km = 6km/order
    cost_per_order = score_with_vehicle / bundle.num_orders
    
    # 8. Apply bundling discount to incentivize multi-order bundles
    # Each additional order reduces cost by BUNDLE_DISCOUNT_PER_ORDER
    if bundle.num_orders > 1:
        bundle_discount = config.BUNDLE_DISCOUNT_PER_ORDER * (bundle.num_orders - 1)
        cost_per_order = cost_per_order * (1.0 - bundle_discount)

    return cost_per_order


def calculate_marginal_cost(
    driver: Driver,
    new_order: Order,
    current_time: time
) -> float:
    """
    Calculate the marginal cost of adding one more order to a driver's route.
    
    This is useful for sequential dispatch where we want to find the
    cheapest driver to add a single order to.
    
    Args:
        driver: The driver to evaluate
        new_order: The order to potentially add
        current_time: Current simulation time
        
    Returns:
        Marginal cost of adding this order
    """
    # Import here to avoid circular dependency
    from .dispatch import find_optimal_route
    
    # Calculate route with just the new order
    orders = driver.assigned_orders + [new_order]
    already_picked_up = [o for o in driver.assigned_orders if o.status.value == "PICKED_UP"]
    
    route_sequence, total_distance = find_optimal_route(
        driver.current_loc, orders, already_picked_up
    )
    
    if not route_sequence:
        return float('inf')
    
    bundle = Bundle(
        orders=orders,
        route_sequence=route_sequence,
        total_distance=total_distance
    )
    
    return calculate_trip_cost(driver, bundle, current_time)
