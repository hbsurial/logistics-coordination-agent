"""
Inventory model for the Logistics Coordination Agent.

This module defines the data structures for representing inventory items
and warehouses in the logistics system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class InventoryItem:
    """
    Represents an inventory item in a warehouse.
    
    Attributes:
        id: Unique identifier for the item
        name: Human-readable name of the item
        category: Category of the item
        quantity: Current quantity in stock
        unit: Unit of measurement (e.g., "kg", "liters", "units")
        min_threshold: Minimum threshold for reordering
        max_threshold: Maximum capacity or target level
        last_updated: Timestamp of the last update
    """
    
    id: str
    name: str
    category: str
    quantity: int
    unit: str
    min_threshold: int
    max_threshold: int
    last_updated: Optional[datetime] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_below_threshold(self) -> bool:
        """
        Check if the item quantity is below the minimum threshold.
        
        Returns:
            True if below threshold, False otherwise
        """
        return self.quantity < self.min_threshold
    
    def is_above_threshold(self) -> bool:
        """
        Check if the item quantity is above the maximum threshold.
        
        Returns:
            True if above threshold, False otherwise
        """
        return self.quantity > self.max_threshold
    
    def get_threshold_percentage(self) -> float:
        """
        Get the current quantity as a percentage of the threshold range.
        
        Returns:
            Percentage between min and max thresholds (0-100%)
        """
        threshold_range = self.max_threshold - self.min_threshold
        
        if threshold_range <= 0:
            return 100.0 if self.quantity >= self.min_threshold else 0.0
        
        percentage = ((self.quantity - self.min_threshold) / threshold_range) * 100
        return max(0.0, min(100.0, percentage))
    
    def get_days_supply(self, daily_usage: float) -> Optional[float]:
        """
        Calculate the number of days the current quantity will last.
        
        Args:
            daily_usage: Average daily usage of the item
            
        Returns:
            Number of days the current quantity will last, or None if daily_usage is 0
        """
        if daily_usage <= 0:
            return None
        
        return self.quantity / daily_usage
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the inventory item to a dictionary representation.
        
        Returns:
            Dictionary representation of the inventory item
        """
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "quantity": self.quantity,
            "unit": self.unit,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InventoryItem':
        """
        Create an inventory item from a dictionary representation.
        
        Args:
            data: Dictionary representation of the inventory item
            
        Returns:
            InventoryItem object
        """
        # Parse datetime string
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            quantity=data["quantity"],
            unit=data["unit"],
            min_threshold=data.get("min_threshold", 0),
            max_threshold=data.get("max_threshold", 1000),
            last_updated=last_updated,
            metadata=data.get("metadata", {})
        )


@dataclass
class Warehouse:
    """
    Represents a warehouse in the logistics system.
    
    Attributes:
        id: Unique identifier for the warehouse
        name: Human-readable name of the warehouse
        location: Location identifier or coordinates
        capacity: Total capacity of the warehouse
        items: Dictionary of inventory items in the warehouse
    """
    
    id: str
    name: str
    location: str
    capacity: int
    items: Dict[str, InventoryItem]
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_total_quantity(self) -> int:
        """
        Get the total quantity of all items in the warehouse.
        
        Returns:
            Total quantity of all items
        """
        return sum(item.quantity for item in self.items.values())
    
    def get_capacity_utilization(self) -> float:
        """
        Get the current capacity utilization as a percentage.
        
        Returns:
            Percentage of capacity utilized (0-100%)
        """
        if self.capacity <= 0:
            return 100.0
        
        utilization = (self.get_total_quantity() / self.capacity) * 100
        return max(0.0, min(100.0, utilization))
    
    def get_items_below_threshold(self) -> Dict[str, InventoryItem]:
        """
        Get all items that are below their minimum threshold.
        
        Returns:
            Dictionary of items below threshold
        """
        return {
            item_id: item
            for item_id, item in self.items.items()
            if item.is_below_threshold()
        }
    
    def get_items_above_threshold(self) -> Dict[str, InventoryItem]:
        """
        Get all items that are above their maximum threshold.
        
        Returns:
            Dictionary of items above threshold
        """
        return {
            item_id: item
            for item_id, item in self.items.items()
            if item.is_above_threshold()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the warehouse to a dictionary representation.
        
        Returns:
            Dictionary representation of the warehouse
        """
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "capacity": self.capacity,
            "items": {item_id: item.to_dict() for item_id, item in self.items.items()},
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Warehouse':
        """
        Create a warehouse from a dictionary representation.
        
        Args:
            data: Dictionary representation of the warehouse
            
        Returns:
            Warehouse object
        """
        # Convert item dictionaries to InventoryItem objects
        items = {}
        for item_id, item_data in data.get("items", {}).items():
            items[item_id] = InventoryItem.from_dict(item_data)
        
        return cls(
            id=data["id"],
            name=data["name"],
            location=data["location"],
            capacity=data["capacity"],
            items=items,
            metadata=data.get("metadata", {})
        )
