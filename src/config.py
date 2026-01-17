# snoonu-smart-dispatch/src/config.py
"""
Configuration parameters for the Snoonu Last-Mile Delivery Simulation.

This module centralizes all tunable parameters, making it easy to:
- Adjust simulation behavior
- Fine-tune dispatch strategies
- Configure scoring weights for the bidding system

All parameters are documented with their purpose and typical value ranges.
"""

from datetime import datetime, time
from typing import Final

# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================

START_TIME: Final[time] = datetime.strptime("17:00:00", "%H:%M:%S").time()
"""Simulation start time (typically evening rush hour for food delivery)."""

SIMULATION_END_TIME: Final[time] = datetime.strptime("22:00:00", "%H:%M:%S").time()
"""Simulation end time. All orders should be delivered by this time."""

SIMULATION_SPEED_MINUTES: int = 1
"""Time advance per tick. Higher = faster simulation, lower = more granular."""

# =============================================================================
# PHYSICS AND TIME CONSTANTS
# =============================================================================

AVG_SPEED_KMH: float = 35.0
"""Average vehicle speed in km/h. Accounts for traffic, stops, etc."""

SERVICE_TIME_MINS: float = 5.0
"""Time spent at each stop for parking, handover, etc."""

# =============================================================================
# DISPATCH STRATEGY PARAMETERS
# =============================================================================

HIGH_LOAD_THRESHOLD: float = 2.0
"""
Orders per minute threshold for switching to combinatorial mode.
When order rate exceeds this, the system uses more sophisticated bundling.
"""

COMBINATORIAL_WINDOW_MINS: int = 5
"""Time window (in minutes) for calculating the rolling order rate."""

# =============================================================================
# SCORING WEIGHTS AND PENALTIES
# =============================================================================
# These weights determine the "cost" of a delivery in the bidding system.
# Lower cost = better bid = higher priority for assignment.

W_DISTANCE: float = 1.0
"""Weight for total distance traveled. Higher = prefer shorter routes."""

W_DELAY: float = 1.5
"""Weight for delivery delay. Higher = prioritize on-time delivery."""

BUNDLE_DISCOUNT_PER_ORDER: float = 0.25
"""
Per-order discount for multi-order bundles (0.0 - 1.0).
0.25 means 25% cost reduction per additional order in a bundle.
This incentivizes drivers to take bundles, improving fleet efficiency.
"""

DISPATCH_FIXED_COST: float = 1.5
"""
Fixed cost (in km equivalent) for activating a driver.
This represents fleet management overhead and encourages bundling
by amortizing the fixed cost across multiple orders.
"""

# =============================================================================
# VEHICLE PENALTIES
# =============================================================================
# Penalty multipliers for different vehicle types.
# Lower = preferred. Motorbikes are ideal for food delivery.

PENALTY_MOTORBIKE: float = 1.0
"""Baseline penalty for motorbikes (most efficient for food delivery)."""

PENALTY_BIKE: float = 1.2
"""Penalty for bicycles (slower, limited range)."""

PENALTY_CAR: float = 1.4
"""Penalty for cars (less maneuverable, parking challenges)."""

# =============================================================================
# BUNDLE GENERATION
# =============================================================================

MAX_BUNDLE_SIZE: int = 2
"""
Maximum orders per bundle. Keep low for performance.
With N orders, combinatorial complexity is O(N choose MAX_BUNDLE_SIZE).
"""

MAX_PICKUP_DISTANCE_KM: float = 5.0
"""
Maximum distance between pickups for bundling eligibility (graph-cut).
Orders with pickups further apart won't be bundled together.
This is a performance optimization to prune the search space.
"""

MAX_BUNDLE_PICKUP_DISTANCE_KM: float = 1.8
"""
Maximum distance between pickups for combinatorial bundle eligibility.
Stricter than MAX_PICKUP_DISTANCE_KM for brute-force combinations.
Orders with pickups within this radius are considered bundle-worthy.
"""

MAX_DELIVERY_TIME_MINS: float = 52.0
"""
HARD CONSTRAINT: Maximum delivery time from order creation.
Bundles that would exceed this time are rejected outright.
Prevents SLA violations even if bundling would be otherwise efficient.
"""

# =============================================================================
# BATCHING PARAMETERS
# =============================================================================

BATCH_WINDOW_MINS: float = 1.0
"""
Time window to accumulate orders before dispatching.
Longer = better bundling opportunities, but increased latency.
This is the key trade-off between efficiency and responsiveness.
"""

MIN_BATCH_SIZE: int = 1
"""Minimum orders to trigger immediate dispatch (bypasses batch window)."""

# =============================================================================
# ROAD DISTANCE (OSRM) CONFIGURATION
# =============================================================================

USE_ROAD_DISTANCE: bool = False
"""
Enable real road distance calculation via OSRM.
When True, uses actual road network distances instead of straight-line.
When False, uses Haversine (great-circle) distance.
"""

OSRM_SERVER_URL: str = "https://router.project-osrm.org"
"""
OSRM server URL. Options:
- "https://router.project-osrm.org" (public demo, rate-limited)
- "http://localhost:5000" (local Docker instance)
"""

OSRM_TIMEOUT_SECONDS: float = 5.0
"""Timeout for OSRM API requests. Fail fast to avoid blocking simulation."""

OSRM_CACHE_SIZE: int = 10000
"""Maximum number of route results to cache. Prevents repeated API calls."""

HAVERSINE_FALLBACK_MULTIPLIER: float = 1.4
"""
Multiplier applied to Haversine distance when OSRM fails.
Typical city roads are 1.3-1.5x longer than straight-line distance.
"""
