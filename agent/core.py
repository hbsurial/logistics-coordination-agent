"""
Core implementation of the Logistics Coordination Agent.

This module contains the main LogisticsAgent class that coordinates
all monitoring, decision-making, and action execution for logistics optimization.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from agent.config import AgentConfig
from agent.decision_engine import DecisionEngine
from connectors.inventory_api import InventoryAPI
from connectors.transport_api import TransportAPI
from connectors.weather_api import WeatherAPI
from models.inventory import InventoryItem, Warehouse
from models.route import Route, RouteStatus
from models.shipment import Shipment, ShipmentStatus
from utils.data_processing import normalize_data
from utils.notifications import NotificationManager

logger = logging.getLogger(__name__)


class LogisticsAgent:
    """
    Agentic AI system for logistics coordination in humanitarian operations.
    
    This agent continuously monitors inventory levels, shipment status, and external
    conditions to optimize logistics operations and respond to disruptions.
    """

    def __init__(
        self,
        config: AgentConfig,
        inventory_api: InventoryAPI,
        transport_api: TransportAPI,
        weather_api: WeatherAPI,
    ):
        """
        Initialize the Logistics Coordination Agent.
        
        Args:
            config: Configuration settings for the agent
            inventory_api: API connector for inventory management system
            transport_api: API connector for transportation tracking system
            weather_api: API connector for weather and road conditions
        """
        self.config = config
        self.inventory_api = inventory_api
        self.transport_api = transport_api
        self.weather_api = weather_api
        
        self.decision_engine = DecisionEngine(config)
        self.notification_manager = NotificationManager(config)
        
        self.warehouses: Dict[str, Warehouse] = {}
        self.active_shipments: Dict[str, Shipment] = {}
        self.route_conditions: Dict[str, RouteStatus] = {}
        
        self.last_inventory_check: Optional[datetime] = None
        self.last_shipment_check: Optional[datetime] = None
        self.last_weather_check: Optional[datetime] = None
        
        logger.info(f"Logistics Agent initialized with {config.agent_name}")

    def run(self) -> None:
        """
        Run the agent's main loop, continuously monitoring and making decisions.
        """
        logger.info("Starting Logistics Agent main loop")
        
        try:
            while True:
                self._check_inventory()
                self._monitor_shipments()
                self._update_route_conditions()
                self._optimize_operations()
                
                time.sleep(self.config.main_loop_interval)
        except KeyboardInterrupt:
            logger.info("Logistics Agent stopped by user")
        except Exception as e:
            logger.error(f"Logistics Agent encountered an error: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "agent_error", f"Agent error: {str(e)}", severity="high"
            )

    def _check_inventory(self) -> None:
        """
        Check inventory levels across all warehouses and identify potential shortages.
        """
        now = datetime.now()
        
        # Only check inventory at the configured interval
        if (
            self.last_inventory_check is not None
            and now - self.last_inventory_check < timedelta(seconds=self.config.inventory_check_interval)
        ):
            return
            
        logger.info("Checking inventory levels across warehouses")
        self.last_inventory_check = now
        
        try:
            # Get updated inventory data from API
            inventory_data = self.inventory_api.get_all_inventory()
            normalized_data = normalize_data(inventory_data, "inventory")
            
            # Update warehouse inventory levels
            for warehouse_id, items in normalized_data.items():
                if warehouse_id not in self.warehouses:
                    warehouse_info = self.inventory_api.get_warehouse_info(warehouse_id)
                    self.warehouses[warehouse_id] = Warehouse(
                        id=warehouse_id,
                        name=warehouse_info["name"],
                        location=warehouse_info["location"],
                        capacity=warehouse_info["capacity"],
                        items={}
                    )
                
                # Update inventory items
                for item_id, item_data in items.items():
                    self.warehouses[warehouse_id].items[item_id] = InventoryItem(
                        id=item_id,
                        name=item_data["name"],
                        category=item_data["category"],
                        quantity=item_data["quantity"],
                        unit=item_data["unit"],
                        min_threshold=item_data["min_threshold"],
                        max_threshold=item_data["max_threshold"],
                        last_updated=now
                    )
            
            # Check for inventory alerts
            self._check_inventory_alerts()
            
        except Exception as e:
            logger.error(f"Error checking inventory: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "inventory_check_error", f"Failed to check inventory: {str(e)}", severity="medium"
            )

    def _check_inventory_alerts(self) -> None:
        """
        Identify inventory items that are below threshold and require action.
        """
        alerts = []
        
        for warehouse_id, warehouse in self.warehouses.items():
            for item_id, item in warehouse.items.items():
                # Check if item is below minimum threshold
                if item.quantity < item.min_threshold:
                    alert_data = {
                        "warehouse_id": warehouse_id,
                        "warehouse_name": warehouse.name,
                        "item_id": item_id,
                        "item_name": item.name,
                        "current_quantity": item.quantity,
                        "min_threshold": item.min_threshold,
                        "unit": item.unit,
                        "severity": "high" if item.quantity == 0 else "medium"
                    }
                    alerts.append(alert_data)
                    
                    logger.warning(
                        f"Inventory alert: {item.name} in {warehouse.name} is below threshold "
                        f"({item.quantity}/{item.min_threshold} {item.unit})"
                    )
        
        if alerts:
            # Trigger inventory replenishment decision
            self.decision_engine.evaluate_inventory_replenishment(
                self.warehouses, alerts
            )
            
            # Send notifications about low inventory
            self.notification_manager.send_inventory_alerts(alerts)

    def _monitor_shipments(self) -> None:
        """
        Monitor the status of all active shipments and detect delays or issues.
        """
        now = datetime.now()
        
        # Only check shipments at the configured interval
        if (
            self.last_shipment_check is not None
            and now - self.last_shipment_check < timedelta(seconds=self.config.shipment_check_interval)
        ):
            return
            
        logger.info("Monitoring active shipments")
        self.last_shipment_check = now
        
        try:
            # Get updated shipment data from API
            shipment_data = self.transport_api.get_active_shipments()
            normalized_data = normalize_data(shipment_data, "shipment")
            
            # Update active shipments
            current_shipment_ids = set()
            for shipment_id, shipment_info in normalized_data.items():
                current_shipment_ids.add(shipment_id)
                
                if shipment_id not in self.active_shipments:
                    # New shipment
                    self.active_shipments[shipment_id] = Shipment(
                        id=shipment_id,
                        origin=shipment_info["origin"],
                        destination=shipment_info["destination"],
                        items=shipment_info["items"],
                        status=ShipmentStatus(shipment_info["status"]),
                        priority=shipment_info["priority"],
                        route=shipment_info["route"],
                        estimated_arrival=shipment_info["estimated_arrival"],
                        actual_arrival=None,
                        last_updated=now
                    )
                else:
                    # Update existing shipment
                    self.active_shipments[shipment_id].status = ShipmentStatus(shipment_info["status"])
                    self.active_shipments[shipment_id].route = shipment_info["route"]
                    self.active_shipments[shipment_id].estimated_arrival = shipment_info["estimated_arrival"]
                    self.active_shipments[shipment_id].last_updated = now
                    
                    if shipment_info["status"] == "delivered":
                        self.active_shipments[shipment_id].actual_arrival = now
            
            # Remove completed shipments
            completed_shipments = []
            for shipment_id in list(self.active_shipments.keys()):
                if (
                    shipment_id not in current_shipment_ids
                    or self.active_shipments[shipment_id].status in [ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED]
                ):
                    completed_shipments.append(self.active_shipments[shipment_id])
                    del self.active_shipments[shipment_id]
            
            # Process completed shipments
            if completed_shipments:
                self._process_completed_shipments(completed_shipments)
            
            # Check for shipment delays or issues
            self._check_shipment_issues()
            
        except Exception as e:
            logger.error(f"Error monitoring shipments: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "shipment_monitor_error", f"Failed to monitor shipments: {str(e)}", severity="medium"
            )

    def _process_completed_shipments(self, shipments: List[Shipment]) -> None:
        """
        Process shipments that have been completed (delivered or cancelled).
        
        Args:
            shipments: List of completed shipment objects
        """
        for shipment in shipments:
            logger.info(f"Shipment {shipment.id} completed with status {shipment.status}")
            
            # Update inventory if shipment was delivered
            if shipment.status == ShipmentStatus.DELIVERED:
                try:
                    # Get the destination warehouse
                    destination_id = shipment.destination
                    if destination_id in self.warehouses:
                        # Update inventory with delivered items
                        for item in shipment.items:
                            item_id = item["id"]
                            quantity = item["quantity"]
                            
                            if item_id in self.warehouses[destination_id].items:
                                self.warehouses[destination_id].items[item_id].quantity += quantity
                                logger.info(
                                    f"Updated inventory for {item_id} in warehouse {destination_id}: "
                                    f"added {quantity} units"
                                )
                except Exception as e:
                    logger.error(f"Error updating inventory for delivered shipment: {e}", exc_info=True)
            
            # Notify stakeholders about completed shipment
            self.notification_manager.send_shipment_update(
                shipment_id=shipment.id,
                status=shipment.status.value,
                message=f"Shipment {shipment.id} has been {shipment.status.value}",
                details={
                    "origin": shipment.origin,
                    "destination": shipment.destination,
                    "items": shipment.items,
                    "completed_at": datetime.now().isoformat()
                }
            )

    def _check_shipment_issues(self) -> None:
        """
        Identify shipments with delays or other issues that require attention.
        """
        issues = []
        now = datetime.now()
        
        for shipment_id, shipment in self.active_shipments.items():
            # Skip shipments that are already being handled
            if shipment.status in [ShipmentStatus.REROUTING, ShipmentStatus.ON_HOLD]:
                continue
                
            # Check for delays
            if shipment.estimated_arrival and shipment.estimated_arrival < now:
                delay_minutes = (now - shipment.estimated_arrival).total_seconds() / 60
                
                issue_data = {
                    "shipment_id": shipment_id,
                    "origin": shipment.origin,
                    "destination": shipment.destination,
                    "status": shipment.status.value,
                    "estimated_arrival": shipment.estimated_arrival.isoformat(),
                    "delay_minutes": delay_minutes,
                    "priority": shipment.priority,
                    "severity": "high" if shipment.priority >= 8 else "medium"
                }
                issues.append(issue_data)
                
                logger.warning(
                    f"Shipment delay: {shipment_id} is delayed by {delay_minutes:.1f} minutes, "
                    f"priority: {shipment.priority}"
                )
        
        if issues:
            # Trigger shipment rerouting decision
            rerouting_decisions = self.decision_engine.evaluate_shipment_rerouting(
                self.active_shipments, issues, self.route_conditions
            )
            
            # Execute rerouting decisions
            for decision in rerouting_decisions:
                self._execute_rerouting(decision)
            
            # Send notifications about shipment issues
            self.notification_manager.send_shipment_alerts(issues)

    def _update_route_conditions(self) -> None:
        """
        Update information about route conditions, including weather and infrastructure status.
        """
        now = datetime.now()
        
        # Only check route conditions at the configured interval
        if (
            self.last_weather_check is not None
            and now - self.last_weather_check < timedelta(seconds=self.config.weather_check_interval)
        ):
            return
            
        logger.info("Updating route conditions")
        self.last_weather_check = now
        
        try:
            # Get all unique routes from active shipments
            active_routes = set()
            for shipment in self.active_shipments.values():
                active_routes.add(shipment.route)
            
            # Update conditions for each active route
            for route_id in active_routes:
                # Get weather conditions along the route
                weather_data = self.weather_api.get_conditions_along_route(route_id)
                
                # Get road and infrastructure conditions
                road_data = self.transport_api.get_road_conditions(route_id)
                
                # Combine and normalize data
                route_data = {
                    "weather": weather_data,
                    "road": road_data
                }
                normalized_data = normalize_data(route_data, "route")
                
                # Determine if route is disrupted
                is_disrupted = self._is_route_disrupted(normalized_data)
                
                # Update route status
                self.route_conditions[route_id] = RouteStatus(
                    route_id=route_id,
                    weather_conditions=normalized_data["weather"],
                    road_conditions=normalized_data["road"],
                    is_disrupted=is_disrupted,
                    last_updated=now
                )
                
                if is_disrupted:
                    logger.warning(f"Route {route_id} is currently disrupted")
                    
                    # Notify about disrupted route
                    self.notification_manager.send_route_alert(
                        route_id=route_id,
                        status="disrupted",
                        message=f"Route {route_id} is currently disrupted",
                        details=normalized_data
                    )
        
        except Exception as e:
            logger.error(f"Error updating route conditions: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "route_update_error", f"Failed to update route conditions: {str(e)}", severity="medium"
            )

    def _is_route_disrupted(self, route_data: Dict[str, Any]) -> bool:
        """
        Determine if a route is disrupted based on weather and road conditions.
        
        Args:
            route_data: Normalized data about route conditions
            
        Returns:
            True if the route is disrupted, False otherwise
        """
        # Check weather conditions
        weather = route_data["weather"]
        if weather.get("severe_weather", False):
            return True
        
        if weather.get("visibility_meters", 10000) < self.config.min_visibility_meters:
            return True
            
        if weather.get("wind_speed_kmh", 0) > self.config.max_wind_speed_kmh:
            return True
        
        # Check road conditions
        road = route_data["road"]
        if road.get("closed", False):
            return True
            
        if road.get("severe_damage", False):
            return True
            
        if road.get("flooding", False):
            return True
        
        return False

    def _optimize_operations(self) -> None:
        """
        Run periodic optimization of logistics operations.
        """
        logger.info("Running logistics optimization")
        
        try:
            # Generate optimization recommendations
            recommendations = self.decision_engine.optimize_logistics(
                warehouses=self.warehouses,
                active_shipments=self.active_shipments,
                route_conditions=self.route_conditions
            )
            
            # Execute optimization recommendations
            for recommendation in recommendations:
                recommendation_type = recommendation["type"]
                
                if recommendation_type == "inventory_transfer":
                    self._execute_inventory_transfer(recommendation)
                elif recommendation_type == "route_optimization":
                    self._execute_route_optimization(recommendation)
                elif recommendation_type == "schedule_adjustment":
                    self._execute_schedule_adjustment(recommendation)
                else:
                    logger.warning(f"Unknown recommendation type: {recommendation_type}")
        
        except Exception as e:
            logger.error(f"Error during logistics optimization: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "optimization_error", f"Failed to optimize logistics: {str(e)}", severity="medium"
            )

    def _execute_rerouting(self, decision: Dict[str, Any]) -> None:
        """
        Execute a decision to reroute a shipment.
        
        Args:
            decision: Rerouting decision details
        """
        shipment_id = decision["shipment_id"]
        new_route = decision["new_route"]
        reason = decision["reason"]
        
        logger.info(f"Executing rerouting for shipment {shipment_id} to route {new_route}")
        
        try:
            # Update route in transportation system
            success = self.transport_api.update_route(shipment_id, new_route)
            
            if success:
                # Update local shipment data
                if shipment_id in self.active_shipments:
                    self.active_shipments[shipment_id].route = new_route
                    self.active_shipments[shipment_id].status = ShipmentStatus.REROUTING
                    self.active_shipments[shipment_id].estimated_arrival = decision["new_eta"]
                
                # Notify stakeholders
                self.notification_manager.send_shipment_update(
                    shipment_id=shipment_id,
                    status="rerouted",
                    message=f"Shipment {shipment_id} has been rerouted due to {reason}",
                    details={
                        "old_route": decision["old_route"],
                        "new_route": new_route,
                        "reason": reason,
                        "new_eta": decision["new_eta"].isoformat()
                    }
                )
                
                logger.info(f"Successfully rerouted shipment {shipment_id}")
            else:
                logger.error(f"Failed to reroute shipment {shipment_id}")
                self.notification_manager.send_alert(
                    "reroute_failure",
                    f"Failed to reroute shipment {shipment_id}",
                    severity="high"
                )
        
        except Exception as e:
            logger.error(f"Error executing rerouting for shipment {shipment_id}: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "reroute_error",
                f"Error rerouting shipment {shipment_id}: {str(e)}",
                severity="high"
            )

    def _execute_inventory_transfer(self, recommendation: Dict[str, Any]) -> None:
        """
        Execute a recommendation to transfer inventory between warehouses.
        
        Args:
            recommendation: Inventory transfer recommendation details
        """
        source_warehouse = recommendation["source_warehouse"]
        destination_warehouse = recommendation["destination_warehouse"]
        items = recommendation["items"]
        
        logger.info(
            f"Executing inventory transfer from {source_warehouse} to {destination_warehouse} "
            f"for {len(items)} items"
        )
        
        try:
            # Create transfer request in inventory system
            transfer_id = self.inventory_api.create_inventory_transfer(
                source_warehouse, destination_warehouse, items
            )
            
            if transfer_id:
                # Notify stakeholders
                self.notification_manager.send_inventory_update(
                    update_type="transfer_initiated",
                    message=f"Inventory transfer initiated from {source_warehouse} to {destination_warehouse}",
                    details={
                        "transfer_id": transfer_id,
                        "source_warehouse": source_warehouse,
                        "destination_warehouse": destination_warehouse,
                        "items": items,
                        "reason": recommendation["reason"]
                    }
                )
                
                logger.info(f"Successfully initiated inventory transfer {transfer_id}")
            else:
                logger.error(f"Failed to initiate inventory transfer")
                self.notification_manager.send_alert(
                    "transfer_failure",
                    f"Failed to initiate inventory transfer from {source_warehouse} to {destination_warehouse}",
                    severity="medium"
                )
        
        except Exception as e:
            logger.error(f"Error executing inventory transfer: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "transfer_error",
                f"Error initiating inventory transfer: {str(e)}",
                severity="medium"
            )

    def _execute_route_optimization(self, recommendation: Dict[str, Any]) -> None:
        """
        Execute a recommendation to optimize delivery routes.
        
        Args:
            recommendation: Route optimization recommendation details
        """
        shipment_ids = recommendation["shipment_ids"]
        optimized_routes = recommendation["optimized_routes"]
        
        logger.info(f"Executing route optimization for {len(shipment_ids)} shipments")
        
        try:
            success_count = 0
            
            # Update routes for each shipment
            for i, shipment_id in enumerate(shipment_ids):
                new_route = optimized_routes[i]
                
                # Update route in transportation system
                success = self.transport_api.update_route(shipment_id, new_route)
                
                if success:
                    # Update local shipment data
                    if shipment_id in self.active_shipments:
                        self.active_shipments[shipment_id].route = new_route
                        self.active_shipments[shipment_id].estimated_arrival = recommendation["new_etas"][i]
                    
                    success_count += 1
            
            # Notify stakeholders
            self.notification_manager.send_logistics_update(
                update_type="routes_optimized",
                message=f"Routes optimized for {success_count}/{len(shipment_ids)} shipments",
                details={
                    "optimization_id": recommendation["optimization_id"],
                    "shipment_ids": shipment_ids,
                    "success_count": success_count,
                    "estimated_savings": recommendation["estimated_savings"]
                }
            )
            
            logger.info(f"Successfully optimized routes for {success_count}/{len(shipment_ids)} shipments")
        
        except Exception as e:
            logger.error(f"Error executing route optimization: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "optimization_error",
                f"Error optimizing routes: {str(e)}",
                severity="medium"
            )

    def _execute_schedule_adjustment(self, recommendation: Dict[str, Any]) -> None:
        """
        Execute a recommendation to adjust delivery schedules.
        
        Args:
            recommendation: Schedule adjustment recommendation details
        """
        shipment_ids = recommendation["shipment_ids"]
        new_schedules = recommendation["new_schedules"]
        
        logger.info(f"Executing schedule adjustment for {len(shipment_ids)} shipments")
        
        try:
            success_count = 0
            
            # Update schedule for each shipment
            for i, shipment_id in enumerate(shipment_ids):
                new_schedule = new_schedules[i]
                
                # Update schedule in transportation system
                success = self.transport_api.update_schedule(shipment_id, new_schedule)
                
                if success:
                    # Update local shipment data
                    if shipment_id in self.active_shipments:
                        self.active_shipments[shipment_id].estimated_arrival = new_schedule["estimated_arrival"]
                    
                    success_count += 1
            
            # Notify stakeholders
            self.notification_manager.send_logistics_update(
                update_type="schedules_adjusted",
                message=f"Schedules adjusted for {success_count}/{len(shipment_ids)} shipments",
                details={
                    "adjustment_id": recommendation["adjustment_id"],
                    "shipment_ids": shipment_ids,
                    "success_count": success_count,
                    "reason": recommendation["reason"]
                }
            )
            
            logger.info(f"Successfully adjusted schedules for {success_count}/{len(shipment_ids)} shipments")
        
        except Exception as e:
            logger.error(f"Error executing schedule adjustment: {e}", exc_info=True)
            self.notification_manager.send_alert(
                "adjustment_error",
                f"Error adjusting schedules: {str(e)}",
                severity="medium"
            )
