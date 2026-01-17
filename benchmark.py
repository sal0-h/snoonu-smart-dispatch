# snoonu-smart-dispatch/benchmark.py
"""
Comprehensive benchmark script for Snoonu Smart Dispatch Optimization Engine.
Outputs detailed CSV files for statistical analysis with comparison to baseline.
"""

import copy
import csv
import json
import os
from datetime import datetime
from src.simulation import Simulation

# Define all test scenarios
SCENARIOS = [
    {
        "name": "Hybrid_100_50Drivers",
        "orders": "data/doha_orders_hybrid_100.csv",
        "couriers": "data/doha_couriers_50.csv",
    },
    {
        "name": "Clean_100",
        "orders": "data/doha_orders_clean_100.csv",
        "couriers": "data/doha_couriers_clean_100.csv",
    },
    {
        "name": "Hybrid_100_FullDrivers",
        "orders": "data/doha_orders_hybrid_100.csv",
        "couriers": "data/doha_couriers_hybrid_100.csv",
    },
    {
        "name": "Spread_100",
        "orders": "data/doha_orders_spread_100.csv",
        "couriers": "data/doha_couriers_spread_100.csv",
    },
]

LARGE_SCENARIOS = [
    {
        "name": "Clean_500",
        "orders": "data/doha_orders_clean.csv",
        "couriers": "data/doha_couriers_clean.csv",
    },
    {
        "name": "Hybrid_300",
        "orders": "data/doha_orders_hybrid.csv",
        "couriers": "data/doha_couriers_hybrid.csv",
    },
    {
        "name": "Spread_300",
        "orders": "data/doha_orders_spread.csv",
        "couriers": "data/doha_couriers_spread.csv",
    },
]

STRATEGIES = ["baseline", "sequential", "combinatorial", "adaptive"]

# All KPIs for CSV output (30 metrics)
CSV_KPIS = [
    # Delivery Performance
    "orders_delivered",
    "total_orders",
    "delivery_success_rate_pct",
    
    # Driver Efficiency
    "drivers_used",
    "total_drivers",
    "drivers_idle",
    "driver_utilization_rate_pct",
    "orders_per_driver",
    "fleet_utilization_pct",
    
    # Delivery Time Statistics
    "avg_delivery_time_min",
    "median_delivery_time_min",
    "min_delivery_time_min",
    "max_delivery_time_min",
    "std_delivery_time_min",
    "p90_delivery_time_min",
    "p95_delivery_time_min",
    "p99_delivery_time_min",
    
    # Distance Metrics
    "total_fleet_distance_km",
    "avg_distance_per_order_km",
    "distance_per_driver_km",
    
    # On-Time Performance
    "on_time_deliveries",
    "on_time_rate_pct",
    "early_deliveries_under_15m",
    "late_deliveries_over_30m",
    "late_deliveries_over_45m",
    "late_deliveries_over_60m",
    "late_rate_45m_pct",
    "late_rate_60m_pct",
    
    # Efficiency Ratios
    "time_efficiency_ratio",
]

# Metrics where LOWER is better (for highlighting improvements)
LOWER_IS_BETTER = [
    "total_fleet_distance_km",
    "avg_delivery_time_min",
    "median_delivery_time_min",
    "max_delivery_time_min",
    "std_delivery_time_min",
    "p90_delivery_time_min",
    "p95_delivery_time_min",
    "p99_delivery_time_min",
    "avg_distance_per_order_km",
    "drivers_used",
    "late_deliveries_over_30m",
    "late_deliveries_over_45m",
    "late_deliveries_over_60m",
    "late_rate_45m_pct",
    "late_rate_60m_pct",
]


