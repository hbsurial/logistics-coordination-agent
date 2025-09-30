"""
Data processing utilities for the Logistics Coordination Agent.

This module provides functions for cleaning, normalizing, and
transforming data from various sources.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)


def normalize_data(data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
    """
    Normalize data from external APIs to a consistent format.
    
    Args:
        data: Raw data from external API
        data_type: Type of data ('inventory', 'shipment', 'route', etc.)
        
    Returns:
        Normalized data in a consistent format
    """
    logger.debug(f"Normalizing {data_type} data")
    
    if data_type == "inventory":
        return normalize_inventory_data(data)
    elif data_type == "shipment":
        return normalize_shipment_data(data)
    elif data_type == "route":
        return normalize_route_data(data)
    else:
        logger.warning(f"Unknown data type: {data_type}, returning raw data")
        return data


def normalize_inventory_data(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Normalize inventory data from external API.
    
    Args:
        data: Raw inventory data from API
        
    Returns:
        Normalized inventory data by warehouse
    """
    normalized = {}
    
    try:
        # Handle different API response formats
        if "warehouses" in data:
            # Format: {"warehouses": [{warehouse1}, {warehouse2}, ...]}
            warehouses = data["warehouses"]
            for warehouse in warehouses:
                warehouse_id = warehouse.get("id")
                if not warehouse_id:
                    continue
                
                items = {}
                for item in warehouse.get("items", []):
                    item_id = item.get("id")
                    if not item_id:
                        continue
                    
                    items[item_id] = normalize_inventory_item(item)
                
                normalized[warehouse_id] = items
        
        elif "inventory" in data:
            # Format: {"inventory": {"warehouse1": {items}, "warehouse2": {items}, ...}}
            inventory = data["inventory"]
            for warehouse_id, warehouse_items in inventory.items():
                items = {}
                for item_id, item in warehouse_items.items():
                    items[item_id] = normalize_inventory_item(item)
                
                normalized[warehouse_id] = items
        
        else:
            # Assume direct warehouse mapping
            # Format: {"warehouse1": {items}, "warehouse2": {items}, ...}
            for warehouse_id, warehouse_items in data.items():
                items = {}
                for item_id, item in warehouse_items.items():
                    items[item_id] = normalize_inventory_item(item)
                
                normalized[warehouse_id] = items
    
    except Exception as e:
        logger.error(f"Error normalizing inventory data: {str(e)}")
    
    return normalized


def normalize_inventory_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an individual inventory item.
    
    Args:
        item: Raw inventory item data
        
    Returns:
        Normalized inventory item data
    """
    normalized = {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "category": item.get("category", ""),
        "quantity": int(item.get("quantity", 0)),
        "unit": item.get("unit", "unit"),
        "min_threshold": int(item.get("min_threshold", 0)),
        "max_threshold": int(item.get("max_threshold", 1000))
    }
    
    # Handle different date formats
    last_updated = item.get("last_updated")
    if last_updated:
        try:
            if isinstance(last_updated, str):
                normalized["last_updated"] = parse_datetime(last_updated)
            else:
                normalized["last_updated"] = last_updated
        except Exception:
            normalized["last_updated"] = datetime.now()
    
    return normalized


def normalize_shipment_data(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Normalize shipment data from external API.
    
    Args:
        data: Raw shipment data from API
        
    Returns:
        Normalized shipment data by shipment ID
    """
    normalized = {}
    
    try:
        # Handle different API response formats
        if "shipments" in data:
            # Format: {"shipments": [{shipment1}, {shipment2}, ...]}
            shipments = data["shipments"]
            for shipment in shipments:
                shipment_id = shipment.get("id")
                if not shipment_id:
                    continue
                
                normalized[shipment_id] = normalize_shipment_item(shipment)
        
        elif "active_shipments" in data:
            # Format: {"active_shipments": {"shipment1": {data}, "shipment2": {data}, ...}}
            active_shipments = data["active_shipments"]
            for shipment_id, shipment in active_shipments.items():
                normalized[shipment_id] = normalize_shipment_item(shipment)
        
        else:
            # Assume direct shipment mapping
            # Format: {"shipment1": {data}, "shipment2": {data}, ...}
            for shipment_id, shipment in data.items():
                normalized[shipment_id] = normalize_shipment_item(shipment)
    
    except Exception as e:
        logger.error(f"Error normalizing shipment data: {str(e)}")
    
    return normalized


