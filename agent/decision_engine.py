"""
Decision Engine for the Logistics Coordination Agent.

This module contains the decision-making logic for logistics optimization,
including inventory management, route planning, and disruption response.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

from agent.config import AgentConfig
from models.inventory import Warehouse
from models.route import RouteStatus
from models.shipment import Shipment, ShipmentStatus

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Decision engine for making logistics optimization decisions.
    
    This class implements the core decision-making algorithms for the logistics agent,
    evaluating different scenarios and recommending actions.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Decision Engine.
        
        Args:
            config: Configuration settings for the agent
        """
        self.config = config
        logger.info("Decision Engine initialized")

    def evaluate_inventory_replenishment(
        self, warehouses: Dict[str, Warehouse], alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate inventory alerts and make replenishment decisions.
        
        Args:
            warehouses: Dictionary of warehouse objects
            alerts: List of inventory alerts
            
        Returns:
            List of replenishment decisions
        """
        logger.info(f"Evaluating inventory replenishment for {len(alerts)} alerts")
        
        replenishment_decisions = []
        
        for alert in alerts:
            warehouse_id = alert["warehouse_id"]
            item_id = alert["item_id"]
            current_quantity = alert["current_quantity"]
            min_threshold = alert["min_threshold"]
            
            # Find potential source warehouses with excess inventory
            potential_sources = self._find_inventory_sources(warehouses, item_id, warehouse_id)
            
            if potential_sources:
                # Choose the best source warehouse
                best_source = self._select_best_inventory_source(potential_sources, warehouse_id)
                
                # Calculate transfer quantity
                target_quantity = min_threshold * 1.5  # Replenish to 150% of minimum threshold
                transfer_quantity = target_quantity - current_quantity
                
                # Adjust transfer quantity based on available excess at source
                available_excess = potential_sources[best_source]["excess_quantity"]
                if transfer_quantity > available_excess:
                    transfer_quantity = available_excess
                
                # Create replenishment decision
                decision = {
                    "type": "inventory_transfer",
                    "source_warehouse": best_source,
                    "destination_warehouse": warehouse_id,
                    "items": [
                        {
                            "id": item_id,
                            "name": alert["item_name"],
                            "quantity": transfer_quantity,
                            "unit": alert["unit"]
                        }
                    ],
                    "reason": "inventory_below_threshold",
                    "priority": 8 if alert["severity"] == "high" else 5
                }
                
                replenishment_decisions.append(decision)
                logger.info(
                    f"Decided to transfer {transfer_quantity} units of {item_id} "
                    f"from {best_source} to {warehouse_id}"
                )
            else:
                # No source warehouse found, need to order from external supplier
                logger.info(
                    f"No source warehouse found for {item_id}, "
                    f"need to order from external supplier"
                )
                
                # This would typically trigger an external procurement process
                # which is outside the scope of this agent
        
        return replenishment_decisions

    def _find_inventory_sources(
        self, warehouses: Dict[str, Warehouse], item_id: str, destination_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Find warehouses that have excess inventory of a specific item.
        
        Args:
            warehouses: Dictionary of warehouse objects
            item_id: ID of the item to find
            destination_id: ID of the destination warehouse (to exclude)
            
        Returns:
            Dictionary of potential source warehouses with excess inventory
        """
        potential_sources = {}
        
        for warehouse_id, warehouse in warehouses.items():
            # Skip the destination warehouse
            if warehouse_id == destination_id:
                continue
                
            # Check if warehouse has the item
            if item_id in warehouse.items:
                item = warehouse.items[item_id]
                
                # Calculate excess inventory (above the minimum threshold)
                excess_quantity = item.quantity - item.min_threshold
                
                # Only consider warehouses with excess inventory
                if excess_quantity > 0:
                    potential_sources[warehouse_id] = {
                        "warehouse": warehouse,
                        "excess_quantity": excess_quantity,
                        "distance_to_destination": self._calculate_distance(warehouse_id, destination_id)
                    }
        
        return potential_sources

    def _select_best_inventory_source(
        self, potential_sources: Dict[str, Dict[str, Any]], destination_id: str
    ) -> str:
        """
        Select the best source warehouse for inventory transfer.
        
        Args:
            potential_sources: Dictionary of potential source warehouses
            destination_id: ID of the destination warehouse
            
        Returns:
            ID of the best source warehouse
        """
        # Sort potential sources by a combination of distance and excess quantity
        sorted_sources = sorted(
            potential_sources.items(),
            key=lambda x: (
                x[1]["distance_to_destination"],  # Prioritize closer warehouses
                -x[1]["excess_quantity"]  # Then prioritize warehouses with more excess
            )
        )
        
        # Return the ID of the best source
        return sorted_sources[0][0] if sorted_sources else None

    def _calculate_distance(self, origin_id: str, destination_id: str) -> float:
        """
        Calculate the distance between two warehouses.
        
        In a real implementation, this would use geospatial calculations
        or routing APIs to determine actual distances.
        
        Args:
            origin_id: ID of the origin warehouse
            destination_id: ID of the destination warehouse
            
        Returns:
            Distance between warehouses (in km)
        """
        # This is a placeholder implementation
        # In a real system, this would use actual coordinates and routing algorithms
        
        # For demonstration purposes, we'll use a simple lookup table
        distance_matrix = {
            ("warehouse_1", "warehouse_2"): 150.0,
            ("warehouse_1", "warehouse_3"): 320.0,
            ("warehouse_1", "warehouse_4"): 450.0,
            ("warehouse_2", "warehouse_1"): 150.0,
            ("warehouse_2", "warehouse_3"): 180.0,
            ("warehouse_2", "warehouse_4"): 300.0,
            ("warehouse_3", "warehouse_1"): 320.0,
            ("warehouse_3", "warehouse_2"): 180.0,
            ("warehouse_3", "warehouse_4"): 200.0,
            ("warehouse_4", "warehouse_1"): 450.0,
            ("warehouse_4", "warehouse_2"): 300.0,
            ("warehouse_4", "warehouse_3"): 200.0,
        }
        
        # Try to find the distance in our lookup table
        key = (origin_id, destination_id)
        if key in distance_matrix:
            return distance_matrix[key]
        
        # Default to a large distance if not found
        return 1000.0

    def evaluate_shipment_rerouting(
        self,
        active_shipments: Dict[str, Shipment],
        issues: List[Dict[str, Any]],
        route_conditions: Dict[str, RouteStatus]
    ) -> List[Dict[str, Any]]:
        """
        Evaluate shipment issues and make rerouting decisions.
        
        Args:
            active_shipments: Dictionary of active shipment objects
            issues: List of shipment issues
            route_conditions: Dictionary of route condition objects
            
        Returns:
            List of rerouting decisions
        """
        logger.info(f"Evaluating shipment rerouting for {len(issues)} issues")
        
        rerouting_decisions = []
        
        for issue in issues:
            shipment_id = issue["shipment_id"]
            
            # Skip if shipment is not in active shipments
            if shipment_id not in active_shipments:
                continue
                
            shipment = active_shipments[shipment_id]
            current_route = shipment.route
            
            # Check if current route is disrupted
            is_disrupted = False
            if current_route in route_conditions:
                is_disrupted = route_conditions[current_route].is_disrupted
            
            # Determine if rerouting is needed
            needs_rerouting = False
            reason = ""
            
            if is_disrupted:
                needs_rerouting = True
                reason = "route_disruption"
            elif issue["delay_minutes"] > self.config.reroute_delay_threshold_minutes:
                needs_rerouting = True
                reason = "significant_delay"
            
            if needs_rerouting:
                # Find alternative routes
                alternative_routes = self._find_alternative_routes(
                    shipment.origin, shipment.destination, current_route
                )
                
                if alternative_routes:
                    # Select the best alternative route
                    new_route, new_eta = self._select_best_route(
                        alternative_routes, shipment.priority, route_conditions
                    )
                    
                    # Create rerouting decision
                    decision = {
                        "shipment_id": shipment_id,
                        "old_route": current_route,
                        "new_route": new_route,
                        "reason": reason,
                        "new_eta": new_eta
                    }
                    
                    rerouting_decisions.append(decision)
                    logger.info(
                        f"Decided to reroute shipment {shipment_id} "
                        f"from route {current_route} to {new_route} due to {reason}"
                    )
                else:
                    logger.warning(
                        f"No alternative routes found for shipment {shipment_id}, "
                        f"cannot reroute despite {reason}"
                    )
        
        return rerouting_decisions

    def _find_alternative_routes(
        self, origin: str, destination: str, current_route: str
    ) -> List[Dict[str, Any]]:
        """
        Find alternative routes between origin and destination.
        
        In a real implementation, this would use routing APIs or
        transportation management systems to find actual alternative routes.
        
        Args:
            origin: Origin location ID
            destination: Destination location ID
            current_route: Current route ID to exclude
            
        Returns:
            List of alternative routes with estimated arrival times
        """
        # This is a placeholder implementation
        # In a real system, this would call routing services or algorithms
        
        # For demonstration purposes, we'll return some dummy alternative routes
        now = datetime.now()
        
        alternatives = [
            {
                "route_id": f"route_{origin}_{destination}_alt1",
                "estimated_duration_hours": 8.5,
                "estimated_arrival": now + timedelta(hours=8.5),
                "distance_km": 320,
                "fuel_consumption_liters": 95
            },
            {
                "route_id": f"route_{origin}_{destination}_alt2",
                "estimated_duration_hours": 9.2,
                "estimated_arrival": now + timedelta(hours=9.2),
                "distance_km": 350,
                "fuel_consumption_liters": 105
            },
            {
                "route_id": f"route_{origin}_{destination}_alt3",
                "estimated_duration_hours": 10.0,
                "estimated_arrival": now + timedelta(hours=10),
                "distance_km": 380,
                "fuel_consumption_liters": 115
            }
        ]
        
        # Filter out the current route
        return [route for route in alternatives if route["route_id"] != current_route]

    def _select_best_route(
        self,
        alternative_routes: List[Dict[str, Any]],
        shipment_priority: int,
        route_conditions: Dict[str, RouteStatus]
    ) -> Tuple[str, datetime]:
        """
        Select the best alternative route based on conditions and priority.
        
        Args:
            alternative_routes: List of alternative routes
            shipment_priority: Priority of the shipment (1-10)
            route_conditions: Dictionary of route condition objects
            
        Returns:
            Tuple of (selected route ID, estimated arrival time)
        """
        # Filter out routes that are known to be disrupted
        valid_routes = []
        for route in alternative_routes:
            route_id = route["route_id"]
            is_disrupted = False
            
            if route_id in route_conditions:
                is_disrupted = route_conditions[route_id].is_disrupted
            
            if not is_disrupted:
                valid_routes.append(route)
        
        # If no valid routes, fall back to all alternatives
        if not valid_routes:
            valid_routes = alternative_routes
        
        # For high priority shipments, prioritize speed
        if shipment_priority >= 8:
            sorted_routes = sorted(
                valid_routes,
                key=lambda x: x["estimated_duration_hours"]
            )
        # For medium priority, balance speed and efficiency
        elif shipment_priority >= 5:
            sorted_routes = sorted(
                valid_routes,
                key=lambda x: (x["estimated_duration_hours"], x["fuel_consumption_liters"])
            )
        # For low priority, prioritize efficiency
        else:
            sorted_routes = sorted(
                valid_routes,
                key=lambda x: x["fuel_consumption_liters"]
            )
        
        # Return the best route
        best_route = sorted_routes[0]
        return best_route["route_id"], best_route["estimated_arrival"]

    def optimize_logistics(
        self,
        warehouses: Dict[str, Warehouse],
        active_shipments: Dict[str, Shipment],
        route_conditions: Dict[str, RouteStatus]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for logistics optimization.
        
        Args:
            warehouses: Dictionary of warehouse objects
            active_shipments: Dictionary of active shipment objects
            route_conditions: Dictionary of route condition objects
            
        Returns:
            List of optimization recommendations
        """
        logger.info("Generating logistics optimization recommendations")
        
        recommendations = []
        
        # Group shipments by region for potential consolidation
        shipment_groups = self._group_shipments_by_region(active_shipments)
        
        # Generate route optimization recommendations
        route_recommendations = self._optimize_routes(shipment_groups, route_conditions)
        recommendations.extend(route_recommendations)
        
        # Generate inventory balancing recommendations
        inventory_recommendations = self._balance_inventory(warehouses)
        recommendations.extend(inventory_recommendations)
        
        # Generate schedule adjustment recommendations
        schedule_recommendations = self._optimize_schedules(active_shipments)
        recommendations.extend(schedule_recommendations)
        
        logger.info(f"Generated {len(recommendations)} optimization recommendations")
        return recommendations

    def _group_shipments_by_region(
        self, active_shipments: Dict[str, Shipment]
    ) -> Dict[str, List[Shipment]]:
        """
        Group shipments by destination region for potential consolidation.
        
        Args:
            active_shipments: Dictionary of active shipment objects
            
        Returns:
            Dictionary of shipments grouped by region
        """
        # This is a simplified implementation
        # In a real system, this would use actual geographic regions
        
        shipment_groups = {}
        
        for shipment_id, shipment in active_shipments.items():
            # Extract region from destination (simplified approach)
            region = shipment.destination.split('_')[0]
            
            if region not in shipment_groups:
                shipment_groups[region] = []
                
            shipment_groups[region].append(shipment)
        
        return shipment_groups

    def _optimize_routes(
        self,
        shipment_groups: Dict[str, List[Shipment]],
        route_conditions: Dict[str, RouteStatus]
    ) -> List[Dict[str, Any]]:
        """
        Generate route optimization recommendations for shipment groups.
        
        Args:
            shipment_groups: Dictionary of shipments grouped by region
            route_conditions: Dictionary of route condition objects
            
        Returns:
            List of route optimization recommendations
        """
        recommendations = []
        
        for region, shipments in shipment_groups.items():
            # Only consider groups with multiple shipments
            if len(shipments) < 2:
                continue
                
            # Find shipments that could be consolidated
            consolidation_candidates = self._find_consolidation_candidates(shipments)
            
            if consolidation_candidates:
                shipment_ids = [s.id for s in consolidation_candidates]
                
                # Generate optimized routes
                optimized_routes, new_etas, estimated_savings = self._generate_optimized_routes(
                    consolidation_candidates, route_conditions
                )
                
                if optimized_routes:
                    recommendation = {
                        "type": "route_optimization",
                        "optimization_id": f"opt_{region}_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "shipment_ids": shipment_ids,
                        "optimized_routes": optimized_routes,
                        "new_etas": new_etas,
                        "estimated_savings": estimated_savings
                    }
                    
                    recommendations.append(recommendation)
                    logger.info(
                        f"Generated route optimization recommendation for {len(shipment_ids)} "
                        f"shipments in region {region}, estimated savings: {estimated_savings}"
                    )
        
        return recommendations

    def _find_consolidation_candidates(
        self, shipments: List[Shipment]
    ) -> List[Shipment]:
        """
        Find shipments that could be consolidated based on proximity and timing.
        
        Args:
            shipments: List of shipment objects
            
        Returns:
            List of shipments that are candidates for consolidation
        """
        # This is a simplified implementation
        # In a real system, this would use more sophisticated clustering algorithms
        
        # For demonstration, we'll just return shipments that are in transit
        # and not already being rerouted
        candidates = []
        
        for shipment in shipments:
            if (
                shipment.status == ShipmentStatus.IN_TRANSIT
                and shipment.estimated_arrival is not None
            ):
                candidates.append(shipment)
        
        return candidates

    def _generate_optimized_routes(
        self,
        shipments: List[Shipment],
        route_conditions: Dict[str, RouteStatus]
    ) -> Tuple[List[str], List[datetime], Dict[str, Any]]:
        """
        Generate optimized routes for a set of shipments.
        
        In a real implementation, this would use vehicle routing algorithms
        or transportation optimization services.
        
        Args:
            shipments: List of shipment objects
            route_conditions: Dictionary of route condition objects
            
        Returns:
            Tuple of (optimized route IDs, new estimated arrival times, estimated savings)
        """
        # This is a placeholder implementation
        # In a real system, this would use actual routing optimization algorithms
        
        # For demonstration purposes, we'll generate dummy optimized routes
        optimized_routes = []
        new_etas = []
        now = datetime.now()
        
        for shipment in shipments:
            # Generate a new "optimized" route ID
            new_route = f"opt_route_{shipment.origin}_{shipment.destination}"
            optimized_routes.append(new_route)
            
            # Estimate a slightly improved arrival time (10% faster)
            if shipment.estimated_arrival:
                current_duration = (shipment.estimated_arrival - now).total_seconds()
                new_duration = current_duration * 0.9  # 10% improvement
                new_eta = now + timedelta(seconds=new_duration)
                new_etas.append(new_eta)
            else:
                # Fallback if no current ETA
                new_etas.append(now + timedelta(hours=8))
        
        # Estimate savings
        estimated_savings = {
            "distance_km": 120,  # Estimated distance saved
            "fuel_liters": 35,   # Estimated fuel saved
            "time_hours": 2.5,   # Estimated time saved
            "cost_usd": 180      # Estimated cost saved
        }
        
        return optimized_routes, new_etas, estimated_savings

    def _balance_inventory(
        self, warehouses: Dict[str, Warehouse]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for balancing inventory across warehouses.
        
        Args:
            warehouses: Dictionary of warehouse objects
            
        Returns:
            List of inventory balancing recommendations
        """
        recommendations = []
        
        # Identify items with significant imbalances across warehouses
        imbalanced_items = self._identify_inventory_imbalances(warehouses)
        
        for item_id, imbalance_data in imbalanced_items.items():
            excess_warehouses = imbalance_data["excess"]
            deficit_warehouses = imbalance_data["deficit"]
            
            # Skip if no clear imbalance
            if not excess_warehouses or not deficit_warehouses:
                continue
                
            # Generate transfer recommendations
            for deficit_id, deficit_amount in deficit_warehouses.items():
                # Find the best source warehouse
                best_source = None
                best_distance = float('inf')
                
                for excess_id, excess_amount in excess_warehouses.items():
                    # Skip if not enough excess to address deficit
                    if excess_amount <= 0:
                        continue
                        
                    distance = self._calculate_distance(excess_id, deficit_id)
                    if distance < best_distance:
                        best_source = excess_id
                        best_distance = distance
                
                if best_source:
                    # Calculate transfer amount
                    excess_amount = excess_warehouses[best_source]
                    transfer_amount = min(excess_amount, deficit_amount)
                    
                    # Create transfer recommendation
                    recommendation = {
                        "type": "inventory_transfer",
                        "source_warehouse": best_source,
                        "destination_warehouse": deficit_id,
                        "items": [
                            {
                                "id": item_id,
                                "name": imbalance_data["name"],
                                "quantity": transfer_amount,
                                "unit": imbalance_data["unit"]
                            }
                        ],
                        "reason": "inventory_balancing",
                        "priority": 3  # Lower priority than critical shortages
                    }
                    
                    recommendations.append(recommendation)
                    logger.info(
                        f"Generated inventory balancing recommendation: transfer {transfer_amount} "
                        f"units of {item_id} from {best_source} to {deficit_id}"
                    )
                    
                    # Update remaining excess
                    excess_warehouses[best_source] -= transfer_amount
        
        return recommendations

    def _identify_inventory_imbalances(
        self, warehouses: Dict[str, Warehouse]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Identify items with significant imbalances across warehouses.
        
        Args:
            warehouses: Dictionary of warehouse objects
            
        Returns:
            Dictionary of imbalanced items with excess and deficit warehouses
        """
        imbalanced_items = {}
        
        # First, collect inventory levels for each item across warehouses
        item_inventory = {}
        
        for warehouse_id, warehouse in warehouses.items():
            for item_id, item in warehouse.items.items():
                if item_id not in item_inventory:
                    item_inventory[item_id] = {
                        "name": item.name,
                        "category": item.category,
                        "unit": item.unit,
                        "warehouses": {}
                    }
                
                item_inventory[item_id]["warehouses"][warehouse_id] = {
                    "quantity": item.quantity,
                    "min_threshold": item.min_threshold,
                    "max_threshold": item.max_threshold
                }
        
        # Identify imbalances for each item
        for item_id, item_data in item_inventory.items():
            # Skip items that are only in one warehouse
            if len(item_data["warehouses"]) <= 1:
                continue
                
            excess_warehouses = {}
            deficit_warehouses = {}
            
            # Calculate average inventory level relative to thresholds
            total_ratio = 0
            warehouse_count = 0
            
            for warehouse_id, inventory in item_data["warehouses"].items():
                quantity = inventory["quantity"]
                min_threshold = inventory["min_threshold"]
                max_threshold = inventory["max_threshold"]
                
                # Calculate inventory level as ratio between min and max thresholds
                # 0 = at min threshold, 1 = at max threshold
                threshold_range = max_threshold - min_threshold
                if threshold_range > 0:
                    ratio = (quantity - min_threshold) / threshold_range
                    total_ratio += ratio
                    warehouse_count += 1
            
            # Skip if no valid ratios
            if warehouse_count == 0:
                continue
                
            # Calculate average ratio
            avg_ratio = total_ratio / warehouse_count
            
            # Identify warehouses with excess or deficit
            for warehouse_id, inventory in item_data["warehouses"].items():
                quantity = inventory["quantity"]
                min_threshold = inventory["min_threshold"]
                max_threshold = inventory["max_threshold"]
                threshold_range = max_threshold - min_threshold
                
                if threshold_range > 0:
                    ratio = (quantity - min_threshold) / threshold_range
                    
                    # Significant excess (>25% above average)
                    if ratio > avg_ratio + 0.25:
                        excess_amount = int((ratio - avg_ratio - 0.15) * threshold_range)
                        if excess_amount > 0:
                            excess_warehouses[warehouse_id] = excess_amount
                    
                    # Significant deficit (>25% below average)
                    elif ratio < avg_ratio - 0.25:
                        deficit_amount = int((avg_ratio - 0.15 - ratio) * threshold_range)
                        if deficit_amount > 0:
                            deficit_warehouses[warehouse_id] = deficit_amount
            
            # Only include items with clear imbalances
            if excess_warehouses and deficit_warehouses:
                imbalanced_items[item_id] = {
                    "name": item_data["name"],
                    "unit": item_data["unit"],
                    "excess": excess_warehouses,
                    "deficit": deficit_warehouses
                }
        
        return imbalanced_items

    def _optimize_schedules(
        self, active_shipments: Dict[str, Shipment]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for optimizing delivery schedules.
        
        Args:
            active_shipments: Dictionary of active shipment objects
            
        Returns:
            List of schedule optimization recommendations
        """
        recommendations = []
        
        # Group shipments by destination
        destination_groups = {}
        for shipment_id, shipment in active_shipments.items():
            destination = shipment.destination
            
            if destination not in destination_groups:
                destination_groups[destination] = []
                
            destination_groups[destination].append(shipment)
        
        # Look for destinations with multiple deliveries on the same day
        for destination, shipments in destination_groups.items():
            # Skip if fewer than 2 shipments
            if len(shipments) < 2:
                continue
                
            # Group shipments by estimated arrival date
            date_groups = {}
            for shipment in shipments:
                if shipment.estimated_arrival:
                    arrival_date = shipment.estimated_arrival.date()
                    
                    if arrival_date not in date_groups:
                        date_groups[arrival_date] = []
                        
                    date_groups[arrival_date].append(shipment)
            
            # Look for dates with multiple deliveries
            for date, date_shipments in date_groups.items():
                if len(date_shipments) >= 2:
                    # Generate schedule adjustment recommendation
                    shipment_ids = [s.id for s in date_shipments]
                    new_schedules = self._generate_staggered_schedules(date_shipments)
                    
                    recommendation = {
                        "type": "schedule_adjustment",
                        "adjustment_id": f"adj_{destination}_{date.strftime('%Y%m%d')}",
                        "shipment_ids": shipment_ids,
                        "new_schedules": new_schedules,
                        "reason": "optimize_receiving_operations"
                    }
                    
                    recommendations.append(recommendation)
                    logger.info(
                        f"Generated schedule adjustment recommendation for {len(shipment_ids)} "
                        f"shipments to {destination} on {date}"
                    )
        
        return recommendations

    def _generate_staggered_schedules(
        self, shipments: List[Shipment]
    ) -> List[Dict[str, Any]]:
        """
        Generate staggered delivery schedules to avoid bottlenecks.
        
        Args:
            shipments: List of shipment objects arriving on the same day
            
        Returns:
            List of new schedule objects
        """
        new_schedules = []
        
        # Sort shipments by priority (higher priority first)
        sorted_shipments = sorted(
            shipments,
            key=lambda s: s.priority,
            reverse=True
        )
        
        # Use the earliest estimated arrival as the base time
        base_time = min(
            s.estimated_arrival for s in sorted_shipments if s.estimated_arrival
        )
        base_date = base_time.date()
        
        # Start at 9 AM if base time is earlier, otherwise use base time
        start_time = datetime.combine(
            base_date,
            datetime.min.time().replace(hour=9)
        )
        if base_time > start_time:
            start_time = base_time
        
        # Generate staggered schedules with 2-hour intervals
        for i, shipment in enumerate(sorted_shipments):
            # Calculate new arrival time (2-hour intervals)
            new_arrival = start_time + timedelta(hours=i * 2)
            
            # Create new schedule
            new_schedule = {
                "estimated_arrival": new_arrival,
                "delivery_window_start": new_arrival - timedelta(minutes=30),
                "delivery_window_end": new_arrival + timedelta(minutes=30)
            }
            
            new_schedules.append(new_schedule)
        
        return new_schedules
