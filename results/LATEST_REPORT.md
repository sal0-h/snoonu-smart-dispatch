# Snoonu Logistics Benchmark Report

**Generated:** 2026-01-17 04:01:26

## Dispatch Strategies Compared

| Strategy | Description |
|:---------|:------------|
| **Baseline** | Greedy nearest-driver assignment. Industry standard - assigns each order to closest idle driver. |
| **Sequential** | Marginal cost bidding. Drivers bid based on additional cost to add an order to their route. |
| **Combinatorial** | Batch optimization. Groups orders into bundles and optimizes assignments globally. |
| **Adaptive** | Dynamic switching. Uses sequential for low load, combinatorial for high load. |

---

## Hybrid_100_50Drivers

- **Orders**: 100
- **Drivers**: 50
- **Ratio**: 2.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:--------:|:--------:|:--------:|
| **Distance (km)** | 946.63 | 927.93 (-1.98%) ✓ | 923.27 (-2.47%) ✓ | 916.66 (-3.17%) ✓ |
| **Avg Time (min)** | 22.77 | 24.57 (+7.91%)  | 24.71 (+8.52%)  | 24.32 (+6.81%)  |
| **Median Time (min)** | 18.69 | 19.57 (+4.71%)  | 19.57 (+4.71%)  | 19.22 (+2.84%)  |
| **P95 Time (min)** | 50.63 | 48.98 (-3.26%) ✓ | 50.63 | 50.63 |
| **Max Time (min)** | 53.12 | 53.12 | 54.12 (+1.88%)  | 54.12 (+1.88%)  |
| **Std Dev Time** | 12.38 | 13.41 (+8.32%)  | 13.61 (+9.94%)  | 13.37 (+8.0%)  |
| **Drivers Used** | 50 | 47 (-6.0%) ✓ | 47 (-6.0%) ✓ | 47 (-6.0%) ✓ |
| **Orders/Driver** | 2.0 | 2.13 (+6.5%) ✓ | 2.13 (+6.5%) ✓ | 2.13 (+6.5%) ✓ |
| **On-Time Rate %** | 75.0 | 67.0 (-10.67%)  | 67.0 (-10.67%)  | 69.0 (-8.0%)  |
| **Late >45m** | 8 | 13 (+62.5%)  | 12 (+50.0%)  | 11 (+37.5%)  |
| **Late >60m** | 0 | 0 | 0 | 0 |
| **Fleet Util %** | 26.68 | 27.04 (+1.35%) ✓ | 26.61 (-0.26%)  | 26.36 (-1.2%)  |

**Winner:** Adaptive saves **29.97 km (3.17%)**

---

## Clean_100

- **Orders**: 100
- **Drivers**: 100
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:--------:|:--------:|:--------:|
| **Distance (km)** | 399.03 | 410.47 (+2.87%)  | 420.3 (+5.33%)  | 421.56 (+5.65%)  |
| **Avg Time (min)** | 13.4 | 13.91 (+3.81%)  | 14.69 (+9.63%)  | 14.59 (+8.88%)  |
| **Median Time (min)** | 11.57 | 12.1 (+4.58%)  | 12.71 (+9.85%)  | 12.5 (+8.04%)  |
| **P95 Time (min)** | 28.65 | 29.45 (+2.79%)  | 37.72 (+31.66%)  | 37.72 (+31.66%)  |
| **Max Time (min)** | 41.57 | 47.07 (+13.23%)  | 47.07 (+13.23%)  | 47.07 (+13.23%)  |
| **Std Dev Time** | 6.32 | 7.58 (+19.94%)  | 8.28 (+31.01%)  | 8.07 (+27.69%)  |
| **Drivers Used** | 64 | 60 (-6.25%) ✓ | 58 (-9.38%) ✓ | 59 (-7.81%) ✓ |
| **Orders/Driver** | 1.56 | 1.67 (+7.05%) ✓ | 1.72 (+10.26%) ✓ | 1.69 (+8.33%) ✓ |
| **On-Time Rate %** | 97.0 | 96.0 (-1.03%)  | 94.0 (-3.09%)  | 95.0 (-2.06%)  |
| **Late >45m** | 0 | 1 | 2 | 2 |
| **Late >60m** | 0 | 0 | 0 | 0 |
| **Fleet Util %** | 9.03 | 8.49 (-5.98%)  | 8.66 (-4.1%)  | 8.65 (-4.21%)  |

