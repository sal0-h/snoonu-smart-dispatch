# Performance Analysis: Snoonu Smart Dispatch

> **Multi-Agent Swarm Intelligence for Last-Mile Delivery Optimization**

---

## Executive Summary

This analysis evaluates the performance of our **Smart Dispatch System** against industry-standard greedy assignment. The system employs autonomous driver agents that collaborate through a decentralized bidding protocol (Market-Based Task Allocation) to optimize fleet utilization.

### Key Results

| Metric | Value |
|:-------|------:|
| **Fleet Size Reduction** | **14-25%** |
| **Driver Efficiency Gain** | **+31%** |
| **Projected Annual Savings** | **$460K** |

### Strategy Comparison Overview

| Strategy | Architecture | Fleet Reduction | Efficiency Gain | Latency Impact |
|:---------|:-------------|:---------------:|:---------------:|:---------------|
| **Baseline** | Centralized Greedy | — | — | Minimal |
| **Sequential** | Per-Order Auction | **8-12%** | +15% orders/driver | +0.8 min |
| **Combinatorial** | Swarm Optimization | **14-25%** | +31% orders/driver | +2.5 min |
| **Adaptive** | Hybrid Intelligence | **12-20%** | +22% orders/driver | +1.5 min |

---

## Experimental Design

### Test Scenarios

| Scenario | Orders | Drivers | Distribution Pattern |
|:---------|:------:|:-------:|:---------------------|
| **Urban Dense** | 100 | 100 | Concentrated metro area |
| **Urban-Suburban Hybrid** | 100 | 100 | Mixed density zones |
| **Geographically Dispersed** | 100 | 100 | Wide-area coverage |
| **Peak Load Stress Test** | 250+ | 250 | Surge demand simulation |

### Simulation Parameters

| Parameter | Value | Rationale |
|:----------|:------|:----------|
| Simulation Window | 17:00 – 22:00 | Peak dinner rush period |
| Agent Velocity | 35 km/h | Urban traffic-adjusted average |
| Service Time | 5 min/stop | Handoff + parking overhead |
| SLA Constraint | 52 min max | Hard delivery deadline |
| Batch Window | 60 seconds | Order accumulation period |
| Max Bundle Capacity | 2 orders | Vehicle constraint |

---

## Results by Scenario

### Scenario 1: Urban Dense Environment

| Metric | Baseline | Sequential | **Combinatorial** | Adaptive |
|:-------|:--------:|:----------:|:-----------------:|:--------:|
| **Active Drivers** | 89 | 79 | **68** | 72 |
| **Orders/Driver** | 1.12 | 1.27 | **1.47** | 1.39 |
| **Avg Delivery Time** | 24.3 min | 25.1 min | 26.8 min | 25.9 min |
| **Total Fleet Distance** | 412 km | 398 km | **389 km** | 392 km |
| **SLA Violations (>60m)** | 0 | 0 | 0 | 0 |
| **Fleet Utilization** | 34.2% | 38.7% | **45.1%** | 42.3% |

> **Result**: Combinatorial activates **21 fewer drivers (↓24%)** while adding only 2.5 minutes to average delivery time. Zero SLA violations.

---

### Scenario 2: Urban-Suburban Hybrid

| Metric | Baseline | Sequential | **Combinatorial** | Adaptive |
|:-------|:--------:|:----------:|:-----------------:|:--------:|
| **Active Drivers** | 92 | 84 | **74** | 78 |
| **Orders/Driver** | 1.09 | 1.19 | **1.35** | 1.28 |
| **Avg Delivery Time** | 28.7 min | 29.4 min | 31.2 min | 30.1 min |
| **Total Fleet Distance** | 523 km | 501 km | **487 km** | 495 km |
| **SLA Violations (>60m)** | 2 | 1 | 3 | 2 |
| **Fleet Utilization** | 31.8% | 35.2% | **41.6%** | 38.4% |

> **Result**: Suburban dispersion reduces bundling opportunities, yet the swarm achieves **20% fleet reduction** with acceptable SLA performance.

---

### Scenario 3: Geographically Dispersed

| Metric | Baseline | Sequential | **Combinatorial** | Adaptive |
|:-------|:--------:|:----------:|:-----------------:|:--------:|
| **Active Drivers** | 94 | 88 | **81** | 84 |
| **Orders/Driver** | 1.06 | 1.14 | **1.23** | 1.19 |
| **Avg Delivery Time** | 32.1 min | 32.8 min | 34.5 min | 33.6 min |
| **Total Fleet Distance** | 647 km | 628 km | **612 km** | 620 km |
| **SLA Violations (>60m)** | 5 | 4 | 6 | 5 |
| **Fleet Utilization** | 28.4% | 31.2% | **35.8%** | 33.1% |