def run_scenario(scenario: dict, strategies_to_run: list = None, quiet: bool = True) -> dict:
    """Run all strategies on a single scenario and return results."""
    if strategies_to_run is None:
        strategies_to_run = STRATEGIES
        
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"Orders: {scenario['orders']}")
    print(f"Couriers: {scenario['couriers']}")
    print(f"{'='*60}")
    
    try:
        initial_drivers, initial_orders = Simulation.load_data(
            scenario['orders'], scenario['couriers']
        )
    except FileNotFoundError as e:
        print(f"  ERROR: Could not load data - {e}")
        return None
    
    if not initial_drivers or not initial_orders:
        print(f"  ERROR: Empty data loaded")
        return None
    
    print(f"  Loaded {len(initial_orders)} orders, {len(initial_drivers)} drivers")
    
    scenario_results = {
        "scenario": scenario['name'],
        "orders_file": scenario['orders'],
        "couriers_file": scenario['couriers'],
        "total_orders": len(initial_orders),
        "total_drivers": len(initial_drivers),
        "order_driver_ratio": round(len(initial_orders)/len(initial_drivers), 2),
        "strategies": {}
    }
    
    for strategy in strategies_to_run:
        print(f"\n  Running {strategy.upper()}...")
        sim = Simulation(copy.deepcopy(initial_drivers), copy.deepcopy(initial_orders))
        
        # Suppress tick-by-tick output
        import sys
        from io import StringIO
        if quiet:
            old_stdout = sys.stdout
            sys.stdout = StringIO()
        
        try:
            results = sim.run(strategy)
        finally:
            if quiet:
                sys.stdout = old_stdout
        
        scenario_results["strategies"][strategy] = results
        
        dist = results.get("total_fleet_distance_km", 0)
        time_avg = results.get("avg_delivery_time_min", 0)
        drivers = results.get("drivers_used", 0)
        print(f"    ✓ {strategy}: {dist:.2f} km, {time_avg:.2f} min, {drivers} drivers")
    
    return scenario_results


def calculate_comparison_stats(results: dict, baseline_key: str = "baseline") -> dict:
    """Calculate comparison statistics vs baseline for each strategy."""
    if baseline_key not in results["strategies"]:
        return results
    
    baseline = results["strategies"][baseline_key]
    
    for strategy, data in results["strategies"].items():
        comparison = {}
        comparison_pct = {}
        is_improvement = {}
        
        for kpi in CSV_KPIS:
            baseline_val = baseline.get(kpi, 0)
            strategy_val = data.get(kpi, 0)
            
            if baseline_val is None:
                baseline_val = 0
            if strategy_val is None:
                strategy_val = 0
            
            # Absolute difference
            diff = strategy_val - baseline_val
            comparison[kpi] = round(diff, 4)
            
            # Percentage difference
            if baseline_val != 0:
                pct_diff = ((strategy_val - baseline_val) / abs(baseline_val)) * 100
                comparison_pct[kpi] = round(pct_diff, 2)
            else:
                comparison_pct[kpi] = 0
            
            # Determine if this is an improvement
            if strategy == baseline_key:
                is_improvement[kpi] = False
            elif kpi in LOWER_IS_BETTER:
                is_improvement[kpi] = diff < 0  # Lower is better
            else:
                is_improvement[kpi] = diff > 0  # Higher is better
        
        data["vs_baseline"] = comparison
        data["vs_baseline_pct"] = comparison_pct
        data["is_improvement"] = is_improvement
    
    return results


