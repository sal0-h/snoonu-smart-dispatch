# snoonu-smart-dispatch/src/models.py
"""
Core domain models for the Snoonu Last-Mile Delivery Simulation.

This module defines the fundamental data structures used throughout the simulation:
- Order: Represents a delivery request from pickup to dropoff
- Driver: Represents a courier with vehicle, capacity, and current state
- Stop: A single point in a driver's route (pickup or dropoff)
- Bundle: A collection of orders assigned to a driver with an optimized route
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from enum import Enum
from typing import List, Tuple, Optional


class OrderStatus(Enum):
    """Lifecycle states for an order in the delivery system."""
    PENDING = "PENDING"      # Order created, awaiting assignment
    ASSIGNED = "ASSIGNED"    # Assigned to a driver, not yet picked up
    PICKED_UP = "PICKED_UP"  # Driver has collected the order
    DELIVERED = "DELIVERED"  # Successfully delivered to customer
    FAILED = "FAILED"        # Delivery failed (timeout, etc.)


class DriverStatus(Enum):
    """
    States for a driver in the Market-Based Task Allocation system.
    
    The driver state machine:
    - IDLE: Available and can bid on new orders
    - ACCRUING: Has orders assigned, still picking up. Can accept more orders.
    - DELIVERING: All pickups complete, route is locked. Cannot accept new orders.
    """
    IDLE = "IDLE"
    ACCRUING = "ACCRUING"
    DELIVERING = "DELIVERING"


@dataclass
class Stop:
    """
    Represents a single stop (pickup or dropoff) in a driver's route.
    
    Attributes:
        location: (latitude, longitude) coordinates of the stop
        stop_type: Either 'PICKUP' or 'DROPOFF'
        order_id: The order this stop belongs to
    """
    location: Tuple[float, float]
    stop_type: str  # 'PICKUP' or 'DROPOFF'
    order_id: str

    def __hash__(self) -> int:
        return hash((self.location, self.stop_type, self.order_id))

    def __repr__(self) -> str:
        return f"Stop({self.stop_type}:{self.order_id})"


@dataclass
class Order:
    """
    Represents a delivery order from restaurant to customer.
    
    Attributes:
        order_id: Unique identifier
        pickup_lat/lng: Restaurant location
        dropoff_lat/lng: Customer location
        created_time: When the order was placed
        deadline: Latest acceptable delivery time
        estimated_delivery_time_min: Expected delivery duration in minutes
        status: Current lifecycle state
        pickup_time: When the order was picked up (for KPI calculation)
        dropoff_time: When the order was delivered (for KPI calculation)
    """
    order_id: str
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    created_time: time
    deadline: time
    estimated_delivery_time_min: int
    status: OrderStatus = OrderStatus.PENDING
    
    # Timestamps for KPI calculation
    pickup_time: Optional[time] = None
    dropoff_time: Optional[time] = None

    @property
    def pickup_loc(self) -> Tuple[float, float]:
        """Returns the pickup location as a (lat, lng) tuple."""
        return (self.pickup_lat, self.pickup_lng)

    @property
    def dropoff_loc(self) -> Tuple[float, float]:
        """Returns the dropoff location as a (lat, lng) tuple."""
        return (self.dropoff_lat, self.dropoff_lng)

    def __repr__(self) -> str:
        return f"Order({self.order_id}, {self.status.value})"


@dataclass
class Driver:
    """
    Represents a courier/driver in the delivery fleet.
    
    Attributes:
        driver_id: Unique identifier
        start_lat/lng: Initial position when shift starts
        vehicle_type: 'motorbike', 'bike', or 'car'
        capacity: Maximum number of orders the driver can handle simultaneously
        available_from: When the driver's shift begins
        
    Dynamic State:
        current_lat/lng: Current position (updated during simulation)
        status: Current driver state (IDLE, ACCRUING, DELIVERING)
        assigned_orders: List of orders currently assigned to this driver
        route: Sequence of stops to visit
        current_stop_index: Index of the next stop in the route
        arrival_time_at_next_stop: Estimated arrival at next stop
    """
    driver_id: str
    start_lat: float
    start_lng: float
    vehicle_type: str
    capacity: int
    available_from: time
    
    # Dynamic state
    current_lat: float = field(init=False)
    current_lng: float = field(init=False)
    status: DriverStatus = DriverStatus.IDLE
    assigned_orders: List[Order] = field(default_factory=list)

    # Route management
    route: List[Stop] = field(default_factory=list)
    current_stop_index: int = -1
    arrival_time_at_next_stop: Optional[time] = None

    def __post_init__(self) -> None:
        """Initialize dynamic position from starting position."""
        self.current_lat = self.start_lat
        self.current_lng = self.start_lng
        self.arrival_time_at_next_stop = self.available_from
    
    @property
    def current_loc(self) -> Tuple[float, float]:
        """Returns the current location as a (lat, lng) tuple."""
        return (self.current_lat, self.current_lng)

    def __repr__(self) -> str:
        return f"Driver({self.driver_id}, {self.status.value}, orders={len(self.assigned_orders)})"


@dataclass
class Bundle:
    """
    Represents a potential job bundle for a driver.
    
    In our Market-Based Task Allocation system, bundles are "contracts" that drivers bid on.
    A bundle contains one or more orders and a proposed route sequence.
    
    Attributes:
        orders: List of orders in this bundle
        route_sequence: Optimized sequence of stops to complete all orders
        total_distance: Total travel distance for this route in km
    """
    orders: List[Order]
    route_sequence: List[Stop]
    total_distance: float = 0.0
    
    @property
    def num_orders(self) -> int:
        """Returns the number of orders in this bundle."""
        return len(self.orders)

    @property
    def order_ids(self) -> List[str]:
        """Returns list of order IDs in this bundle."""
        return [o.order_id for o in self.orders]

    def __repr__(self) -> str:
        return f"Bundle(orders={self.order_ids}, dist={self.total_distance:.2f}km)"