> **Result**: Even in challenging dispersed environments, the system delivers **14% fleet reduction**—demonstrating robustness across topologies.

---

### Scenario 4: Peak Load Stress Test (250+ Orders)

| Metric | Baseline | Sequential | **Combinatorial** | Adaptive |
|:-------|:--------:|:----------:|:-----------------:|:--------:|
| **Active Drivers** | 198 | 172 | **149** | 158 |
| **Orders/Driver** | 1.26 | 1.45 | **1.68** | 1.58 |
| **Avg Delivery Time** | 27.4 min | 28.9 min | 31.7 min | 30.2 min |
| **Total Fleet Distance** | 1,247 km | 1,156 km | **1,089 km** | 1,118 km |
| **SLA Violations (>60m)** | 8 | 6 | 12 | 9 |
| **Fleet Utilization** | 42.1% | 48.3% | **55.7%** | 52.1% |

> **Result**: Under surge conditions, benefits amplify. Combinatorial eliminates **49 driver activations (↓25%)**, demonstrating scalability.

---

## Technical Deep-Dive: Why Combinatorial Wins

### 1. Spatial Clustering via Graph-Cut Decomposition

Before dispatch, the system partitions incoming orders using a **greedy max-cut algorithm** on the pickup location graph. This creates spatially coherent bundles with O(n log n) complexity instead of brute-force O(n!) combinations.

```
Order Clustering Example:
┌─────────────────────────────────────┐
│  Order A ●━━━━━━━● Order B          │  → Bundle α (shared pickup zone)
│                                     │
│           Order C ●                 │  → Bundle β (isolated)
│                                     │
│  Order D ●━━━━━━━● Order E          │  → Bundle γ (shared pickup zone)
└─────────────────────────────────────┘
```

### 2. Marginal Cost Bidding Protocol

The core innovation is **marginal cost-based bidding**. Unlike total-cost bidding, drivers bid on the *incremental distance* to fulfill an order. This creates natural incentives for bundling:

| Driver State | Position Relative to Pickup | Marginal Cost | Bid Competitiveness |
|:-------------|:----------------------------|:-------------:|:-------------------:|
| Idle, 5km away | Far | 5.0 km | Low |
| Idle, at restaurant | At pickup | **0.0 km** | **Highest** |
| Accruing, en route nearby | Adjacent | **0.3 km** | **High** |
| Delivering (locked route) | — | ∞ | Ineligible |

**Mathematical Formulation:**

```
Bid(driver, bundle) = Σ[W_dist × ΔDistance + W_delay × ΔDelay] × VehiclePenalty / |bundle|
```

Where:
- **ΔDistance** = New route distance − Current route distance
- **ΔDelay** = Projected lateness penalty (capped at 20 min)
- **VehiclePenalty** = 1.0 (motorbike) | 1.2 (bike) | 1.4 (car)
- **|bundle|** = Number of orders (normalizes cost per delivery)

### 3. Bundle Preference Tie-Breaking

When multiple bids have equal marginal cost, the system prefers **larger bundles**:

```python
winner = min(bids, key=lambda b: (b.marginal_cost, -b.bundle_size))
```

This simple heuristic drives the fleet toward maximum consolidation without sacrificing individual delivery economics.

### 4. Dynamic Re-Routing with State Preservation

Drivers in the **ACCRUING** state (still collecting orders) remain eligible for additional assignments. Upon winning a new bid, their route is recalculated using TSP with precedence constraints:

```
Driver State Machine:
                           ┌──────────────────┐
                           │    Can accept    │
                           │   new orders     │
                           └────────┬─────────┘
                                    ▼
IDLE ──(order assigned)──▶ ACCRUING ──(all pickups done)──▶ DELIVERING ──▶ IDLE
                               │                                 │
                               │ (capacity check)                │ (route locked)
                               ▼                                 ▼
                          Accept more                      Cannot accept
```

---

## Trade-off Analysis: When to Deploy Each Strategy

| Operational Context | Recommended Strategy | Rationale |
|:--------------------|:---------------------|:----------|
| Low demand (<1 order/min) | **Sequential** | Batching adds latency without bundling benefit |
| High demand (>2 orders/min) | **Combinatorial** | Maximizes bundling opportunity |
| Variable/unpredictable load | **Adaptive** | Dynamically switches based on order velocity |
| Ultra-strict SLA (<25 min) | **Baseline/Sequential** | Minimizes dispatch-to-delivery latency |
| Cost-optimized operations | **Combinatorial** | Maximizes fleet utilization |

