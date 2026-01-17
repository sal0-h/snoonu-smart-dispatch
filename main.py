#!/usr/bin/env python3
# snoonu-smart-dispatch/main.py
"""
Command-Line Interface for the Snoonu Last-Mile Delivery Simulation.

This script serves as a CLI fallback if Streamlit fails, and as a quick
way to run simulations without the UI overhead.

Usage:
    python main.py                          # Run with defaults
    python main.py --dataset clean_100      # Run specific dataset
    python main.py --strategies baseline combinatorial  # Compare strategies
    python main.py --verbose                # Show detailed output

Exit Codes:
    0: Success
    1: Data loading error
    2: Simulation error
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from typing import Dict, List, Any, Optional

# Ensure src package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.simulation import Simulation


# Available datasets
DATASETS: Dict[str, Dict[str, str]] = {
    "clean_100": {
        "orders": "data/doha_orders_clean_100.csv",
        "couriers": "data/doha_couriers_clean_100.csv",
        "description": "100 orders, clean urban scenario"
    },
    "clean": {
        "orders": "data/doha_orders_clean.csv",
        "couriers": "data/doha_couriers_clean.csv",
        "description": "Full clean urban scenario"
    },
    "hybrid_100": {
        "orders": "data/doha_orders_hybrid_100.csv",
        "couriers": "data/doha_couriers_hybrid_100.csv",
        "description": "100 orders, mixed urban/suburban"
    },
    "hybrid": {
        "orders": "data/doha_orders_hybrid.csv",
        "couriers": "data/doha_couriers_hybrid.csv",
        "description": "Full mixed urban/suburban scenario"
    },
    "spread_100": {
        "orders": "data/doha_orders_spread_100.csv",
        "couriers": "data/doha_couriers_spread_100.csv",
        "description": "100 orders, geographically spread"
    },
    "spread": {
        "orders": "data/doha_orders_spread.csv",
        "couriers": "data/doha_couriers_spread.csv",
        "description": "Full geographically spread scenario"
    },
    "stress": {
        "orders": "data/doha_orders_stress.csv",
        "couriers": "data/doha_couriers_stress.csv",
        "description": "High-volume stress test scenario"
    },
    "test_50": {
        "orders": "data/doha_test_orders_50.csv",
        "couriers": "data/doha_couriers_50.csv",
        "description": "50 orders, quick test scenario"
    },
}

AVAILABLE_STRATEGIES = ["baseline", "sequential", "combinatorial", "adaptive"]


def print_header() -> None:
    """Print the CLI header."""
    print("\n" + "=" * 60)
    print("  SNOONU LOGISTICS - Last-Mile Delivery Simulation")
    print("  Bidding-Based Dispatch Strategy Comparison")
    print("=" * 60 + "\n")


def print_results_table(results: Dict[str, Dict[str, Any]]) -> None:
    """
    Print a formatted comparison table of results.
    
    Args:
        results: Dictionary mapping strategy name to KPI results
    """
    metrics = [
        "Total Deliveries",
        "Avg Delivery Time",
        "Total Fleet Distance",
        "Late Deliveries (>60m)",
        "Fleet Utilization",
        "Drivers Used",
        "Active Driver Efficiency",  # THE KEY METRIC
    ]

    strategies = list(results.keys())

    print("\n" + "=" * 60)
    print("  FINAL RESULTS COMPARISON")
    print("=" * 60 + "\n")
    
    # Header
    header = "| Metric                    |"
    for strat in strategies:
        header += f" {strat.title():^15} |"
    print(header)
    
    separator = "|" + "-" * 27 + "|"
    for _ in strategies:
        separator += "-" * 17 + "|"
    print(separator)

    # Rows
    for metric in metrics:
        row = f"| {metric:<25} |"
        for strat in strategies:
            val = results[strat].get(metric, "N/A")
            # Remove dict entries that aren't display values
            if isinstance(val, dict):
                val = "N/A"
            
            # Highlight the key metric
            if metric == "Active Driver Efficiency" and strat == "combinatorial":
                row += f" **{val:^13}** |"
            elif metric == "Drivers Used" and strat == "combinatorial":
                row += f" **{val:^13}** |"
            else:
                row += f" {str(val):^15} |"
        print(row)

    print("\n" + "=" * 60)
    
    # Print efficiency comparison
    if "baseline" in results and "combinatorial" in results:
        baseline_drivers = results["baseline"].get("Drivers Used", 0)
        comb_drivers = results["combinatorial"].get("Drivers Used", 0)
        
        if baseline_drivers > 0:
            drivers_saved = baseline_drivers - comb_drivers
            pct_saved = (drivers_saved / baseline_drivers) * 100
            
            print(f"\n  Combinatorial saved {drivers_saved} drivers ({pct_saved:.1f}% reduction)")
            
            baseline_eff = results["baseline"].get("Active Driver Efficiency", "0.00")
            comb_eff = results["combinatorial"].get("Active Driver Efficiency", "0.00")
            
            # Parse efficiency values
            try:
                base_val = float(str(baseline_eff).split()[0])
                comb_val = float(str(comb_eff).split()[0])
                eff_gain = ((comb_val - base_val) / base_val) * 100 if base_val > 0 else 0
                print(f"  Efficiency gain: {eff_gain:.1f}% more deliveries per driver")
            except (ValueError, AttributeError):
                pass
    
    print("=" * 60 + "\n")


def load_data_safe(dataset_name: str) -> Optional[tuple]:
    """
    Load data with graceful error handling.
    
    Args:
        dataset_name: Key from DATASETS dictionary
        
    Returns:
        Tuple of (drivers, orders) or None if error
    """
    if dataset_name not in DATASETS:
        print(f"ERROR: Unknown dataset '{dataset_name}'")
        print(f"Available datasets: {', '.join(DATASETS.keys())}")
        return None
    
    dataset = DATASETS[dataset_name]
    order_file = dataset["orders"]
    courier_file = dataset["couriers"]
    
    # Check file existence
    if not os.path.exists(order_file):
        print(f"ERROR: Order file not found: {order_file}")
        print("Please ensure the data/ directory contains the required CSV files.")
        print("Available datasets:")
        for name, info in DATASETS.items():
            if os.path.exists(info["orders"]) and os.path.exists(info["couriers"]):
                print(f"  - {name}: {info['description']}")
        return None
    
    if not os.path.exists(courier_file):
        print(f"ERROR: Courier file not found: {courier_file}")
        return None
    
    try:
        drivers, orders = Simulation.load_data(order_file, courier_file)
        print(f"Loaded {len(orders)} orders and {len(drivers)} drivers from '{dataset_name}' dataset")
        return drivers, orders
    except Exception as e:
        print(f"ERROR: Failed to load data: {e}")
        return None


def run_simulation_safe(
    drivers, 
    orders, 
    strategy: str, 
    verbose: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Run simulation with error handling.
    
    Args:
        drivers: List of Driver objects
        orders: List of Order objects
        strategy: Dispatch strategy name
        verbose: Whether to print progress
        
    Returns:
        Results dictionary or None if error
    """
    try:
        sim = Simulation(copy.deepcopy(drivers), copy.deepcopy(orders))
        results = sim.run(strategy=strategy, verbose=verbose)
        return results
    except Exception as e:
        print(f"ERROR: Simulation failed for '{strategy}': {e}")
        import traceback
        traceback.print_exc()
        return None