---

## Hybrid_100_FullDrivers

- **Orders**: 100
- **Drivers**: 100
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:--------:|:--------:|:--------:|
| **Distance (km)** | 760.5 | 782.92 (+2.95%)  | 780.94 (+2.69%)  | 780.94 (+2.69%)  |
| **Avg Time (min)** | 19.55 | 20.81 (+6.45%)  | 21.29 (+8.9%)  | 21.29 (+8.9%)  |
| **Median Time (min)** | 14.97 | 15.53 (+3.74%)  | 15.68 (+4.74%)  | 15.68 (+4.74%)  |
| **P95 Time (min)** | 42.62 | 44.72 (+4.93%)  | 44.98 (+5.54%)  | 44.98 (+5.54%)  |
| **Max Time (min)** | 53.12 | 53.12 | 54.12 (+1.88%)  | 54.12 (+1.88%)  |
| **Std Dev Time** | 11.14 | 12.22 (+9.69%)  | 12.25 (+9.96%)  | 12.25 (+9.96%)  |
| **Drivers Used** | 68 | 63 (-7.35%) ✓ | 63 (-7.35%) ✓ | 63 (-7.35%) ✓ |
| **Orders/Driver** | 1.47 | 1.59 (+8.16%) ✓ | 1.59 (+8.16%) ✓ | 1.59 (+8.16%) ✓ |
| **On-Time Rate %** | 80.0 | 74.0 (-7.5%)  | 72.0 (-10.0%)  | 72.0 (-10.0%)  |
| **Late >45m** | 3 | 4 (+33.33%)  | 4 (+33.33%)  | 4 (+33.33%)  |
| **Late >60m** | 0 | 0 | 0 | 0 |
| **Fleet Util %** | 11.41 | 11.73 (+2.8%) ✓ | 11.67 (+2.28%) ✓ | 11.67 (+2.28%) ✓ |

---

## Spread_100

- **Orders**: 100
- **Drivers**: 100
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential | Combinatorial | Adaptive |
|:-------|:--------:|:--------:|:--------:|:--------:|
| **Distance (km)** | 581.06 | 598.75 (+3.04%)  | 587.82 (+1.16%)  | 578.5 (-0.44%) ✓ |
| **Avg Time (min)** | 16.38 | 18.77 (+14.59%)  | 19.71 (+20.33%)  | 18.87 (+15.2%)  |
| **Median Time (min)** | 15.11 | 15.83 (+4.77%)  | 16.32 (+8.01%)  | 16.32 (+8.01%)  |
| **P95 Time (min)** | 29.45 | 42.98 (+45.94%)  | 43.77 (+48.62%)  | 42.95 (+45.84%)  |
| **Max Time (min)** | 42.98 | 45.8 (+6.56%)  | 48.33 (+12.45%)  | 48.33 (+12.45%)  |
| **Std Dev Time** | 6.48 | 9.38 (+44.75%)  | 9.94 (+53.4%)  | 8.91 (+37.5%)  |
| **Drivers Used** | 69 | 65 (-5.8%) ✓ | 63 (-8.7%) ✓ | 64 (-7.25%) ✓ |
| **Orders/Driver** | 1.45 | 1.54 (+6.21%) ✓ | 1.59 (+9.66%) ✓ | 1.56 (+7.59%) ✓ |
| **On-Time Rate %** | 98.0 | 87.0 (-11.22%)  | 85.0 (-13.27%)  | 90.0 (-8.16%)  |
| **Late >45m** | 0 | 3 | 3 | 2 |
| **Late >60m** | 0 | 0 | 0 | 0 |
| **Fleet Util %** | 10.34 | 10.71 (+3.58%) ✓ | 10.82 (+4.64%) ✓ | 10.41 (+0.68%) ✓ |

**Winner:** Adaptive saves **2.56 km (0.44%)**

---