def save_scenario_csv(results: dict, output_dir: str, timestamp: str):
    """Save detailed CSV for a single scenario with all strategies and comparisons."""
    scenario_name = results["scenario"]
    filename = f"{output_dir}/{scenario_name}_{timestamp}.csv"
    
    strategies = list(results["strategies"].keys())
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header row
        header = ["KPI", "Category", "Lower_Is_Better"]
        for strat in strategies:
            header.append(f"{strat}")
            if strat != "baseline":
                header.append(f"{strat}_vs_baseline")
                header.append(f"{strat}_vs_baseline_pct")
                header.append(f"{strat}_is_improvement")
        writer.writerow(header)
        
        # Metadata rows
        writer.writerow(["_scenario", "metadata", "", scenario_name] + [""] * (len(header) - 4))
        writer.writerow(["_total_orders", "metadata", "", results["total_orders"]] + [""] * (len(header) - 4))
        writer.writerow(["_total_drivers", "metadata", "", results["total_drivers"]] + [""] * (len(header) - 4))
        writer.writerow(["_order_driver_ratio", "metadata", "", results["order_driver_ratio"]] + [""] * (len(header) - 4))
        writer.writerow(["_timestamp", "metadata", "", timestamp] + [""] * (len(header) - 4))
        writer.writerow([])  # Empty row separator
        
        # KPI categories for organization
        kpi_categories = {
            "orders_delivered": "delivery",
            "total_orders": "delivery",
            "delivery_success_rate_pct": "delivery",
            "drivers_used": "efficiency",
            "total_drivers": "efficiency",
            "drivers_idle": "efficiency",
            "driver_utilization_rate_pct": "efficiency",
            "orders_per_driver": "efficiency",
            "fleet_utilization_pct": "efficiency",
            "avg_delivery_time_min": "time",
            "median_delivery_time_min": "time",
            "min_delivery_time_min": "time",
            "max_delivery_time_min": "time",
            "std_delivery_time_min": "time",
            "p90_delivery_time_min": "time",
            "p95_delivery_time_min": "time",
            "p99_delivery_time_min": "time",
            "total_fleet_distance_km": "distance",
            "avg_distance_per_order_km": "distance",
            "distance_per_driver_km": "distance",
            "on_time_deliveries": "on_time",
            "on_time_rate_pct": "on_time",
            "early_deliveries_under_15m": "on_time",
            "late_deliveries_over_30m": "late",
            "late_deliveries_over_45m": "late",
            "late_deliveries_over_60m": "late",
            "late_rate_45m_pct": "late",
            "late_rate_60m_pct": "late",
            "time_efficiency_ratio": "efficiency",
        }
        
        # KPI rows
        for kpi in CSV_KPIS:
            category = kpi_categories.get(kpi, "other")
            lower_better = "yes" if kpi in LOWER_IS_BETTER else "no"
            
            row = [kpi, category, lower_better]
            
            for strat in strategies:
                strat_data = results["strategies"][strat]
                row.append(strat_data.get(kpi, ""))
                
                if strat != "baseline":
                    vs_baseline = strat_data.get("vs_baseline", {})
                    vs_baseline_pct = strat_data.get("vs_baseline_pct", {})
                    is_improvement = strat_data.get("is_improvement", {})
                    
                    row.append(vs_baseline.get(kpi, ""))
                    row.append(vs_baseline_pct.get(kpi, ""))
                    row.append("yes" if is_improvement.get(kpi, False) else "no")
            
            writer.writerow(row)
    
    print(f"  ✓ Saved: {filename}")
    return filename


def save_master_csv(all_results: list, output_dir: str, timestamp: str):
    """Save a master CSV with all scenarios and strategies in a flat format."""
    filename = f"{output_dir}/MASTER_DATA_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["scenario", "orders", "drivers", "ratio", "strategy"]
        for kpi in CSV_KPIS:
            header.append(kpi)
            header.append(f"{kpi}_vs_baseline")
            header.append(f"{kpi}_vs_baseline_pct")
        writer.writerow(header)
        
        # Data rows
        for result in all_results:
            if result is None:
                continue
            
            for strategy, data in result["strategies"].items():
                row = [
                    result["scenario"],
                    result["total_orders"],
                    result["total_drivers"],
                    result["order_driver_ratio"],
                    strategy,
                ]
                
                for kpi in CSV_KPIS:
                    row.append(data.get(kpi, ""))
                    vs_baseline = data.get("vs_baseline", {})
                    vs_baseline_pct = data.get("vs_baseline_pct", {})
                    row.append(vs_baseline.get(kpi, ""))
                    row.append(vs_baseline_pct.get(kpi, ""))
                
                writer.writerow(row)
    
    print(f"✓ Saved master data: {filename}")
    return filename


def save_summary_csv(all_results: list, output_dir: str, timestamp: str):
    """Save a summary CSV with key metrics for quick analysis."""
    filename = f"{output_dir}/SUMMARY_{timestamp}.csv"
    
    # Key metrics for summary
    key_metrics = [
        ("Total Distance (km)", "total_fleet_distance_km"),
        ("Avg Delivery Time (min)", "avg_delivery_time_min"),
        ("Median Delivery Time (min)", "median_delivery_time_min"),
        ("P95 Delivery Time (min)", "p95_delivery_time_min"),
        ("Drivers Used", "drivers_used"),
        ("Orders/Driver", "orders_per_driver"),
        ("On-Time Rate %", "on_time_rate_pct"),
        ("Late >45m Count", "late_deliveries_over_45m"),
        ("Late >60m Count", "late_deliveries_over_60m"),
        ("Fleet Utilization %", "fleet_utilization_pct"),
        ("Distance/Driver (km)", "distance_per_driver_km"),
        ("Std Dev Time (min)", "std_delivery_time_min"),
    ]
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["Scenario", "Orders", "Drivers", "Ratio", "Strategy"]
        for display_name, _ in key_metrics:
            header.append(display_name)
            header.append(f"{display_name} vs Baseline %")
        writer.writerow(header)
        
        # Data rows
        for result in all_results:
            if result is None:
                continue
            
            for strategy, data in result["strategies"].items():
                row = [
                    result["scenario"],
                    result["total_orders"],
                    result["total_drivers"],
                    result["order_driver_ratio"],
                    strategy,
                ]
                
                for _, kpi_key in key_metrics:
                    row.append(data.get(kpi_key, ""))
                    vs_pct = data.get("vs_baseline_pct", {})
                    row.append(vs_pct.get(kpi_key, 0))
                
                writer.writerow(row)
    
    print(f"✓ Saved summary: {filename}")
    return filename