def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        description="Snoonu Last-Mile Delivery Simulation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Default: clean_100, all strategies
  python main.py --dataset stress                   # Run stress test
  python main.py --strategies baseline combinatorial # Compare only these
  python main.py --list-datasets                    # Show available datasets
        """
    )
    
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        default="clean_100",
        help=f"Dataset to use (default: clean_100). Options: {', '.join(DATASETS.keys())}"
    )
    
    parser.add_argument(
        "--strategies", "-s",
        nargs="+",
        default=["baseline", "combinatorial"],
        help=f"Strategies to compare. Options: {', '.join(AVAILABLE_STRATEGIES)}"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed simulation progress"
    )
    
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="List available datasets and exit"
    )
    
    parser.add_argument(
        "--all-strategies",
        action="store_true",
        help="Run all available strategies"
    )
    
    args = parser.parse_args()
    
    # List datasets mode
    if args.list_datasets:
        print("\nAvailable Datasets:")
        print("-" * 50)
        for name, info in DATASETS.items():
            exists = "OK" if (os.path.exists(info["orders"]) and os.path.exists(info["couriers"])) else "MISSING"
            print(f"  {name:15} [{exists}] - {info['description']}")
        return 0
    
    print_header()
    
    # Load data
    data = load_data_safe(args.dataset)
    if data is None:
        return 1
    
    drivers, orders = data
    
    # Determine strategies to run
    strategies = AVAILABLE_STRATEGIES if args.all_strategies else args.strategies
    
    # Validate strategies
    for strat in strategies:
        if strat not in AVAILABLE_STRATEGIES:
            print(f"ERROR: Unknown strategy '{strat}'")
            print(f"Available strategies: {', '.join(AVAILABLE_STRATEGIES)}")
            return 1
    
    print(f"\nRunning strategies: {', '.join(strategies)}")
    print("-" * 40)
    
    # Run simulations
    all_results: Dict[str, Dict[str, Any]] = {}
    
    for strategy in strategies:
        print(f"\n[{strategy.upper()}] Starting simulation...")
        results = run_simulation_safe(drivers, orders, strategy, verbose=args.verbose)
        
        if results is None:
            print(f"WARN: Skipping '{strategy}' due to error")
            continue
        
        all_results[strategy] = results
    
    if not all_results:
        print("ERROR: No simulations completed successfully")
        return 2
    
    # Print comparison table
    print_results_table(all_results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