## Clean_500

- **Orders**: 500
- **Drivers**: 500
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential |
|:-------|:--------:|:--------:|
| **Distance (km)** | 2186.35 | 2237.34 (+2.33%)  |
| **Avg Time (min)** | 14.12 | 14.95 (+5.88%)  |
| **Median Time (min)** | 11.54 | 11.81 (+2.34%)  |
| **P95 Time (min)** | 29.52 | 34.5 (+16.87%)  |
| **Max Time (min)** | 42.73 | 48.42 (+13.32%)  |
| **Std Dev Time** | 7.09 | 8.43 (+18.9%)  |
| **Drivers Used** | 347 | 276 (-20.46%) ✓ |
| **Orders/Driver** | 1.44 | 1.81 (+25.69%) ✓ |
| **On-Time Rate %** | 95.6 | 93.4 (-2.3%)  |
| **Late >45m** | 0 | 6 |
| **Late >60m** | 0 | 0 |
| **Fleet Util %** | 8.79 | 8.64 (-1.71%)  |

---

## Hybrid_300

- **Orders**: 300
- **Drivers**: 300
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential |
|:-------|:--------:|:--------:|
| **Distance (km)** | 2166.89 | 2215.82 (+2.26%)  |
| **Avg Time (min)** | 18.92 | 20.24 (+6.98%)  |
| **Median Time (min)** | 14.72 | 15.77 (+7.13%)  |
| **P95 Time (min)** | 39.88 | 45.63 (+14.42%)  |
| **Max Time (min)** | 52.78 | 52.78 |
| **Std Dev Time** | 11.04 | 12.13 (+9.87%)  |
| **Drivers Used** | 210 | 178 (-15.24%) ✓ |
| **Orders/Driver** | 1.43 | 1.69 (+18.18%) ✓ |
| **On-Time Rate %** | 80.67 | 76.67 (-4.96%)  |
| **Late >45m** | 9 | 16 (+77.78%)  |
| **Late >60m** | 0 | 0 |
| **Fleet Util %** | 11.17 | 11.46 (+2.6%) ✓ |

---

## Spread_300

- **Orders**: 300
- **Drivers**: 300
- **Ratio**: 1.0:1

### Key Performance Metrics

| Metric | Baseline | Sequential |
|:-------|:--------:|:--------:|
| **Distance (km)** | 1533.81 | 1529.02 (-0.31%) ✓ |
| **Avg Time (min)** | 15.29 | 18.84 (+23.22%)  |
| **Median Time (min)** | 14.52 | 15.54 (+7.02%)  |
| **P95 Time (min)** | 23.88 | 42.72 (+78.89%)  |
| **Max Time (min)** | 40.42 | 49.15 (+21.6%)  |
| **Std Dev Time** | 4.95 | 9.73 (+96.57%)  |
| **Drivers Used** | 218 | 179 (-17.89%) ✓ |
| **Orders/Driver** | 1.38 | 1.68 (+21.74%) ✓ |
| **On-Time Rate %** | 99.0 | 85.33 (-13.81%)  |
| **Late >45m** | 0 | 7 |
| **Late >60m** | 0 | 0 |
| **Fleet Util %** | 10.06 | 9.28 (-7.75%)  |

**Winner:** Sequential saves **4.79 km (0.31%)**

---

## Summary

| Scenario | Best Strategy | Distance Savings | Time Delta | Drivers Saved |
|:---------|:-------------:|:----------------:|:----------:|:-------------:|
| Hybrid_100_50Drivers | Adaptive | 29.97 km (3.2%) | +1.55 min | 3 |
| Clean_100 | Baseline | 0 km | 0 min | 0 |
| Hybrid_100_FullDrivers | Baseline | 0 km | 0 min | 0 |
| Spread_100 | Adaptive | 2.56 km (0.4%) | +2.49 min | 5 |
| Clean_500 | Baseline | 0 km | 0 min | 0 |
| Hybrid_300 | Baseline | 0 km | 0 min | 0 |
| Spread_300 | Sequential | 4.79 km (0.3%) | +3.55 min | 39 |

---
*Report generated by benchmark.py*
