"""
Route model for the Logistics Coordination Agent.

This module defines the data structures for representing routes
and their conditions in the logistics system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List


@dataclass
class RouteStatus:
    """
    Represents the current status and conditions of a route.
    
    Attributes:
        route_id: Unique identifier for the route
        weather_conditions: Dictionary of weather conditions along the route
        road_conditions: Dictionary of road conditions along the route
        is_disrupted: Flag indicating if the route is currently disrupted
        last_updated: Timestamp of the last update
    """
    
    route_id: str
    weather_conditions: Dict[str, Any]
    road_conditions: Dict[str, Any]
    is_disrupted: bool
    last_updated: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_disruption_reason(self) -> Optional[str]:
        """
        Get the reason for route disruption, if any.
        
        Returns:
            Reason for disruption, or None if not disrupted
        """
        if not self.is_disrupted:
            return None
        
        # Check weather conditions
        weather = self.weather_conditions
        if weather.get("severe_weather", False):
            return "severe_weather"
        
        if weather.get("visibility_meters", 10000) < 200:
            return "low_visibility"
            
        if weather.get("wind_speed_kmh", 0) > 80:
            return "high_winds"
        
        # Check road conditions
        road = self.road_conditions
        if road.get("closed", False):
            return "road_closed"
            
        if road.get("severe_damage", False):
            return "road_damage"
            
        if road.get("flooding", False):
            return "flooding"
        
        # Default reason if specific cause not identified
        return "unknown_disruption"
    
    def get_estimated_delay(self) -> Optional[int]:
        """
        Get the estimated delay in minutes due to current conditions.
        
        Returns:
            Estimated delay in minutes, or None if not available
        """
        if not self.is_disrupted:
            return 0
        
        # This is a simplified implementation
        # In a real system, this would use more sophisticated models
        
        # Default delays based on disruption type
        delay_by_reason = {
            "severe_weather": 120,  # 2 hours
            "low_visibility": 90,   # 1.5 hours
            "high_winds": 60,       # 1 hour
            "road_closed": 240,     # 4 hours
            "road_damage": 180,     # 3 hours
            "flooding": 210,        # 3.5 hours
            "unknown_disruption": 120  # 2 hours
        }
        
        reason = self.get_disruption_reason()
        if reason:
            return delay_by_reason.get(reason, 60)
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the route status to a dictionary representation.
        
        Returns:
            Dictionary representation of the route status
        """
        return {
            "route_id": self.route_id,
            "weather_conditions": self.weather_conditions,
            "road_conditions": self.road_conditions,
            "is_disrupted": self.is_disrupted,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteStatus':
        """
        Create a route status from a dictionary representation.
        
        Args:
            data: Dictionary representation of the route status
            
        Returns:
            RouteStatus object
        """
        # Parse datetime string
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return cls(
            route_id=data["route_id"],
            weather_conditions=data.get("weather_conditions", {}),
            road_conditions=data.get("road_conditions", {}),
            is_disrupted=data.get("is_disrupted", False),
            last_updated=last_updated,
            metadata=data.get("metadata", {})
        )


@dataclass
class Route:
    """
    Represents a transportation route between locations.
    
    Attributes:
        id: Unique identifier for the route
        origin: Origin location ID
        destination: Destination location ID
        distance_km: Distance in kilometers
        estimated_duration_hours: Estimated travel duration in hours
        waypoints: List of waypoints along the route
        current_status: Current status of the route
    """
    
    id: str
    origin: str
    destination: str
    distance_km: float
    estimated_duration_hours: float
    waypoints: List[Dict[str, Any]]
    current_status: Optional[RouteStatus] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """
        Check if the route is currently available for use.
        
        Returns:
            True if the route is available, False otherwise
        """
        if not self.current_status:
            return True
        
        return not self.current_status.is_disrupted
    
    def get_adjusted_duration(self) -> float:
        """
        Get the adjusted travel duration based on current conditions.
        
        Returns:
            Adjusted travel duration in hours
        """
        if not self.current_status:
            return self.estimated_duration_hours
        
        # If route is disrupted, add estimated delay
        if self.current_status.is_disrupted:
            delay_minutes = self.current_status.get_estimated_delay() or 0
            return self.estimated_duration_hours + (delay_minutes / 60)
        
        return self.estimated_duration_hours
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the route to a dictionary representation.
        
        Returns:
            Dictionary representation of the route
        """
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "distance_km": self.distance_km,
            "estimated_duration_hours": self.estimated_duration_hours,
            "waypoints": self.waypoints,
            "current_status": self.current_status.to_dict() if self.current_status else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Route':
        """
        Create a route from a dictionary representation.
        
        Args:
            data: Dictionary representation of the route
            
        Returns:
            Route object
        """
        # Parse current status if available
        current_status = None
        if data.get("current_status"):
            current_status = RouteStatus.from_dict(data["current_status"])
        
        return cls(
            id=data["id"],
            origin=data["origin"],
            destination=data["destination"],
            distance_km=data["distance_km"],
            estimated_duration_hours=data["estimated_duration_hours"],
            waypoints=data.get("waypoints", []),
            current_status=current_status,
            metadata=data.get("metadata", {})
        )
