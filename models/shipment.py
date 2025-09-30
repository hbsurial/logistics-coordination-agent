"""
Shipment model for the Logistics Coordination Agent.

This module defines the data structures for representing shipments
and their status in the logistics system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class ShipmentStatus(Enum):
    """Enumeration of possible shipment statuses."""
    
    PENDING = "pending"
    PREPARING = "preparing"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    REROUTING = "rerouting"
    ON_HOLD = "on_hold"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class Shipment:
    """
    Represents a shipment of items between warehouses.
    
    Attributes:
        id: Unique identifier for the shipment
        origin: ID of the origin warehouse
        destination: ID of the destination warehouse
        items: List of items in the shipment
        status: Current status of the shipment
        priority: Priority level (1-10, with 10 being highest)
        route: ID of the assigned route
        estimated_arrival: Estimated arrival time
        actual_arrival: Actual arrival time (if delivered)
        last_updated: Timestamp of the last update
    """
    
    id: str
    origin: str
    destination: str
    items: List[Dict[str, Any]]
    status: ShipmentStatus
    priority: int
    route: str
    estimated_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """
        Check if the shipment is currently active.
        
        Returns:
            True if the shipment is active, False otherwise
        """
        return self.status not in [ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED]
    
    def is_delayed(self) -> bool:
        """
        Check if the shipment is currently delayed.
        
        Returns:
            True if the shipment is delayed, False otherwise
        """
        if not self.estimated_arrival:
            return False
        
        return (
            self.status == ShipmentStatus.DELAYED
            or (datetime.now() > self.estimated_arrival and self.status == ShipmentStatus.IN_TRANSIT)
        )
    
    def get_delay_minutes(self) -> Optional[float]:
        """
        Get the current delay in minutes.
        
        Returns:
            Delay in minutes if delayed, None otherwise
        """
        if not self.is_delayed() or not self.estimated_arrival:
            return None
        
        delay = datetime.now() - self.estimated_arrival
        return delay.total_seconds() / 60
    
    def get_total_quantity(self) -> int:
        """
        Get the total quantity of items in the shipment.
        
        Returns:
            Total quantity of items
        """
        return sum(item.get("quantity", 0) for item in self.items)
    
    def get_item_quantity(self, item_id: str) -> int:
        """
        Get the quantity of a specific item in the shipment.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Quantity of the item, or 0 if not found
        """
        for item in self.items:
            if item.get("id") == item_id:
                return item.get("quantity", 0)
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the shipment to a dictionary representation.
        
        Returns:
            Dictionary representation of the shipment
        """
        return {
            "id": self.id,
            "origin": self.origin,
            "destination": self.destination,
            "items": self.items,
            "status": self.status.value,
            "priority": self.priority,
            "route": self.route,
            "estimated_arrival": self.estimated_arrival.isoformat() if self.estimated_arrival else None,
            "actual_arrival": self.actual_arrival.isoformat() if self.actual_arrival else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Shipment':
        """
        Create a shipment from a dictionary representation.
        
        Args:
            data: Dictionary representation of the shipment
            
        Returns:
            Shipment object
        """
        # Convert string status to enum
        status_str = data.get("status", "pending")
        status = ShipmentStatus(status_str)
        
        # Parse datetime strings
        estimated_arrival = None
        if data.get("estimated_arrival"):
            estimated_arrival = datetime.fromisoformat(data["estimated_arrival"])
        
        actual_arrival = None
        if data.get("actual_arrival"):
            actual_arrival = datetime.fromisoformat(data["actual_arrival"])
        
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return cls(
            id=data["id"],
            origin=data["origin"],
            destination=data["destination"],
            items=data["items"],
            status=status,
            priority=data.get("priority", 5),
            route=data["route"],
            estimated_arrival=estimated_arrival,
            actual_arrival=actual_arrival,
            last_updated=last_updated,
            metadata=data.get("metadata", {})
        )