def save_improvements_csv(all_results: list, output_dir: str, timestamp: str):
    """Save a CSV showing only improvements vs baseline."""
    filename = f"{output_dir}/IMPROVEMENTS_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        header = [
            "Scenario", "Strategy", "Metric", "Category",
            "Baseline_Value", "Strategy_Value", "Difference", "Improvement_%", "Is_Improvement"
        ]
        writer.writerow(header)
        
        for result in all_results:
            if result is None:
                continue
            
            baseline = result["strategies"].get("baseline", {})
            
            for strategy, data in result["strategies"].items():
                if strategy == "baseline":
                    continue
                
                for kpi in CSV_KPIS:
                    baseline_val = baseline.get(kpi, 0)
                    strategy_val = data.get(kpi, 0)
                    diff = data.get("vs_baseline", {}).get(kpi, 0)
                    pct = data.get("vs_baseline_pct", {}).get(kpi, 0)
                    is_improvement = data.get("is_improvement", {}).get(kpi, False)
                    
                    # Determine category
                    if "time" in kpi or "delivery" in kpi.lower():
                        category = "Time"
                    elif "distance" in kpi or "km" in kpi:
                        category = "Distance"
                    elif "driver" in kpi:
                        category = "Drivers"
                    elif "late" in kpi:
                        category = "Late Deliveries"
                    elif "on_time" in kpi:
                        category = "On-Time"
                    else:
                        category = "Other"
                    
                    writer.writerow([
                        result["scenario"],
                        strategy,
                        kpi,
                        category,
                        baseline_val,
                        strategy_val,
                        diff,
                        pct,
                        "yes" if is_improvement else "no"
                    ])
    
    print(f"✓ Saved improvements: {filename}")
    return filename


def save_best_strategy_csv(all_results: list, output_dir: str, timestamp: str):
    """Save CSV showing best strategy for each metric in each scenario."""
    filename = f"{output_dir}/BEST_STRATEGIES_{timestamp}.csv"
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        header = [
            "Scenario", "Metric", "Lower_Is_Better", "Best_Strategy", 
            "Best_Value", "Baseline_Value", "Improvement", "Improvement_%"
        ]
        writer.writerow(header)
        
        for result in all_results:
            if result is None:
                continue
            
            baseline_data = result["strategies"].get("baseline", {})
            
            for kpi in CSV_KPIS:
                lower_better = kpi in LOWER_IS_BETTER
                best_strategy = None
                best_value = None
                
                for strategy, data in result["strategies"].items():
                    val = data.get(kpi)
                    if val is None:
                        continue
                    
                    if best_value is None:
                        best_value = val
                        best_strategy = strategy
                    elif lower_better and val < best_value:
                        best_value = val
                        best_strategy = strategy
                    elif not lower_better and val > best_value:
                        best_value = val
                        best_strategy = strategy
                
                baseline_val = baseline_data.get(kpi, 0)
                if baseline_val is None:
                    baseline_val = 0
                    
                improvement = (best_value - baseline_val) if best_value is not None else 0
                improvement_pct = 0
                if baseline_val and baseline_val != 0 and best_value is not None:
                    improvement_pct = round((improvement / abs(baseline_val)) * 100, 2)
                
                writer.writerow([
                    result["scenario"],
                    kpi,
                    "yes" if lower_better else "no",
                    best_strategy,
                    best_value,
                    baseline_val,
                    round(improvement, 4) if improvement else 0,
                    improvement_pct
                ])
    
    print(f"✓ Saved best strategies: {filename}")
    return filename


