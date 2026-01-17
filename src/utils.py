# snoonu-smart-dispatch/src/utils.py
"""
Utility functions for the Snoonu Last-Mile Delivery Simulation.

Provides geographic calculations and time manipulation utilities.
Includes OSRM integration for real road distance calculations.
"""

from __future__ import annotations

import math
import logging
from datetime import time, timedelta, datetime
from functools import lru_cache
from typing import Union, Tuple, Optional
import requests

from . import config

# Configure logging
logger = logging.getLogger(__name__)

# Module-level cache for OSRM results (separate from lru_cache for more control)
_osrm_cache: dict[Tuple[float, float, float, float], Tuple[float, float]] = {}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula to compute the distance between two GPS coordinates.
    This accounts for Earth's curvature, making it accurate for last-mile distances.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees
        lon1: Longitude of point 1 in decimal degrees
        lat2: Latitude of point 2 in decimal degrees
        lon2: Longitude of point 2 in decimal degrees
        
    Returns:
        Distance in kilometers between the two points
        
    Example:
        >>> haversine_distance(25.2854, 51.5310, 25.2900, 51.5350)
        0.623  # ~623 meters
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    return c * r


def _get_cache_key(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float, float, float]:
    """Create a cache key with rounded coordinates (5 decimal places ≈ 1m precision)."""
    return (round(lat1, 5), round(lon1, 5), round(lat2, 5), round(lon2, 5))


