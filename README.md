<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<h1 align="center">🚀 Snoonu Smart Dispatch</h1>

<p align="center">
  <strong>AI-Powered Last-Mile Delivery Optimization</strong><br>
  Reduce fleet size by 15-25% while maintaining delivery SLAs
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-the-problem">The Problem</a> •
  <a href="#-our-solution">Our Solution</a> •
  <a href="#-results">Results</a> •
  <a href="#-how-it-works">How It Works</a>
</p>

---

## 🎯 The Problem

Traditional food delivery dispatch systems use **greedy nearest-neighbor assignment**: each order goes to the closest available driver. This approach is simple but wasteful:

- **Low driver utilization** — drivers often carry single orders when they could handle multiple
- **Oversized fleets** — companies hire more drivers than necessary to meet demand
- **Inefficient routing** — no consideration of order bundling or route optimization

> 💰 **The Cost**: A fleet using 100 drivers when 75 would suffice wastes 25% on labor, vehicles, and coordination overhead.

---

## 💡 Our Solution

**Smart Dispatch** uses **combinatorial optimization with bidding-based assignment** to intelligently bundle orders and minimize the number of active drivers needed.

### Key Innovation: Market-Based Task Allocation with Marginal Cost Bidding

Instead of assigning orders greedily, our system:

1. **Batches incoming orders** for 1-2 minutes to identify bundling opportunities
2. **Generates spatial clusters** using graph-cut algorithms
3. **Solicits bids from drivers** based on *marginal cost* (not total cost)
4. **Awards bundles** to the lowest bidder, preferring multi-order assignments

The **marginal cost approach** is critical: a driver already heading toward a restaurant can pick up a nearby order for minimal extra distance, making bundling naturally attractive.

---

## 🏆 Results

| Metric | Baseline (Greedy) | Smart Dispatch | Improvement |
|:-------|:-----------------:|:--------------:|:-----------:|
| **Drivers Used** | 89 | 68 | **-24%** |
| **Orders/Driver** | 1.12 | 1.47 | **+31%** |
| **Fleet Distance** | 412 km | 389 km | **-6%** |

> 📊 Tested on 100 orders with 100 available drivers in Doha, Qatar

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/snoonu-smart-dispatch.git
cd snoonu-smart-dispatch

# Install dependencies
pip install -r requirements.txt
```

### Run the Dashboard

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

### Run via CLI

```bash
# Compare baseline vs optimized strategies
python main.py

# Run specific dataset
python main.py --dataset stress

# Run all strategies
python main.py --all-strategies

# List available datasets
python main.py --list-datasets
```

---

## ⚙️ How It Works

### 1. Order Batching

Orders are accumulated for a configurable window (default: 1 minute) before dispatch. This creates opportunities for bundling nearby orders.

```
17:00:00 → Order A arrives (Restaurant X → Customer 1)
17:00:23 → Order B arrives (Restaurant X → Customer 2)  ← Same restaurant!
17:00:45 → Order C arrives (Restaurant Y → Customer 3)
17:01:00 → Dispatch window closes, bundle [A,B] identified
```

### 2. Spatial Clustering (Graph-Cut)

Orders are clustered by pickup location using a greedy max-cut algorithm:

```
┌─────────────────────────────────────┐
│  Order A ●────────● Order B         │  ← Bundle 1 (nearby pickups)
│                                     │
│           Order C ●                 │  ← Bundle 2 (isolated)
│                                     │
│  Order D ●────────● Order E         │  ← Bundle 3 (nearby pickups)
└─────────────────────────────────────┘
```

### 3. Marginal Cost Bidding

Drivers submit bids based on **additional distance** required:

| Driver | Current Location | Bid for Bundle [A,B] | Calculation |
|:-------|:-----------------|:---------------------|:------------|
| D1 | Near Restaurant X | **2.3 km** | Already nearby |
| D2 | Far from Restaurant X | 8.7 km | Must travel far |
| D3 | En route elsewhere | ∞ | Currently delivering |

**Winner: D1** (lowest marginal cost)

### 4. Dynamic Re-Routing

Drivers in `ACCRUING` state (still picking up) can accept additional orders. Routes are recalculated on-the-fly using TSP with precedence constraints.

---

## 📊 Dispatch Strategies

| Strategy | Description | Best For |
|:---------|:------------|:---------|
| **Baseline** | Greedy nearest-neighbor | Benchmark comparison |
| **Sequential** | Per-order bidding with marginal costs | Low-volume periods |
| **Combinatorial** | Batch optimization with bundling | High-volume periods |
| **Adaptive** | Switches based on order rate | Production use |

---

## 📁 Project Structure

```
snoonu-smart-dispatch/
├── app.py                    # Streamlit Dashboard (entry point)
├── main.py                   # CLI interface
├── benchmark.py              # Benchmarking suite
├── requirements.txt          # Python dependencies
├── src/
│   ├── __init__.py          # Package exports
│   ├── config.py            # Tunable parameters
│   ├── models.py            # Domain models (Order, Driver, Bundle)
│   ├── dispatch.py          # Dispatch strategies
│   ├── simulation.py        # Discrete-event simulation
│   ├── scoring.py           # Bid cost calculation
│   └── utils.py             # Geographic utilities
├── data/
│   ├── doha_orders_*.csv    # Order datasets
│   └── doha_couriers_*.csv  # Driver datasets
├── ALGORITHM_DEEP_DIVE.md   # Technical documentation
└── PERFORMANCE_ANALYSIS.md  # Benchmark results & analysis
```

---

## 🔧 Configuration

Key parameters in `src/config.py`:

```python
# Batching
BATCH_WINDOW_MINS = 1.0       # Time to accumulate orders

# Bundling
MAX_BUNDLE_SIZE = 2           # Max orders per driver
BUNDLE_DISCOUNT_PER_ORDER = 0.25  # Cost incentive for bundling

# Scoring
W_DISTANCE = 1.0              # Weight for distance
W_DELAY = 1.5                 # Weight for lateness penalty
MAX_DELIVERY_TIME_MINS = 52   # Hard SLA constraint
```

---

## 📈 Datasets

| Dataset | Orders | Drivers | Scenario |
|:--------|:------:|:-------:|:---------|
| `clean_100` | 100 | 100 | Standard urban |
| `hybrid_100` | 100 | 100 | Mixed urban/suburban |
| `spread_100` | 100 | 100 | Geographically dispersed |
| `stress` | 250+ | 250 | High-volume stress test |

---

## 🤝 Team

Built with ❤️ for the **Snoonu Hackathon 2026**

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>⭐ Star this repo if you found it useful!</strong>
</p>