def generate_markdown_report(all_results: list, output_dir: str, timestamp: str):
    """Generate a markdown report with tables."""
    filename = f"{output_dir}/REPORT_{timestamp}.md"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Snoonu Smart Dispatch Benchmark Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Dispatch Strategies Compared\n\n")
        f.write("| Strategy | Description |\n")
        f.write("|:---------|:------------|\n")
        f.write("| **Baseline** | Greedy nearest-driver assignment. Industry standard - assigns each order to closest idle driver. |\n")
        f.write("| **Sequential** | Marginal cost bidding. Drivers bid based on additional cost to add an order to their route. |\n")
        f.write("| **Combinatorial** | Batch optimization. Groups orders into bundles and optimizes assignments globally. |\n")
        f.write("| **Adaptive** | Dynamic switching. Uses sequential for low load, combinatorial for high load. |\n\n")
        
        f.write("---\n\n")
        
        # Results for each scenario
        for result in all_results:
            if result is None:
                continue
            
            f.write(f"## {result['scenario']}\n\n")
            f.write(f"- **Orders**: {result['total_orders']}\n")
            f.write(f"- **Drivers**: {result['total_drivers']}\n")
            f.write(f"- **Ratio**: {result['order_driver_ratio']}:1\n\n")
            
            # Key metrics table
            strategies = list(result["strategies"].keys())
            
            f.write("### Key Performance Metrics\n\n")
            
            header = "| Metric |"
            for strat in strategies:
                header += f" {strat.title()} |"
            f.write(header + "\n")
            
            sep = "|:-------|"
            for _ in strategies:
                sep += ":--------:|"
            f.write(sep + "\n")
            
            key_display = [
                ("Distance (km)", "total_fleet_distance_km"),
                ("Avg Time (min)", "avg_delivery_time_min"),
                ("Median Time (min)", "median_delivery_time_min"),
                ("P95 Time (min)", "p95_delivery_time_min"),
                ("Max Time (min)", "max_delivery_time_min"),
                ("Std Dev Time", "std_delivery_time_min"),
                ("Drivers Used", "drivers_used"),
                ("Orders/Driver", "orders_per_driver"),
                ("On-Time Rate %", "on_time_rate_pct"),
                ("Late >45m", "late_deliveries_over_45m"),
                ("Late >60m", "late_deliveries_over_60m"),
                ("Fleet Util %", "fleet_utilization_pct"),
            ]
            
            for display_name, kpi in key_display:
                row = f"| **{display_name}** |"
                for strat in strategies:
                    data = result["strategies"].get(strat, {})
                    val = data.get(kpi, "N/A")
                    
                    if strat != "baseline" and val != "N/A":
                        vs_pct = data.get("vs_baseline_pct", {}).get(kpi, 0)
                        is_better = data.get("is_improvement", {}).get(kpi, False)
                        
                        if vs_pct != 0:
                            sign = "+" if vs_pct > 0 else ""
                            indicator = "✓" if is_better else ""
                            row += f" {val} ({sign}{vs_pct}%) {indicator} |"
                        else:
                            row += f" {val} |"
                    else:
                        row += f" {val} |"
                f.write(row + "\n")
            
            f.write("\n")
            
            # Winner highlight
            baseline_dist = result["strategies"].get("baseline", {}).get("total_fleet_distance_km", 0)
            best_strat = "baseline"
            best_dist = baseline_dist
            
            for strat, data in result["strategies"].items():
                dist = data.get("total_fleet_distance_km", float('inf'))
                if dist < best_dist:
                    best_dist = dist
                    best_strat = strat
            
            if best_strat != "baseline":
                savings = baseline_dist - best_dist
                savings_pct = (savings / baseline_dist * 100) if baseline_dist > 0 else 0
                f.write(f"**Winner:** {best_strat.title()} saves **{savings:.2f} km ({savings_pct:.2f}%)**\n\n")
            
            f.write("---\n\n")
        
        f.write("## Summary\n\n")
        f.write("| Scenario | Best Strategy | Distance Savings | Time Delta | Drivers Saved |\n")
        f.write("|:---------|:-------------:|:----------------:|:----------:|:-------------:|\n")
        
        for result in all_results:
            if result is None:
                continue
            
            baseline = result["strategies"].get("baseline", {})
            baseline_dist = baseline.get("total_fleet_distance_km", 0)
            baseline_time = baseline.get("avg_delivery_time_min", 0)
            baseline_drivers = baseline.get("drivers_used", 0)
            
            best_strat = "baseline"
            best_dist = baseline_dist
            
            for strat, data in result["strategies"].items():
                dist = data.get("total_fleet_distance_km", float('inf'))
                if dist < best_dist:
                    best_dist = dist
                    best_strat = strat
            
            best_data = result["strategies"].get(best_strat, {})
            
            if best_strat == "baseline":
                f.write(f"| {result['scenario']} | Baseline | 0 km | 0 min | 0 |\n")
            else:
                dist_save = baseline_dist - best_dist
                dist_pct = (dist_save / baseline_dist * 100) if baseline_dist > 0 else 0
                time_delta = best_data.get("avg_delivery_time_min", 0) - baseline_time
                driver_save = baseline_drivers - best_data.get("drivers_used", baseline_drivers)
                
                f.write(f"| {result['scenario']} | {best_strat.title()} | {dist_save:.2f} km ({dist_pct:.1f}%) | +{time_delta:.2f} min | {driver_save} |\n")
        
        f.write("\n---\n")
        f.write("*Report generated by benchmark.py*\n")
    
    print(f"✓ Saved report: {filename}")
    return filename