def osrm_route(
    lat1: float, lon1: float, 
    lat2: float, lon2: float
) -> Optional[Tuple[float, float]]:
    """
    Get road distance and duration from OSRM routing service.
    
    Queries the OSRM API for the actual driving route between two points.
    Results are cached to minimize API calls.
    
    Args:
        lat1: Latitude of origin in decimal degrees
        lon1: Longitude of origin in decimal degrees
        lat2: Latitude of destination in decimal degrees
        lon2: Longitude of destination in decimal degrees
        
    Returns:
        Tuple of (distance_km, duration_minutes) if successful, None if failed
        
    Note:
        OSRM expects coordinates in lon,lat order (not lat,lon).
    """
    # Check cache first
    cache_key = _get_cache_key(lat1, lon1, lat2, lon2)
    if cache_key in _osrm_cache:
        return _osrm_cache[cache_key]
    
    # Also check reverse direction (roads are often bidirectional with same distance)
    reverse_key = _get_cache_key(lat2, lon2, lat1, lon1)
    if reverse_key in _osrm_cache:
        return _osrm_cache[reverse_key]
    
    try:
        # OSRM expects lon,lat order
        url = (
            f"{config.OSRM_SERVER_URL}/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?overview=false"  # Don't need the geometry, saves bandwidth
        )
        
        response = requests.get(url, timeout=config.OSRM_TIMEOUT_SECONDS)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning(f"OSRM returned no route: {data.get('code')}")
            return None
        
        route = data["routes"][0]
        distance_km = route["distance"] / 1000  # Convert meters to km
        duration_min = route["duration"] / 60   # Convert seconds to minutes
        
        result = (distance_km, duration_min)
        
        # Cache the result (enforce cache size limit)
        if len(_osrm_cache) >= config.OSRM_CACHE_SIZE:
            # Remove oldest entries (first 10% of cache)
            keys_to_remove = list(_osrm_cache.keys())[:config.OSRM_CACHE_SIZE // 10]
            for key in keys_to_remove:
                del _osrm_cache[key]
        
        _osrm_cache[cache_key] = result
        return result
        
    except requests.exceptions.Timeout:
        logger.warning("OSRM request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"OSRM request failed: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"OSRM response parsing failed: {e}")
        return None


def get_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Get the distance between two points using the configured method.
    
    This is the main distance function that should be used throughout the codebase.
    It automatically uses OSRM road distance when enabled, with fallback to
    Haversine distance (with a multiplier) when OSRM is disabled or fails.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees
        lon1: Longitude of point 1 in decimal degrees
        lat2: Latitude of point 2 in decimal degrees
        lon2: Longitude of point 2 in decimal degrees
        
    Returns:
        Distance in kilometers between the two points
    """
    if config.USE_ROAD_DISTANCE:
        result = osrm_route(lat1, lon1, lat2, lon2)
        if result is not None:
            return result[0]  # Return distance_km
        
        # Fallback to Haversine with multiplier
        logger.debug("Falling back to Haversine distance with multiplier")
        return haversine_distance(lat1, lon1, lat2, lon2) * config.HAVERSINE_FALLBACK_MULTIPLIER
    
    return haversine_distance(lat1, lon1, lat2, lon2)


def get_travel_time(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Get the travel time between two points using the configured method.
    
    When OSRM is enabled, returns the actual road travel time which accounts
    for road types (highway vs. residential) and typical speeds.
    When disabled, uses distance-based estimation with average speed.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees
        lon1: Longitude of point 1 in decimal degrees
        lat2: Latitude of point 2 in decimal degrees
        lon2: Longitude of point 2 in decimal degrees
        
    Returns:
        Estimated travel time in minutes
    """
    if config.USE_ROAD_DISTANCE:
        result = osrm_route(lat1, lon1, lat2, lon2)
        if result is not None:
            return result[1]  # Return duration_min
        
        # Fallback: calculate from Haversine distance with multiplier
        distance = haversine_distance(lat1, lon1, lat2, lon2) * config.HAVERSINE_FALLBACK_MULTIPLIER
        return calculate_travel_time_minutes(distance)
    
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    return calculate_travel_time_minutes(distance)


def clear_osrm_cache() -> int:
    """
    Clear the OSRM route cache.
    
    Returns:
        Number of cached entries that were cleared
    """
    global _osrm_cache
    count = len(_osrm_cache)
    _osrm_cache = {}
    return count


def get_osrm_cache_stats() -> dict:
    """
    Get statistics about the OSRM cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return {
        "size": len(_osrm_cache),
        "max_size": config.OSRM_CACHE_SIZE,
        "utilization": len(_osrm_cache) / config.OSRM_CACHE_SIZE if config.OSRM_CACHE_SIZE > 0 else 0
    }


def osrm_table(
    locations: list[Tuple[float, float]],
    max_locations: int = 100
) -> Optional[Tuple[list[list[float]], list[list[float]]]]:
    """
    Get distance and duration matrix for multiple locations using OSRM Table API.
    
    This is MUCH more efficient than individual route calls - gets all pairwise
    distances in a single API request instead of O(N^2) individual calls.
    
    Args:
        locations: List of (lat, lng) tuples
        max_locations: Maximum locations per request (public OSRM limit is ~100)
        
    Returns:
        Tuple of (distances_matrix, durations_matrix) where each is a 2D list.
        distances[i][j] = distance in km from location i to j
        durations[i][j] = duration in minutes from location i to j
        Returns None if the API call fails.
    """
    if len(locations) < 2:
        return None
    
    # If too many locations, we can't use table API efficiently
    if len(locations) > max_locations:
        logger.warning(f"Too many locations ({len(locations)}) for OSRM table API (max {max_locations})")
        return None
    
    try:
        # Build coordinates string (OSRM expects lon,lat order)
        coords = ";".join(f"{lng},{lat}" for lat, lng in locations)
        
        url = (
            f"{config.OSRM_SERVER_URL}/table/v1/driving/{coords}"
            f"?annotations=distance,duration"
        )
        
        response = requests.get(url, timeout=config.OSRM_TIMEOUT_SECONDS * 3)  # Longer timeout for table
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("code") != "Ok":
            logger.warning(f"OSRM table returned error: {data.get('code')}")
            return None
        
        # Convert distances from meters to km
        distances = [
            [d / 1000 if d is not None else float('inf') for d in row]
            for row in data["distances"]
        ]
        
        # Convert durations from seconds to minutes
        durations = [
            [d / 60 if d is not None else float('inf') for d in row]
            for row in data["durations"]
        ]
        
        return distances, durations
        
    except requests.exceptions.Timeout:
        logger.warning("OSRM table request timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"OSRM table request failed: {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.warning(f"OSRM table response parsing failed: {e}")
        return None


def precompute_distances(
    locations: list[Tuple[float, float]],
    chunk_size: int = 100
) -> dict[Tuple[Tuple[float, float], Tuple[float, float]], Tuple[float, float]]:
    """
    Precompute all pairwise distances for a set of locations.
    
    Uses OSRM Table API for efficiency when possible. For larger datasets,
    falls back to Haversine with a realistic multiplier.
    
    Args:
        locations: List of (lat, lng) tuples
        chunk_size: Maximum locations per OSRM table request
        
    Returns:
        Dictionary mapping (loc1, loc2) -> (distance_km, duration_min)
    """
    result = {}
    
    if len(locations) < 2:
        return result
    
    # For datasets larger than chunk_size, use Haversine with multiplier
    # This is a practical tradeoff for hackathon performance
    if not config.USE_ROAD_DISTANCE or len(locations) > chunk_size:
        multiplier = config.HAVERSINE_FALLBACK_MULTIPLIER if config.USE_ROAD_DISTANCE else 1.0
        
        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i != j:
                    dist = haversine_distance(loc1[0], loc1[1], loc2[0], loc2[1]) * multiplier
                    time_mins = calculate_travel_time_minutes(dist)
                    result[(loc1, loc2)] = (dist, time_mins)
                    
                    # Cache for individual lookups
                    cache_key = _get_cache_key(loc1[0], loc1[1], loc2[0], loc2[1])
                    _osrm_cache[cache_key] = (dist, time_mins)
        return result
    
    # Try OSRM table API for smaller datasets
    table_result = osrm_table(locations)
    
    if table_result is not None:
        distances, durations = table_result
        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i != j:
                    dist = distances[i][j]
                    dur = durations[i][j]
                    result[(loc1, loc2)] = (dist, dur)
                    
                    # Also populate the cache for individual lookups
                    cache_key = _get_cache_key(loc1[0], loc1[1], loc2[0], loc2[1])
                    _osrm_cache[cache_key] = (dist, dur)
    else:
        # Fall back to Haversine with multiplier
        logger.info("OSRM table failed, using Haversine with multiplier")
        for i, loc1 in enumerate(locations):
            for j, loc2 in enumerate(locations):
                if i != j:
                    dist = haversine_distance(loc1[0], loc1[1], loc2[0], loc2[1]) * config.HAVERSINE_FALLBACK_MULTIPLIER
                    time_mins = calculate_travel_time_minutes(dist)
                    result[(loc1, loc2)] = (dist, time_mins)
                    
                    cache_key = _get_cache_key(loc1[0], loc1[1], loc2[0], loc2[1])
                    _osrm_cache[cache_key] = (dist, time_mins)
    
    return result


def calculate_travel_time_minutes(distance_km: float) -> float:
    """
    Calculate estimated travel time for a given distance.
    
    Uses the average speed from config to estimate travel duration.
    
    Args:
        distance_km: Distance in kilometers
        
    Returns:
        Estimated travel time in minutes
        
    Example:
        >>> calculate_travel_time_minutes(5.0)  # 5km at 35km/h
        8.57  # ~8.5 minutes
    """
    if config.AVG_SPEED_KMH <= 0:
        return float('inf')
    return (distance_km / config.AVG_SPEED_KMH) * 60


def add_minutes_to_time(base_time: time, minutes_to_add: Union[int, float]) -> time:
    """
    Add a number of minutes to a datetime.time object.
    
    Note: This is designed for single-day simulations. Times past midnight
    will wrap around, which may cause unexpected behavior in multi-day scenarios.
    
    Args:
        base_time: The starting time
        minutes_to_add: Number of minutes to add (can be negative)
        
    Returns:
        A new time object with the minutes added
        
    Example:
        >>> add_minutes_to_time(time(18, 30), 45)
        datetime.time(19, 15)
    """
    # Use a dummy date to leverage timedelta arithmetic
    dummy_date = datetime.now().date()
    base_datetime = datetime.combine(dummy_date, base_time)
    result_datetime = base_datetime + timedelta(minutes=minutes_to_add)
    return result_datetime.time()


def format_time_duration(minutes: float) -> str:
    """
    Format a duration in minutes as a human-readable string.
    
    Args:
        minutes: Duration in minutes
        
    Returns:
        Formatted string like "1h 23m" or "45m"
    """
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m"


def time_to_minutes(t: time) -> int:
    """
    Convert a time object to minutes since midnight.
    
    Args:
        t: A datetime.time object
        
    Returns:
        Total minutes since midnight
        
    Example:
        >>> time_to_minutes(time(14, 30))
        870  # 14*60 + 30
    """
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """
    Convert minutes since midnight to a time object.
    
    Args:
        minutes: Minutes since midnight
        
    Returns:
        A datetime.time object
        
    Example:
        >>> minutes_to_time(870)
        datetime.time(14, 30)
    """
    hours = (minutes // 60) % 24
    mins = minutes % 60
    return time(hours, mins)
