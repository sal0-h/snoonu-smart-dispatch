# Snoonu Logistics Benchmark Results

**Generated:** 2026-01-17 03:50:56

## Summary

This report compares 4 dispatch strategies across multiple order/courier datasets:
- **Baseline**: Greedy nearest-driver assignment (one order per driver)
- **Sequential**: Marginal cost bidding (drivers can accept additional orders while picking up)
- **Combinatorial**: Batch orders and find optimal bundles
- **Adaptive**: Dynamically switches between sequential and combinatorial based on load

---

## Hybrid 100 + 50 Drivers (2:1 ratio)

**Configuration:**
- Orders: `data/doha_orders_hybrid_100.csv` (100 orders)
- Couriers: `data/doha_couriers_50.csv` (50 drivers)
- Order/Driver Ratio: 2.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 100/100 | 100/100 | 100/100 | 100/100 |
| **Drivers Used** | 50/50 | 47/50 | 47/50 | 47/50 |
| **Total Fleet Distance** | 946.63 km | 927.93 km | 923.27 km | 916.66 km |
| **Distance Savings** | 0.00 km (0.00%) | 18.70 km (1.98%) | 23.36 km (2.47%) | 29.97 km (3.17%) |
| **Avg Delivery Time** | 22.77 min | 24.57 min | 24.71 min | 24.32 min |
| **Time Delta** | 0.00 min | +1.80 min | +1.94 min | +1.55 min |
| **Min Delivery Time** | 7.13 min | 7.13 min | 7.13 min | 7.13 min |
| **Max Delivery Time** | 53.12 min | 53.12 min | 54.12 min | 54.12 min |
| **Avg Distance/Order** | 9.47 km | 9.28 km | 9.23 km | 9.17 km |
| **Late Deliveries (>45m)** | 8 | 13 | 12 | 11 |
| **Late Deliveries (>60m)** | 0 | 0 | 0 | 0 |
| **Fleet Utilization** | 26.68% | 27.04% | 26.61% | 26.36% |
| **Orders/Driver** | 2.00 | 2.13 | 2.13 | 2.13 |
| **Driver Savings** | 0 | 3 | 3 | 3 |

---

## Clean 100

