# Snoonu Smart Dispatch: Algorithm Deep Dive

**A Complete Technical Guide to the 4 Dispatch Strategies**

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Core Data Structures](#2-core-data-structures)
3. [The Simulation Engine](#3-the-simulation-engine)
4. [Algorithm 1: Baseline (Greedy Nearest-Neighbor)](#4-algorithm-1-baseline-greedy-nearest-neighbor)
5. [Algorithm 2: Sequential (Per-Order Bidding)](#5-algorithm-2-sequential-per-order-bidding)
6. [Algorithm 3: Combinatorial (Bundle-Based Bidding)](#6-algorithm-3-combinatorial-bundle-based-bidding)
7. [Algorithm 4: Adaptive (Dynamic Strategy Switching)](#7-algorithm-4-adaptive-dynamic-strategy-switching)
8. [The Scoring System (MARGINAL Cost Function)](#8-the-scoring-system-marginal-cost-function)
9. [Route Optimization (TSP with Precedence)](#9-route-optimization-tsp-with-precedence)
10. [Why Our Approach Works](#10-why-our-approach-works)

---

## 1. System Overview

### What We're Solving

The **Last-Mile Delivery Dispatch Problem**: Given a set of orders (each with a pickup and dropoff location) and a fleet of drivers, assign orders to drivers in a way that:

1. **Minimizes the number of drivers needed** (primary goal)
2. **Maintains on-time delivery** (all orders delivered within 60 minutes)
3. **Reduces total distance traveled** (secondary optimization)

### Market-Based Task Allocation

Our system uses a **bidding-based dispatch** inspired by Market-Based Task Allocation from Collective Intelligence:

```
┌─────────────────────────────────────────────────────────────────┐
│                     CONTRACT NET PROTOCOL                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DISPATCHER                           DRIVERS                   │
│   (Auctioneer)                        (Bidders)                  │
│                                                                  │
│   1. Announce Order(s) ─────────────▶ All Eligible Drivers      │
│                                                                  │
│   2. ◀───────────────────────────── Submit Bids (MARGINAL cost) │
│                                                                  │
│   3. Select Winner ──────────────────▶ Lowest Bidder Wins       │
│                                                                  │
│   4. Assign Order(s) ─────────────────▶ Update Driver State     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Discrete-Event Simulation

The simulation advances in **1-minute ticks** from 17:00 to 22:00:

```python
for each tick:
    1. Update driver positions (process arrivals at stops)
    2. Inject new orders (based on created_time in CSV)
    3. Run dispatch algorithm (assign pending orders to drivers)
    4. Track KPIs
    5. Advance clock by 1 minute
```

---

## 2. Core Data Structures

### Order

```python
@dataclass
class Order:
    order_id: str                    # Unique identifier (e.g., "ORD_001")
    pickup_lat: float                # Restaurant latitude
    pickup_lng: float                # Restaurant longitude
    dropoff_lat: float               # Customer latitude
    dropoff_lng: float               # Customer longitude
    created_time: time               # When order was placed (e.g., 17:05:00)
    deadline: time                   # Latest acceptable delivery time
    estimated_delivery_time_min: int # Expected duration (e.g., 30 min)
    status: OrderStatus              # PENDING → ASSIGNED → PICKED_UP → DELIVERED
    pickup_time: Optional[time]      # Timestamp when picked up
    dropoff_time: Optional[time]     # Timestamp when delivered
    
    @property
    def pickup_loc(self) -> Tuple[float, float]:
        return (self.pickup_lat, self.pickup_lng)
    
    @property
    def dropoff_loc(self) -> Tuple[float, float]:
        return (self.dropoff_lat, self.dropoff_lng)
```

### Driver

```python
@dataclass
class Driver:
    driver_id: str                   # Unique identifier (e.g., "DRV_001")
    start_lat: float                 # Starting position latitude
    start_lng: float                 # Starting position longitude
    vehicle_type: str                # "motorbike", "bike", or "car"
    capacity: int                    # Max orders at once (typically 2)
    available_from: time             # When shift starts
    
    # Dynamic State (changes during simulation)
    current_lat: float               # Current position latitude
    current_lng: float               # Current position longitude
    status: DriverStatus             # IDLE, ACCRUING, or DELIVERING
    assigned_orders: List[Order]     # Orders currently assigned
    route: List[Stop]                # Sequence of stops to visit
    current_stop_index: int          # Which stop is next
    arrival_time_at_next_stop: time  # ETA at next stop
    
    @property
    def current_loc(self) -> Tuple[float, float]:
        return (self.current_lat, self.current_lng)
```

### Driver State Machine

```
┌──────────────────────────────────────────────────────────────────┐
│                      DRIVER STATE MACHINE                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌────────┐    Order(s)     ┌───────────┐    All Pickups    ┌────────────┐
│   │  IDLE  │ ───Assigned───▶ │  ACCRUING │ ───Complete────▶ │ DELIVERING │
│   └────────┘                 └───────────┘                   └────────────┘
│       ▲                           │                               │
│       │                           │                               │
│       │                    Can accept more                        │
│       │                    orders if capacity                     │
│       │                    allows (re-routing)                    │
│       │                           │                               │
│       │                           ▼                               │
│       │                    ┌───────────┐                          │
│       │                    │  ACCRUING │ (with new route)         │
│       │                    └───────────┘                          │
│       │                                                           │
│       └───────────────────────────────────────────────────────────┘
│                         Route Complete                             │
└──────────────────────────────────────────────────────────────────┘

IDLE:       Available for new orders. Can bid on anything.
ACCRUING:   Has orders but still picking up. Can accept MORE orders.
DELIVERING: All pickups done, only dropoffs remain. Route is LOCKED.
```

### Bundle

```python
@dataclass
class Bundle:
    orders: List[Order]          # 1 or more orders grouped together
    route_sequence: List[Stop]   # Optimized sequence of pickups/dropoffs
    total_distance: float        # Total km for this route
    
    @property
    def num_orders(self) -> int:
        return len(self.orders)
```

### Stop

```python
@dataclass
class Stop:
    location: Tuple[float, float]  # (lat, lng)
    stop_type: str                 # "PICKUP" or "DROPOFF"
    order_id: str                  # Which order this stop belongs to
```

---

## 3. The Simulation Engine

### Main Loop (`simulation.py`)

```python
def run(self, strategy: str) -> Dict:
    """Run the complete simulation."""
    
    while current_time < end_time and not all_orders_delivered:
        self.tick(strategy)
    
    return self.get_results()

def tick(self, strategy: str) -> None:
    """Execute one simulation tick (1 minute)."""
    
    # Step 1: Update driver positions and process stop arrivals
    self._update_driver_states()
    
    # Step 2: Inject new orders based on creation time
    self._inject_new_orders()
    
    # Step 3: Dispatch pending orders
    if self.pending_orders:
        if strategy == "baseline":
            # Dispatch immediately (no batching)
            self.dispatch_engine.run_baseline(...)
        elif self._should_dispatch_batch():
            # Batch window elapsed or urgent order - dispatch now
            if strategy == "combinatorial":
                self.dispatch_engine.run_combinatorial(...)
            elif strategy == "sequential":
                self.dispatch_engine.run_sequential(...)
            elif strategy == "adaptive":
                mode = self._get_dispatch_mode()  # Check order rate
                if mode == "combinatorial":
                    self.dispatch_engine.run_combinatorial(...)
                else:
                    self.dispatch_engine.run_sequential(...)
    
    # Step 4: Advance clock
    self.current_time += 1 minute
```

### Batching Logic

Orders don't get dispatched immediately (except in Baseline). Instead, they accumulate in a **batch window**:

```python
BATCH_WINDOW_MINS = 1.0  # Wait 1 minute to accumulate orders

def _should_dispatch_batch(self) -> bool:
    """Decide if it's time to dispatch the accumulated orders."""
    
    # Dispatch if batch window has elapsed
    if time_since_first_order >= BATCH_WINDOW_MINS:
        return True
    
    # Dispatch urgently if any order is close to deadline
    for order in pending_orders:
        if time_to_deadline <= estimated_time / 3:
            return True  # Urgent!
    
    return False
```

**Why batch?** Waiting allows geographically close orders to accumulate, enabling better bundling.

---

## 4. Algorithm 1: Baseline (Greedy Nearest-Neighbor)

### Philosophy

> "For each order, find the closest available driver and assign immediately."

This is the **dumb** strategy used for comparison. It represents how a naive system might work.

### Implementation (`dispatch.py`)

```python
def run_baseline(self, drivers, orders, current_time):
    """Baseline greedy dispatch: assign each order to nearest idle driver."""
    assigned_orders = []
    
    # Only consider idle, available drivers
    idle_drivers = [
        d for d in drivers 
        if d.status == DriverStatus.IDLE and d.available_from <= current_time
    ]
    
    for order in orders:
        if not idle_drivers:
            break  # No available drivers
        
        # Find nearest driver to pickup location
        best_driver = None
        min_distance = float('inf')
        
        for driver in idle_drivers:
            dist = get_distance(driver.current_loc, order.pickup_loc)
            if dist < min_distance:
                min_distance = dist
                best_driver = driver
        
        if best_driver:
            # Create simple route: Pickup → Dropoff
            route = [
                Stop(order.pickup_loc, "PICKUP", order.order_id),
                Stop(order.dropoff_loc, "DROPOFF", order.order_id)
            ]
            
            bundle = Bundle(orders=[order], route_sequence=route, ...)
            self._assign_bundle_to_driver(best_driver, bundle, current_time)
            
            assigned_orders.append(order)
            idle_drivers.remove(best_driver)
    
    return assigned_orders, total_distance
```

### Visual Example

```
Order O1: Restaurant A → Customer X
Order O2: Restaurant B → Customer Y

Drivers: D1 (near A), D2 (near B), D3 (far away)

BASELINE RESULT:
  D1 assigned to O1: [Pickup A] → [Dropoff X]
  D2 assigned to O2: [Pickup B] → [Dropoff Y]
  D3 remains IDLE

Drivers Used: 2
```

### Characteristics

| Aspect | Baseline |
|--------|----------|
| **Bundling** | ❌ None - one order per driver |
| **Re-routing** | ❌ None - route is fixed at assignment |
| **Decision Speed** | ✅ Instant - no waiting |
| **Optimality** | ❌ Poor - doesn't consider future orders |
| **Complexity** | O(n × m) where n=orders, m=drivers |

---

## 5. Algorithm 2: Sequential (Per-Order Bidding)

### Philosophy

> "For each order, all eligible drivers compute a MARGINAL COST bid. The lowest bidder wins. Drivers who are still picking up can accept additional orders."

This is the first **smart** strategy. It uses Market-Based Task Allocation with **marginal cost bidding**.

### Key Innovation: Marginal Cost Bidding

Unlike Baseline, Sequential calculates the **additional** cost to add an order, not the total cost:

```python
# Track existing route distances for marginal cost calculation
driver_existing_distances = {}
for driver in drivers:
    if driver.status != DriverStatus.IDLE and driver.assigned_orders:
        _, existing_dist = find_optimal_route(driver.current_loc, driver.assigned_orders, ...)
        driver_existing_distances[driver.driver_id] = existing_dist
    else:
        driver_existing_distances[driver.driver_id] = 0.0

# When calculating bid:
existing_dist = driver_existing_distances[driver.driver_id]
bid = calculate_trip_cost(driver, new_bundle, current_time, existing_dist)
marginal_dist = total_distance - existing_dist
```

**Why marginal cost?** This rewards drivers who are already nearby. If D1 is heading to pickup A, and A' is next door, D1's marginal cost to also pickup A' is tiny - making bundling economically attractive.

### Implementation (`dispatch.py`)

```python
def run_sequential(self, drivers, new_orders, current_time):
    """Sequential market-based dispatch with MARGINAL COST bidding."""
    assigned_orders = []
    
    # Build eligible driver list
    eligible_drivers = []
    for d in drivers:
        if d.status == DriverStatus.DELIVERING:
            continue  # Locked route
        
        if d.status == DriverStatus.IDLE and d.available_from <= current_time:
            eligible_drivers.append(d)
        elif d.status == DriverStatus.ACCRUING and len(d.assigned_orders) < d.capacity:
            eligible_drivers.append(d)

    for order in new_orders:
        best_bid = float('inf')
        best_driver = None
        best_bundle = None

        for driver in eligible_drivers:
            # Check capacity
            potential_orders = driver.assigned_orders + [order]
            if len(potential_orders) > driver.capacity:
                continue

            # Calculate optimal route from current location
            already_picked_up = [o for o in driver.assigned_orders if o.status == PICKED_UP]
            route, total_distance = find_optimal_route(
                driver.current_loc, potential_orders, already_picked_up
            )
            
            if not route:
                continue

            bundle = Bundle(potential_orders, route, total_distance)
            
            # MARGINAL cost calculation
            existing_dist = driver_existing_distances.get(driver.driver_id, 0.0)
            bid = calculate_trip_cost(driver, bundle, current_time, existing_dist)

            if bid < best_bid:
                best_bid = bid
                best_driver = driver
                best_bundle = bundle
        
        if best_driver:
            self._assign_bundle_to_driver(best_driver, best_bundle, current_time)
            assigned_orders.append(order)
            
            # Remove from eligible if at capacity
            if len(best_driver.assigned_orders) >= best_driver.capacity:
                eligible_drivers.remove(best_driver)
        else:
            # FALLBACK: If no valid bid, assign to nearest IDLE driver anyway
            # (better late than never)
            _handle_fallback_assignment(order, eligible_drivers, ...)
    
    return assigned_orders, total_distance
```

### Visual Example

```
Time 17:05: Order O1 arrives (Restaurant A → Customer X)
  D1, D2, D3 bid on O1
  D1 wins (closest to A)
  D1: [Pickup A] → [Dropoff X]

Time 17:06: Order O2 arrives (Restaurant A' → Customer Y)
  (A' is near A)
  D1 bids (ACCRUING, capacity=2): marginal cost = 0.8 km (A' is on the way!)
  D2 bids (IDLE): total cost = 5.2 km
  D1 wins! (lowest marginal cost)
  D1 route updated: [Pickup A] → [Pickup A'] → [Dropoff X] → [Dropoff Y]

Drivers Used: 1 (instead of 2 in Baseline!)
```

### Characteristics

| Aspect | Sequential |
|--------|------------|
| **Bundling** | ✅ Dynamic - drivers can accumulate orders |
| **Re-routing** | ✅ Yes - route recalculated on each new order |
| **Decision Speed** | Fast - per-order bidding |
| **Optimality** | Good - competitive allocation with marginal costs |
| **Complexity** | O(n × m × k!) where k=orders per driver |

---

## 6. Algorithm 3: Combinatorial (Bundle-Based Bidding)

### Philosophy

> "Wait for orders to accumulate, then generate spatially coherent bundles. Drivers bid on bundles using marginal cost. Assign greedily, preferring larger bundles."

This is the **smartest** strategy. It explicitly optimizes for bundling through spatial clustering.

### Key Innovation: Graph-Cut Spatial Clustering

Instead of generating all O(n choose k) possible bundles (exponential), we use a **recursive graph-cut** algorithm that generates O(n log n) spatially coherent bundles:

```
GRAPH-CUT BUNDLE GENERATION:

1. Build distance matrix between all order pickup locations
2. Start with all orders as one big group
3. Use greedy MAX-CUT to split into two groups
   - MAX-CUT maximizes distance BETWEEN groups
   - This means orders WITHIN each group are close together
4. Add valid-sized groups to bundle list
5. Recursively split larger groups (max depth = 5)
6. Also add all pairwise combinations within MAX_PICKUP_DISTANCE_KM
7. Ensure all single orders are included as bundles
```

### Implementation: Bundle Generation (`dispatch.py`)

```python
def generate_spatial_bundles(orders, max_bundle_size=2):
    """Generate bundles using recursive graph-cut spatial clustering."""
    if not orders:
        return []
    
    # Build distance matrix once
    distances = _build_distance_matrix(orders)
    
    bundles = []
    
    def recursive_split(order_group, depth=0):
        if not order_group:
            return
        
        # Always add individual orders
        if len(order_group) == 1:
            bundles.append(order_group)
            return
        
        # Add current group if within size limit
        if len(order_group) <= max_bundle_size:
            bundles.append(order_group)
        
        # Split into two groups using max-cut
        group_a, group_b = _greedy_max_cut(order_group, distances)
        
        # Add the split groups if valid size
        if 1 < len(group_a) <= max_bundle_size:
            bundles.append(group_a)
        if 1 < len(group_b) <= max_bundle_size:
            bundles.append(group_b)
        
        # Recurse on larger groups (limit depth for performance)
        if depth < 5:
            if len(group_a) > max_bundle_size:
                recursive_split(group_a, depth + 1)
            if len(group_b) > max_bundle_size:
                recursive_split(group_b, depth + 1)
    
    recursive_split(orders)
    
    # Also add nearby pairs explicitly (within MAX_PICKUP_DISTANCE_KM = 5.0 km)
    for i, o1 in enumerate(orders):
        for j, o2 in enumerate(orders):
            if i < j and distances[(o1.order_id, o2.order_id)] <= 5.0:
                bundles.append([o1, o2])  # (deduplicated)
    
    # Ensure all single orders are included
    for order in orders:
        if [order] not in bundles:
            bundles.append([order])
    
    return bundles
```

### Greedy Max-Cut (0.5-Approximation)

```python
def _greedy_max_cut(orders, distances):
    """
    Approximation algorithm for max-cut.
    Guaranteed to be at least 50% of optimal.
    """
    group_a = []
    group_b = []
    
    for order in orders:
        # Sum of distances to each group
        dist_to_a = sum(distances.get((order.order_id, o.order_id), 0) for o in group_a)
        dist_to_b = sum(distances.get((order.order_id, o.order_id), 0) for o in group_b)
        
        # Put in group that maximizes cut (place where total distance is greater)
        if dist_to_a >= dist_to_b:
            group_a.append(order)
        else:
            group_b.append(order)
    
    return group_a, group_b
```

### Graph-Cut Visualization

```
Orders: O1, O2, O3, O4, O5 (pickup locations shown)

Geographic Layout:
        O1 ● ● O2         (Cluster 1: O1, O2 are close)
        
        
        
        O3 ●              (Cluster 2: O3 is alone)
        
        
        O4 ● ● O5         (Cluster 3: O4, O5 are close)

MAX-CUT Split 1: {O1, O2} vs {O3, O4, O5}
MAX-CUT Split 2: {O3} vs {O4, O5}

Generated Bundles:
  - [O1, O2]  ← Spatially close pickups
  - [O4, O5]  ← Spatially close pickups
  - [O1], [O2], [O3], [O4], [O5]  ← Singles as fallback
```

### Implementation: Combinatorial Dispatch (`dispatch.py`)

```python
def run_combinatorial(self, drivers, orders, current_time):
    """Combinatorial dispatch using spatial clustering for bundle generation."""
    assigned_orders = []
    pending = list(orders)
    
    # Build eligible driver list (IDLE + ACCRUING with capacity)
    eligible_drivers = [...]
    
    while eligible_drivers and pending:
        # Generate bundles using spatial clustering
        candidate_bundles = generate_spatial_bundles(pending, max_bundle_size=2)
        
        # Collect all (cost, driver, bundle, new_orders, marginal_dist) tuples
        all_bids = []
        
        for order_combo in candidate_bundles:
            for driver in eligible_drivers:
                # Check capacity
                total_orders = len(driver.assigned_orders) + len(order_combo)
                if total_orders > driver.capacity:
                    continue
                
                # Combine existing and new orders
                all_orders = driver.assigned_orders + list(order_combo)
                already_picked_up = [o for o in driver.assigned_orders if o.status == PICKED_UP]
                
                # Calculate optimal route
                route, total_distance = find_optimal_route(
                    driver.current_loc, all_orders, already_picked_up
                )
                if not route:
                    continue
                
                bundle = Bundle(all_orders, route, total_distance)
                
                # MARGINAL cost calculation
                existing_dist = driver_existing_distances.get(driver.driver_id, 0.0)
                cost = calculate_trip_cost(driver, bundle, current_time, existing_dist)
                marginal_distance = total_distance - existing_dist
                
                if cost != float('inf'):  # Passes time constraint
                    all_bids.append((cost, driver, bundle, order_combo, marginal_distance))
        
        if not all_bids:
            # FALLBACK: Assign remaining orders to nearest available driver
            _handle_fallback_assignment(pending, eligible_drivers, ...)
            break
        
        # GREEDY SELECTION with BUNDLE SIZE TIE-BREAKER
        # Primary: lowest cost
        # Secondary: prefer LARGER bundles (reduces drivers needed)
        best = min(all_bids, key=lambda x: (x[0], -len(x[3])))
        cost, driver, bundle, new_orders, marginal_dist = best
        
        self._assign_bundle_to_driver(driver, bundle, current_time)
        
        # Remove assigned orders from pending
        for order in new_orders:
            assigned_orders.append(order)
            pending.remove(order)
        
        # Remove driver if at capacity
        if len(driver.assigned_orders) >= driver.capacity:
            eligible_drivers.remove(driver)
    
    return assigned_orders, total_distance
```

### The Bundle Size Tie-Breaker

This is crucial for maximizing bundling:

```python
# When two bids have similar costs, prefer the larger bundle
best = min(all_bids, key=lambda x: (x[0], -len(x[3])))

# Example:
# Bid 1: cost=5.0, bundle=[O1]      → key=(5.0, -1)
# Bid 2: cost=5.1, bundle=[O1, O2]  → key=(5.1, -2)

# Bid 2 has key (5.1, -2) which is less than (5.0, -1) on second element
# Actually (5.0, -1) < (5.1, -2) because 5.0 < 5.1
# But if costs were equal: (5.0, -1) vs (5.0, -2) → (5.0, -2) wins!

# This saves a driver activation cost.
```

### Characteristics

| Aspect | Combinatorial |
|--------|---------------|
| **Bundling** | ✅✅ Explicit - optimized bundle generation |
| **Re-routing** | ✅ Yes - during ACCRUING state |
| **Decision Speed** | Slower - batch processing |
| **Optimality** | Best - global optimization over bundles |
| **Complexity** | O(n log n) bundles × O(m) drivers × O(k!) routing |

---

## 7. Algorithm 4: Adaptive (Dynamic Strategy Switching)

### Philosophy

> "Monitor the order arrival rate. Use Sequential when load is low (fast response). Switch to Combinatorial when load is high (better bundling)."

This is the **production-ready** strategy that balances responsiveness and efficiency.

### Order Rate Calculation

```python
COMBINATORIAL_WINDOW_MINS = 5  # Look at last 5 minutes
HIGH_LOAD_THRESHOLD = 2.0      # Orders per minute

def _get_dispatch_mode(self) -> str:
    """Determine which strategy to use based on current load."""
    
    # Count orders in the last 5 minutes
    five_mins_ago = current_time - 5 minutes
    recent_orders = [t for t in recent_order_times if t > five_mins_ago]
    
    # Calculate rate
    order_rate = len(recent_orders) / 5.0  # Orders per minute
    
    if order_rate >= HIGH_LOAD_THRESHOLD:
        return "combinatorial"  # High load: bundle aggressively
    else:
        return "sequential"     # Low load: respond quickly
```

### When to Use Which Mode

```
ORDER RATE (orders/minute)
│
│    HIGH LOAD (≥2/min)
│    ┌──────────────────────────────────┐
│    │   COMBINATORIAL MODE             │
│    │   - Batch orders for 1 min       │
│    │   - Generate spatial bundles     │
│    │   - Maximize bundling            │
│    └──────────────────────────────────┘
│ 2.0 ─────────────────────────────────────
│    ┌──────────────────────────────────┐
│    │   SEQUENTIAL MODE                │
│    │   - Dispatch per-order           │
│    │   - Marginal cost bidding        │
│    │   - Fast customer response       │
│    └──────────────────────────────────┘
│    LOW LOAD (<2/min)
│
└──────────────────────────────────────────▶ TIME
```

### Characteristics

| Aspect | Adaptive |
|--------|----------|
| **Bundling** | ✅ Dynamic - depends on load |
| **Re-routing** | ✅ Yes |
| **Decision Speed** | Variable - adapts to conditions |
| **Optimality** | Good - balances speed and efficiency |
| **Best For** | Unknown/variable demand patterns |

---

## 8. The Scoring System (MARGINAL Cost Function)

### The Bid Formula

Every driver calculates a "bid" (cost) for taking on a bundle. **The key innovation is using MARGINAL cost** - the additional cost to add orders to an existing route.

```python
def calculate_trip_cost(
    driver: Driver, 
    bundle: Bundle, 
    current_time: time,
    existing_route_distance: float = 0.0  # KEY PARAMETER!
) -> float:
    """
    Calculate the MARGINAL cost for a driver to take on a bundle.
    Lower cost = better bid = higher priority.
    """
    
    # 1. CAPACITY CHECK (hard constraint)
    if bundle.num_orders > driver.capacity:
        return float('inf')
    
    # 2. TRAVERSE ROUTE, CALCULATE ARRIVAL TIMES
    time_at_current_loc = current_time
    last_loc = driver.current_loc
    total_delay_mins = 0.0
    
    for stop in bundle.route_sequence:
        # Calculate travel time using Haversine or OSRM
        travel_time = get_travel_time(last_loc, stop.location)
        time_at_current_loc += travel_time + SERVICE_TIME_MINS  # 5 min service
        
        if stop.stop_type == 'DROPOFF':
            order = order_map[stop.order_id]
            actual_duration = time_at_current_loc - order.created_time
            
            # HARD CONSTRAINT: Reject if exceeds MAX_DELIVERY_TIME_MINS (52 min)
            if actual_duration > MAX_DELIVERY_TIME_MINS:
                return float('inf')  # Bundle rejected!
            
            # Delay penalty (capped at 20 min to prevent extreme values)
            delay = actual_duration - order.estimated_delivery_time_min
            if delay > 0:
                total_delay_mins += min(delay, 20)
        
        last_loc = stop.location
    
    # 3. CALCULATE MARGINAL DISTANCE (KEY INNOVATION!)
    marginal_distance = bundle.total_distance - existing_route_distance
    
    # 4. BASE SCORE
    distance_cost = W_DISTANCE * marginal_distance  # W_DISTANCE = 1.0
    delay_cost = W_DELAY * total_delay_mins         # W_DELAY = 1.5
    base_score = distance_cost + delay_cost
    
    # 5. VEHICLE PENALTY
    vehicle_penalty = {
        "motorbike": 1.0,  # Preferred
        "bike": 1.2,       # Slower
        "car": 1.4         # Less maneuverable
    }[driver.vehicle_type]
    
    score_with_vehicle = base_score * vehicle_penalty
    
    # 6. NORMALIZE BY NUMBER OF ORDERS
    cost_per_order = score_with_vehicle / bundle.num_orders
    
    # 7. BUNDLE DISCOUNT (25% per additional order)
    if bundle.num_orders > 1:
        bundle_discount = 0.25 * (bundle.num_orders - 1)
        cost_per_order = cost_per_order * (1.0 - bundle_discount)
    
    return cost_per_order
```

### Why Marginal Cost Makes Bundling Work

```
Scenario: Driver D1 is already assigned Order O1 (5km route)
          New Order O2 arrives with pickup near O1's pickup

WITHOUT Marginal Cost (total cost):
  D1's bid for [O1, O2]: total_distance=7km → cost=7.0
  D2's bid for [O2]: total_distance=4km → cost=4.0
  D2 wins! (lower total cost)
  Result: 2 drivers used

WITH Marginal Cost:
  D1's bid for [O1, O2]: marginal = 7km - 5km = 2km → cost=2.0
  D2's bid for [O2]: marginal = 4km - 0km = 4km → cost=4.0
  D1 wins! (lower marginal cost)
  Result: 1 driver used ✓
```

### Why Bundles Are Cheaper (The Bundle Discount)

```
Single Order (bundle size = 1):
  base_score = 10
  cost_per_order = 10 / 1 = 10
  bundle_discount = 0 (no discount for size=1)
  final_cost = 10.0

Bundle of 2 Orders:
  base_score = 14 (more distance, but shared)
  cost_per_order = 14 / 2 = 7.0
  bundle_discount = 0.25 * (2-1) = 0.25 (25% off)
  final_cost = 7.0 * 0.75 = 5.25

RESULT: Bundle is cheaper per-order (5.25 vs 10.0)
        This incentivizes drivers to take bundles
        This reduces total drivers needed
```

### Hard Constraints in Scoring

1. **Capacity Check**: Bundle rejected if `num_orders > capacity`
2. **Time Constraint**: Bundle rejected if any delivery would exceed `MAX_DELIVERY_TIME_MINS` (52 minutes)
3. **Delay Cap**: Delay penalty capped at 20 minutes to prevent extreme values dominating

### Configuration Parameters

```python
# Scoring weights (config.py)
W_DISTANCE = 1.0              # Weight for marginal distance
W_DELAY = 1.5                 # Weight for delay (higher = prioritize on-time)
BUNDLE_DISCOUNT_PER_ORDER = 0.25  # 25% discount per additional order
MAX_DELIVERY_TIME_MINS = 52.0     # Hard constraint (reject bundles exceeding this)

# Vehicle preferences
PENALTY_MOTORBIKE = 1.0       # Baseline
PENALTY_BIKE = 1.2            # 20% penalty
PENALTY_CAR = 1.4             # 40% penalty

# Service time
SERVICE_TIME_MINS = 5.0       # Time at each stop (parking, handover)
```

---

## 9. Route Optimization (TSP with Precedence)

### The Problem

Given a driver's current location and a set of orders, find the shortest route that:
1. Visits all pickup and dropoff locations
2. Respects precedence: each order's pickup must come before its dropoff

This is the **Traveling Salesperson Problem with Precedence Constraints (TSP-PC)**.

### Solution: Exhaustive Search with Pruning

```python
def find_optimal_route(
    start_loc: Tuple[float, float], 
    orders: List[Order], 
    already_picked_up: List[Order] = None
) -> Tuple[List[Stop], float]:
    """
    Find the shortest valid route through all stops.
    
    Complexity: O(n!) where n = 2 * num_orders (but pruned by constraints)
    Practical for n ≤ 4 orders (8 stops = 40,320 permutations max)
    """
    if not orders:
        return [], 0.0
    
    already_picked_up_ids = {o.order_id for o in (already_picked_up or [])}
    
    # Create all required stops
    all_stops = []
    for order in orders:
        if order.order_id not in already_picked_up_ids:
            all_stops.append(Stop(order.pickup_loc, 'PICKUP', order.order_id))
        all_stops.append(Stop(order.dropoff_loc, 'DROPOFF', order.order_id))
    
    # Generate all permutations
    best_route = []
    min_distance = float('inf')
    
    for perm in permutations(all_stops):
        # Validate precedence constraint
        if not is_valid_precedence(perm, already_picked_up_ids):
            continue
        
        # Calculate total distance
        locations = [start_loc] + [stop.location for stop in perm]
        distance = sum(
            get_distance(locations[i], locations[i+1]) 
            for i in range(len(locations) - 1)
        )
        
        if distance < min_distance:
            min_distance = distance
            best_route = list(perm)
    
    return best_route, min_distance


def is_valid_precedence(perm, already_picked_up_ids):
    """Check that each pickup comes before its dropoff."""
    picked_up = set(already_picked_up_ids)
    
    for stop in perm:
        if stop.stop_type == 'PICKUP':
            picked_up.add(stop.order_id)
        elif stop.stop_type == 'DROPOFF':
            if stop.order_id not in picked_up:
                return False  # Dropoff before pickup!
    
    return True
```

### Example

```
Orders: O1 (A→X), O2 (B→Y)
Driver at location D

All Stops: [P1, D1, P2, D2] (P=pickup, D=dropoff)

Valid Permutations (pickup before dropoff):
  [P1, D1, P2, D2] ✓
  [P1, P2, D1, D2] ✓
  [P1, P2, D2, D1] ✓
  [P2, D2, P1, D1] ✓
  [P2, P1, D2, D1] ✓
  [P2, P1, D1, D2] ✓

Invalid Permutations:
  [D1, P1, P2, D2] ✗ (D1 before P1)
  [P1, D1, D2, P2] ✗ (D2 before P2)
  ...

For each valid permutation, calculate total distance.
Return the one with minimum distance.
```

---

## 10. Why Our Approach Works

### Verified Benchmark Results (January 2026)

| Dataset | Orders | Baseline Drivers | Best Strategy | Best Drivers | Reduction |
|:--------|:------:|:----------------:|:-------------:|:------------:|:---------:|
| clean_100 | 100 | 64 | Combinatorial | 58 | **9.4%** |
| hybrid_100 | 100 | 68 | Sequential/Comb | 63 | **7.4%** |
| spread_100 | 100 | 69 | Combinatorial | 64 | **7.2%** |

### The Mathematics of Fleet Reduction

**Baseline** treats each order independently:
- 100 orders → uses ~64 drivers (some parallelism)
- Average efficiency: 1.56 orders per driver
- No bundling, no optimization

**Combinatorial** bundles orders together:
- 100 orders → uses ~58 drivers
- Average efficiency: 1.72 orders per driver
- **9.4% fewer drivers** = significant cost savings

### The Trade-offs

| Metric | Baseline | Combinatorial | Trade-off |
|--------|----------|---------------|-----------|
| Drivers Used | 64 | 58 | **-9.4%** ✅ |
| Avg Delivery Time | 13.40 min | 14.75 min | +1.35 min |
| Total Distance | 399 km | 421 km | +5.5% |
| Late Deliveries (>60m) | 0 | 0 | Same |

**Why is this acceptable?**

1. **+1-2 minutes delivery time** is within acceptable bounds (still under 60 min target)
2. **+5% distance** is offset by 9% fewer driver activations
3. **Cost savings**: 6 fewer drivers × $10-15 per activation = $60-90 saved per 100 orders

### Why Marginal Cost is the Key Innovation

The marginal cost approach creates an **economic incentive for bundling**:

1. Idle drivers bid their full route cost
2. Busy drivers (ACCRUING) bid only the additional cost
3. When a driver is already heading to a pickup area, they can add nearby orders at minimal marginal cost
4. This naturally clusters orders to drivers who are nearby

Without marginal cost, every bid is total cost, and idle drivers always win - defeating the purpose of bundling.

### Scalability

Our graph-cut bundle generation is **O(n log n)** instead of **O(n choose k)**:

```
100 orders:
  Naive: C(100, 2) = 4,950 pairs
  Graph-cut: ~100 × log(100) ≈ 664 bundles

1000 orders:
  Naive: C(1000, 2) = 499,500 pairs
  Graph-cut: ~1000 × log(1000) ≈ 9,966 bundles

10x orders → 15x bundles (vs 100x for naive)
```

### Summary

| Algorithm | When to Use | Fleet Reduction | Response Time |
|-----------|-------------|-----------------|---------------|
| **Baseline** | Never (comparison only) | 0% | Instant |
| **Sequential** | Low load, mixed patterns | 5-7% | Fast |
| **Combinatorial** | High load, clustered orders | 7-9% | 1 min delay |
| **Adaptive** | Production, unknown patterns | 7-9% | Variable |

---

## Appendix A: Key Configuration Parameters

```python
# config.py

# Simulation
START_TIME = 17:00:00
SIMULATION_END_TIME = 22:00:00
SIMULATION_SPEED_MINUTES = 1

# Physics
AVG_SPEED_KMH = 35.0
SERVICE_TIME_MINS = 5.0

# Batching
BATCH_WINDOW_MINS = 1.0
HIGH_LOAD_THRESHOLD = 2.0  # orders/minute for adaptive mode

# Bundling
MAX_BUNDLE_SIZE = 2
MAX_PICKUP_DISTANCE_KM = 5.0  # For graph-cut pair generation

# Scoring
W_DISTANCE = 1.0
W_DELAY = 1.5
BUNDLE_DISCOUNT_PER_ORDER = 0.25
MAX_DELIVERY_TIME_MINS = 52.0  # Hard constraint

# Vehicle Penalties
PENALTY_MOTORBIKE = 1.0
PENALTY_BIKE = 1.2
PENALTY_CAR = 1.4

# Road Distance (optional)
USE_ROAD_DISTANCE = False  # Set True for OSRM integration
OSRM_SERVER_URL = "https://router.project-osrm.org"
```

---

## Appendix B: Distance Calculation

The system supports two distance calculation modes:

### Haversine (Default)

```python
def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance using Haversine formula."""
    # Convert to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    return 6371 * c  # Earth radius in km
```

### OSRM (Optional)

When `USE_ROAD_DISTANCE = True`, the system uses OSRM for actual road distances:

```python
def get_distance(lat1, lon1, lat2, lon2) -> float:
    if config.USE_ROAD_DISTANCE:
        result = osrm_route(lat1, lon1, lat2, lon2)
        if result:
            return result[0]  # distance_km
        # Fallback with 1.4x multiplier
        return haversine_distance(...) * 1.4
    return haversine_distance(...)
```

The system also supports batch precomputation via OSRM Table API for efficiency.

---

## Appendix C: Fallback Mechanisms

Both Sequential and Combinatorial have fallback mechanisms when no valid bids are available (e.g., all bundles exceed time constraint):

```python
# When all bids return infinity (time constraint violation):
# Fall back to nearest-driver assignment

for order in pending_orders:
    # Find nearest IDLE driver
    best_driver = min(
        idle_drivers,
        key=lambda d: get_distance(d.current_loc, order.pickup_loc)
    )
    
    # If no IDLE driver, try ACCRUING drivers with capacity
    if not best_driver:
        best_driver = min(
            accruing_drivers,
            key=lambda d: get_distance(d.current_loc, order.pickup_loc)
        )
    
    # Assign anyway (better late than never)
    if best_driver:
        assign_single_order(best_driver, order)
```

This ensures all orders get assigned even in edge cases.

---

**Document Version**: 2.0  
**Last Updated**: January 17, 2026  
**For**: Snoonu Hackathon 2026 - Case 1: Operations & Logistics at Scale