def normalize_shipment_item(shipment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize an individual shipment.
    
    Args:
        shipment: Raw shipment data
        
    Returns:
        Normalized shipment data
    """
    normalized = {
        "id": shipment.get("id", ""),
        "origin": shipment.get("origin", ""),
        "destination": shipment.get("destination", ""),
        "status": shipment.get("status", "pending"),
        "priority": int(shipment.get("priority", 5)),
        "route": shipment.get("route", ""),
        "items": shipment.get("items", [])
    }
    
    # Handle different date formats
    estimated_arrival = shipment.get("estimated_arrival")
    if estimated_arrival:
        try:
            if isinstance(estimated_arrival, str):
                normalized["estimated_arrival"] = parse_datetime(estimated_arrival)
            else:
                normalized["estimated_arrival"] = estimated_arrival
        except Exception:
            normalized["estimated_arrival"] = None
    
    actual_arrival = shipment.get("actual_arrival")
    if actual_arrival:
        try:
            if isinstance(actual_arrival, str):
                normalized["actual_arrival"] = parse_datetime(actual_arrival)
            else:
                normalized["actual_arrival"] = actual_arrival
        except Exception:
            normalized["actual_arrival"] = None
    
    return normalized


def normalize_route_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize route condition data from external APIs.
    
    Args:
        data: Raw route condition data
        
    Returns:
        Normalized route condition data
    """
    normalized = {
        "weather": {},
        "road": {}
    }
    
    try:
        # Normalize weather conditions
        if "weather" in data:
            weather_data = data["weather"]
            
            # Handle different API response formats
            if isinstance(weather_data, dict):
                normalized["weather"] = normalize_weather_conditions(weather_data)
            elif isinstance(weather_data, list):
                # If weather data is a list of conditions along the route,
                # aggregate into a single set of conditions
                aggregated_weather = aggregate_weather_conditions(weather_data)
                normalized["weather"] = normalize_weather_conditions(aggregated_weather)
        
        # Normalize road conditions
        if "road" in data:
            road_data = data["road"]
            
            # Handle different API response formats
            if isinstance(road_data, dict):
                normalized["road"] = normalize_road_conditions(road_data)
            elif isinstance(road_data, list):
                # If road data is a list of conditions along the route,
                # aggregate into a single set of conditions
                aggregated_road = aggregate_road_conditions(road_data)
                normalized["road"] = normalize_road_conditions(aggregated_road)
    
    except Exception as e:
        logger.error(f"Error normalizing route data: {str(e)}")
    
    return normalized


def normalize_weather_conditions(weather: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize weather condition data.
    
    Args:
        weather: Raw weather condition data
        
    Returns:
        Normalized weather condition data
    """
    normalized = {
        "severe_weather": weather.get("severe_weather", False),
        "visibility_meters": int(weather.get("visibility_meters", 10000)),
        "wind_speed_kmh": float(weather.get("wind_speed_kmh", 0)),
        "precipitation_mm": float(weather.get("precipitation_mm", 0)),
        "temperature_c": float(weather.get("temperature_c", 20))
    }
    
    # Check for severe weather conditions if not explicitly provided
    if "severe_weather" not in weather:
        # Define thresholds for severe weather
        if (
            normalized["visibility_meters"] < 200 or
            normalized["wind_speed_kmh"] > 80 or
            normalized["precipitation_mm"] > 50
        ):
            normalized["severe_weather"] = True
    
    return normalized


def normalize_road_conditions(road: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize road condition data.
    
    Args:
        road: Raw road condition data
        
    Returns:
        Normalized road condition data
    """
    normalized = {
        "closed": road.get("closed", False),
        "severe_damage": road.get("severe_damage", False),
        "flooding": road.get("flooding", False),
        "construction": road.get("construction", False),
        "traffic_level": road.get("traffic_level", "normal")
    }
    
    return normalized


def aggregate_weather_conditions(conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate multiple weather conditions along a route into a single set.
    
    Args:
        conditions: List of weather conditions along the route
        
    Returns:
        Aggregated weather conditions
    """
    if not conditions:
        return {}
    
    # Initialize with default values
    aggregated = {
        "severe_weather": False,
        "visibility_meters": 10000,
        "wind_speed_kmh": 0,
        "precipitation_mm": 0,
        "temperature_c": 20
    }
    
    # Aggregate conditions (take worst case for each metric)
    for condition in conditions:
        # For severe weather, any severe condition makes the whole route severe
        if condition.get("severe_weather", False):
            aggregated["severe_weather"] = True
        
        # For visibility, take the minimum
        visibility = condition.get("visibility_meters")
        if visibility is not None and visibility < aggregated["visibility_meters"]:
            aggregated["visibility_meters"] = visibility
        
        # For wind speed, take the maximum
        wind_speed = condition.get("wind_speed_kmh")
        if wind_speed is not None and wind_speed > aggregated["wind_speed_kmh"]:
            aggregated["wind_speed_kmh"] = wind_speed
        
        # For precipitation, take the maximum
        precipitation = condition.get("precipitation_mm")
        if precipitation is not None and precipitation > aggregated["precipitation_mm"]:
            aggregated["precipitation_mm"] = precipitation
    
    # Calculate average temperature
    if len(conditions) > 0:
        temp_sum = sum(
            c.get("temperature_c", 20) for c in conditions if "temperature_c" in c
        )
        temp_count = sum(1 for c in conditions if "temperature_c" in c)
        if temp_count > 0:
            aggregated["temperature_c"] = temp_sum / temp_count
    
    return aggregated


def aggregate_road_conditions(conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate multiple road conditions along a route into a single set.
    
    Args:
        conditions: List of road conditions along the route
        
    Returns:
        Aggregated road conditions
    """
    if not conditions:
        return {}
    
    # Initialize with default values
    aggregated = {
        "closed": False,
        "severe_damage": False,
        "flooding": False,
        "construction": False,
        "traffic_level": "normal"
    }
    
    # Traffic level mapping for aggregation
    traffic_levels = {
        "light": 1,
        "normal": 2,
        "heavy": 3,
        "severe": 4
    }
    
    max_traffic_level = 1  # Default to "light"
    
    # Aggregate conditions (any critical condition affects the whole route)
    for condition in conditions:
        # For boolean conditions, any true makes the whole route affected
        if condition.get("closed", False):
            aggregated["closed"] = True
        
        if condition.get("severe_damage", False):
            aggregated["severe_damage"] = True
        
        if condition.get("flooding", False):
            aggregated["flooding"] = True
        
        if condition.get("construction", False):
            aggregated["construction"] = True
        
        # For traffic level, take the worst case
        traffic_level = condition.get("traffic_level", "normal")
        traffic_value = traffic_levels.get(traffic_level, 2)  # Default to "normal"
        if traffic_value > max_traffic_level:
            max_traffic_level = traffic_value
    
    # Convert max traffic level back to string
    for level_name, level_value in traffic_levels.items():
        if level_value == max_traffic_level:
            aggregated["traffic_level"] = level_name
            break
    
    return aggregated


def parse_datetime(datetime_str: str) -> datetime:
    """
    Parse a datetime string in various formats.
    
    Args:
        datetime_str: Datetime string to parse
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If the datetime string cannot be parsed
    """
    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",  # ISO format with microseconds and Z
        "%Y-%m-%dT%H:%M:%SZ",     # ISO format with Z
        "%Y-%m-%dT%H:%M:%S.%f",   # ISO format with microseconds
        "%Y-%m-%dT%H:%M:%S",      # ISO format
        "%Y-%m-%d %H:%M:%S.%f",   # SQL format with microseconds
        "%Y-%m-%d %H:%M:%S",      # SQL format
        "%Y-%m-%d %H:%M",         # Date and time without seconds
        "%Y-%m-%d",               # Date only
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    # If all formats fail, raise an error
    raise ValueError(f"Could not parse datetime string: {datetime_str}")


def clean_text(text: str) -> str:
    """
    Clean and normalize text data.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    cleaned = " ".join(text.split())
    
    # Convert to lowercase
    cleaned = cleaned.lower()
    
    return cleaned


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate geographic coordinates.
    
    Args:
        lat: Latitude value
        lon: Longitude value
        
    Returns:
        True if coordinates are valid, False otherwise
    """
    try:
        lat_float = float(lat)
        lon_float = float(lon)
        
        return -90 <= lat_float <= 90 and -180 <= lon_float <= 180
    except (ValueError, TypeError):
        return False