**Configuration:**
- Orders: `data/doha_orders_clean_100.csv` (100 orders)
- Couriers: `data/doha_couriers_clean_100.csv` (100 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 100/100 | 100/100 | 100/100 | 100/100 |
| **Drivers Used** | 64/100 | 60/100 | 58/100 | 59/100 |
| **Total Fleet Distance** | 399.03 km | 410.47 km | 420.30 km | 421.56 km |
| **Distance Savings** | 0.00 km (0.00%) | -11.44 km (-2.87%) | -21.27 km (-5.33%) | -22.53 km (-5.65%) |
| **Avg Delivery Time** | 13.40 min | 13.91 min | 14.69 min | 14.59 min |
| **Time Delta** | 0.00 min | +0.51 min | +1.29 min | +1.19 min |
| **Min Delivery Time** | 7.43 min | 7.43 min | 7.43 min | 7.43 min |
| **Max Delivery Time** | 41.57 min | 47.07 min | 47.07 min | 47.07 min |
| **Avg Distance/Order** | 3.99 km | 4.10 km | 4.20 km | 4.22 km |
| **Late Deliveries (>45m)** | 0 | 1 | 2 | 2 |
| **Late Deliveries (>60m)** | 0 | 0 | 0 | 0 |
| **Fleet Utilization** | 9.03% | 8.49% | 8.66% | 8.65% |
| **Orders/Driver** | 1.56 | 1.67 | 1.72 | 1.69 |
| **Driver Savings** | 0 | 4 | 6 | 5 |

---

## Hybrid 100 (Full Drivers)

**Configuration:**
- Orders: `data/doha_orders_hybrid_100.csv` (100 orders)
- Couriers: `data/doha_couriers_hybrid_100.csv` (100 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 100/100 | 100/100 | 100/100 | 100/100 |
| **Drivers Used** | 68/100 | 63/100 | 63/100 | 63/100 |
| **Total Fleet Distance** | 760.50 km | 782.92 km | 780.94 km | 780.94 km |
| **Distance Savings** | 0.00 km (0.00%) | -22.42 km (-2.95%) | -20.44 km (-2.69%) | -20.44 km (-2.69%) |
| **Avg Delivery Time** | 19.55 min | 20.81 min | 21.29 min | 21.29 min |
| **Time Delta** | 0.00 min | +1.26 min | +1.74 min | +1.74 min |
| **Min Delivery Time** | 7.13 min | 7.13 min | 7.13 min | 7.13 min |
| **Max Delivery Time** | 53.12 min | 53.12 min | 54.12 min | 54.12 min |
| **Avg Distance/Order** | 7.61 km | 7.83 km | 7.81 km | 7.81 km |
| **Late Deliveries (>45m)** | 3 | 4 | 4 | 4 |
| **Late Deliveries (>60m)** | 0 | 0 | 0 | 0 |
| **Fleet Utilization** | 11.41% | 11.73% | 11.67% | 11.67% |
| **Orders/Driver** | 1.47 | 1.59 | 1.59 | 1.59 |
| **Driver Savings** | 0 | 5 | 5 | 5 |

---

## Spread 100

**Configuration:**
- Orders: `data/doha_orders_spread_100.csv` (100 orders)
- Couriers: `data/doha_couriers_spread_100.csv` (100 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 100/100 | 100/100 | 100/100 | 100/100 |
| **Drivers Used** | 69/100 | 65/100 | 63/100 | 64/100 |
| **Total Fleet Distance** | 581.06 km | 598.75 km | 587.82 km | 578.50 km |
| **Distance Savings** | 0.00 km (0.00%) | -17.69 km (-3.04%) | -6.76 km (-1.16%) | 2.56 km (0.44%) |
| **Avg Delivery Time** | 16.38 min | 18.77 min | 19.71 min | 18.87 min |
| **Time Delta** | 0.00 min | +2.39 min | +3.33 min | +2.49 min |
| **Min Delivery Time** | 7.23 min | 8.17 min | 8.17 min | 8.23 min |
| **Max Delivery Time** | 42.98 min | 45.80 min | 48.33 min | 48.33 min |
| **Avg Distance/Order** | 5.81 km | 5.99 km | 5.88 km | 5.78 km |
| **Late Deliveries (>45m)** | 0 | 3 | 3 | 2 |
| **Late Deliveries (>60m)** | 0 | 0 | 0 | 0 |
| **Fleet Utilization** | 10.34% | 10.71% | 10.82% | 10.41% |
| **Orders/Driver** | 1.45 | 1.54 | 1.59 | 1.56 |
| **Driver Savings** | 0 | 4 | 6 | 5 |

---

## Clean (Full - 500 orders)

**Configuration:**
- Orders: `data/doha_orders_clean.csv` (500 orders)
- Couriers: `data/doha_couriers_clean.csv` (500 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 500/500 | 500/500 | N/A | N/A |
| **Drivers Used** | 347/500 | 276/500 | N/A | N/A |
| **Total Fleet Distance** | 2186.35 km | 2237.34 km | N/A | N/A |
| **Distance Savings** | 0.00 km (0.00%) | -50.99 km (-2.33%) | N/A | N/A |
| **Avg Delivery Time** | 14.12 min | 14.95 min | N/A | N/A |
| **Time Delta** | 0.00 min | +0.83 min | N/A | N/A |
| **Min Delivery Time** | 7.00 min | 7.00 min | N/A | N/A |
| **Max Delivery Time** | 42.73 min | 48.42 min | N/A | N/A |
| **Avg Distance/Order** | 4.37 km | 4.47 km | N/A | N/A |
| **Late Deliveries (>45m)** | 0 | 6 | N/A | N/A |
| **Late Deliveries (>60m)** | 0 | 0 | N/A | N/A |
| **Fleet Utilization** | 8.79% | 8.64% | N/A | N/A |
| **Orders/Driver** | 1.44 | 1.81 | N/A | N/A |
| **Driver Savings** | 0 | 71 | N/A | N/A |

---

## Hybrid (Full)

**Configuration:**
- Orders: `data/doha_orders_hybrid.csv` (300 orders)
- Couriers: `data/doha_couriers_hybrid.csv` (300 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 300/300 | 300/300 | N/A | N/A |
| **Drivers Used** | 210/300 | 178/300 | N/A | N/A |
| **Total Fleet Distance** | 2166.89 km | 2215.82 km | N/A | N/A |
| **Distance Savings** | 0.00 km (0.00%) | -48.93 km (-2.26%) | N/A | N/A |
| **Avg Delivery Time** | 18.92 min | 20.24 min | N/A | N/A |
| **Time Delta** | 0.00 min | +1.32 min | N/A | N/A |
| **Min Delivery Time** | 7.07 min | 7.07 min | N/A | N/A |
| **Max Delivery Time** | 52.78 min | 52.78 min | N/A | N/A |
| **Avg Distance/Order** | 7.22 km | 7.39 km | N/A | N/A |
| **Late Deliveries (>45m)** | 9 | 16 | N/A | N/A |
| **Late Deliveries (>60m)** | 0 | 0 | N/A | N/A |
| **Fleet Utilization** | 11.17% | 11.46% | N/A | N/A |
| **Orders/Driver** | 1.43 | 1.69 | N/A | N/A |
| **Driver Savings** | 0 | 32 | N/A | N/A |

---

## Spread (Full)

**Configuration:**
- Orders: `data/doha_orders_spread.csv` (300 orders)
- Couriers: `data/doha_couriers_spread.csv` (300 drivers)
- Order/Driver Ratio: 1.00:1

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:----------:|:-------------:|:--------:|
| **Orders Delivered** | 300/300 | 300/300 | N/A | N/A |
| **Drivers Used** | 218/300 | 179/300 | N/A | N/A |
| **Total Fleet Distance** | 1533.81 km | 1529.02 km | N/A | N/A |
| **Distance Savings** | 0.00 km (0.00%) | 4.79 km (0.31%) | N/A | N/A |
| **Avg Delivery Time** | 15.29 min | 18.84 min | N/A | N/A |
| **Time Delta** | 0.00 min | +3.55 min | N/A | N/A |
| **Min Delivery Time** | 7.17 min | 7.22 min | N/A | N/A |
| **Max Delivery Time** | 40.42 min | 49.15 min | N/A | N/A |
| **Avg Distance/Order** | 5.11 km | 5.10 km | N/A | N/A |
| **Late Deliveries (>45m)** | 0 | 7 | N/A | N/A |
| **Late Deliveries (>60m)** | 0 | 0 | N/A | N/A |
| **Fleet Utilization** | 10.06% | 9.28% | N/A | N/A |
| **Orders/Driver** | 1.38 | 1.68 | N/A | N/A |
| **Driver Savings** | 0 | 39 | N/A | N/A |

---

## Best Results Summary

| Scenario | Best Distance | Best Strategy | Savings vs Baseline | Drivers Used |
|:---------|:-------------:|:-------------:|:-------------------:|:------------:|
| Hybrid 100 + 50 Drivers (2:1 ratio) | 916.66 km | Adaptive | 29.97 km (3.17%) | 47/50 |
| Clean 100 | 399.03 km | Baseline | 0.00 km (0.00%) | 64/100 |
| Hybrid 100 (Full Drivers) | 760.50 km | Baseline | 0.00 km (0.00%) | 68/100 |
| Spread 100 | 578.50 km | Adaptive | 2.56 km (0.44%) | 64/100 |
| Clean (Full - 500 orders) | 2186.35 km | Baseline | 0.00 km (0.00%) | 347/500 |
| Hybrid (Full) | 2166.89 km | Baseline | 0.00 km (0.00%) | 210/300 |
| Spread (Full) | 1529.02 km | Sequential | 4.79 km (0.31%) | 179/300 |

---

*Report generated by benchmark.py*