def main():
    """Run the full benchmark suite."""
    print("=" * 60)
    print("SNOONU LOGISTICS BENCHMARK SUITE")
    print("=" * 60)
    
    # Create output directory
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    all_results = []
    
    # Run small scenarios with all strategies
    for scenario in SCENARIOS:
        result = run_scenario(scenario, strategies_to_run=STRATEGIES, quiet=True)
        if result:
            result = calculate_comparison_stats(result)
            all_results.append(result)
            save_scenario_csv(result, "results", timestamp)
    
    # Run large scenarios with baseline + sequential only
    print(f"\n{'='*60}")
    print("LARGE SCENARIOS (Baseline + Sequential only)")
    print("=" * 60)
    
    for scenario in LARGE_SCENARIOS:
        result = run_scenario(scenario, strategies_to_run=["baseline", "sequential"], quiet=True)
        if result:
            result = calculate_comparison_stats(result)
            all_results.append(result)
            save_scenario_csv(result, "results", timestamp)
    
    # Save all summary files
    print(f"\n{'='*60}")
    print("GENERATING SUMMARY FILES")
    print("=" * 60)
    
    save_master_csv(all_results, "results", timestamp)
    save_summary_csv(all_results, "results", timestamp)
    save_improvements_csv(all_results, "results", timestamp)
    save_best_strategy_csv(all_results, "results", timestamp)
    generate_markdown_report(all_results, "results", timestamp)
    
    # Save JSON for programmatic access
    json_file = f"results/benchmark_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"✓ Saved JSON: {json_file}")
    
    # Copy to LATEST files
    import shutil
    for src_pattern in ["SUMMARY", "MASTER_DATA", "IMPROVEMENTS", "BEST_STRATEGIES", "REPORT"]:
        src = f"results/{src_pattern}_{timestamp}.csv" if src_pattern != "REPORT" else f"results/{src_pattern}_{timestamp}.md"
        dst = f"results/LATEST_{src_pattern}.csv" if src_pattern != "REPORT" else f"results/LATEST_{src_pattern}.md"
        if os.path.exists(src):
            shutil.copy(src, dst)
    
    print("\n✓ Updated LATEST files")
    
    print(f"\n{'='*60}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*60}")
    print(f"\nOutput files in results/ directory:")
    print(f"  - {scenario['name']}_{timestamp}.csv (one per scenario)")
    print(f"  - MASTER_DATA_{timestamp}.csv (all data flat)")
    print(f"  - SUMMARY_{timestamp}.csv (key metrics)")
    print(f"  - IMPROVEMENTS_{timestamp}.csv (changes vs baseline)")
    print(f"  - BEST_STRATEGIES_{timestamp}.csv (winners per metric)")
    print(f"  - REPORT_{timestamp}.md (human-readable report)")
    print(f"  - benchmark_{timestamp}.json (raw JSON)")


if __name__ == "__main__":
    main()
