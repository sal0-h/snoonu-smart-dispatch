# snoonu-smart-dispatch/src/__init__.py

from .models import Order, Driver, Bundle, Stop, OrderStatus, DriverStatus
from .config import (
    START_TIME, 
    SIMULATION_END_TIME, 
    AVG_SPEED_KMH,
    MAX_BUNDLE_SIZE,
    BATCH_WINDOW_MINS,
)
from .simulation import Simulation
from .dispatch import DispatchEngine, find_optimal_route
from .scoring import calculate_trip_cost, get_vehicle_penalty

__version__ = "1.0.0"
__author__ = "Snoonu Hackathon Team"

__all__ = [
    # Models
    "Order",
    "Driver", 
    "Bundle",
    "Stop",
    "OrderStatus",
    "DriverStatus",
    # Core
    "Simulation",
    "DispatchEngine",
    # Functions
    "find_optimal_route",
    "calculate_trip_cost",
    "get_vehicle_penalty",
    # Config
    "START_TIME",
    "SIMULATION_END_TIME",
    "AVG_SPEED_KMH",
    "MAX_BUNDLE_SIZE",
    "BATCH_WINDOW_MINS",
]