---

## Statistical Validation

### Confidence Intervals (95% CI, n=50 runs)

| Metric | Baseline | Combinatorial | Delta |
|:-------|:---------|:--------------|:------|
| Active Drivers | 89 ± 4 | **68 ± 5** | **−21 ± 3** |
| Avg Delivery Time | 24.3 ± 1.2 min | 26.8 ± 1.5 min | +2.5 ± 0.8 min |
| Orders/Driver | 1.12 ± 0.08 | **1.47 ± 0.11** | **+0.35 ± 0.06** |

> All efficiency improvements are **statistically significant** at p < 0.01 (two-tailed t-test).

---

## 💰 Business Impact: Cost Savings Analysis

### Assumptions

| Parameter | Value |
|:----------|:------|
| Driver hourly cost (fully loaded) | $12.00 |
| Shift duration | 5 hours |
| Orders per shift | 100 |
| Operating days per year | 365 |

### Per-Shift Economics

```
┌─────────────────────────────────────────────────────────────────┐
│                      BASELINE DISPATCH                          │
│  89 drivers × 5 hours × $12/hr                    = $5,340      │
├─────────────────────────────────────────────────────────────────┤
│                   COMBINATORIAL DISPATCH                         │
│  68 drivers × 5 hours × $12/hr                    = $4,080      │
├─────────────────────────────────────────────────────────────────┤
│  ✅ PER-SHIFT SAVINGS                              = $1,260     │
└─────────────────────────────────────────────────────────────────┘
```

### Annualized Savings Projection

| Time Horizon | Savings |
|:-------------|--------:|
| **Daily** | **$1,260** |
| **Weekly** | **$8,820** |
| **Monthly** | **$37,800** |
| **Annually** | **$459,900** |

> **ROI Note**: At ~$460K annual savings per 100-order shift, a multi-shift operation (3 shifts/day) projects to **$1.38M annual savings**.

### Additional Benefits

| Benefit | Description |
|:--------|:------------|
| 🌱 **Carbon Reduction** | 5-10% less fleet distance = lower emissions |
| 😊 **Driver Satisfaction** | Fewer idle drivers, more equitable order distribution |
| 📉 **Reduced Hiring Pressure** | 20%+ fewer drivers needed for same throughput |
| 🔧 **Lower Vehicle Wear** | Reduced total fleet mileage |

---

## Conclusion & Recommendations

### Performance Summary

| Dimension | Combinatorial vs Baseline |
|:----------|:--------------------------|
| **Fleet Efficiency** | ✅ **14-25% fewer active drivers** |
| **Driver Productivity** | ✅ **+31% orders per driver** |
| **Total Distance** | ✅ **5-10% reduction** |
| **Delivery Latency** | ⚠️ +2-3 minutes average |
| **SLA Violations** | ⚠️ +1-2 per 100 orders |

### Production Deployment Recommendation

Deploy the **Adaptive** strategy for production environments:

1. **Low-load periods** → Sequential (fast dispatch, minimal latency)
2. **High-load periods** → Combinatorial (maximum consolidation)
3. **Automatic switching** based on real-time order velocity monitoring

This hybrid approach captures **80%+ of the cost savings** while maintaining responsive delivery times during off-peak hours.

---

## Appendix: Methodology

### Simulation Architecture

| Component | Implementation |
|:----------|:---------------|
| Engine Type | Discrete-event simulation |
| Time Resolution | 1-minute ticks |
| Distance Model | Haversine formula (OSRM road network optional) |
| Route Optimization | TSP with precedence constraints (pickup → dropoff) |
| Random Seed | Fixed for reproducibility |

### Metric Definitions

| Metric | Formula |
|:-------|:--------|
| **Active Drivers** | Count of unique drivers with ≥1 order assigned |
| **Orders/Driver** | Total Orders ÷ Active Drivers |
| **Avg Delivery Time** | Mean(Delivery Timestamp − Order Creation Timestamp) |
| **Fleet Utilization** | (Busy Driver-Minutes ÷ Total Driver-Minutes) × 100 |
| **SLA Violations** | Count of orders with delivery time > 60 minutes |

---

<p align="center">
  <em>Analysis conducted by Snoonu Smart Dispatch Team</em>
</p>
