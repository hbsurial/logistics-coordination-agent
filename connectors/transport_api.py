"""
Transport API connector for the Logistics Coordination Agent.

This module provides the interface to interact with the transportation tracking system,
retrieving shipment data and updating routes.
"""

import logging
import time
from typing import Dict, List, Any, Optional

import requests
from requests.exceptions import RequestException

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class TransportAPI:
    """
    Connector for the transportation tracking system API.
    
    This class handles all interactions with the transportation system,
    including retrieving shipment data and updating routes.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Transport API connector.
        
        Args:
            config: Agent configuration settings
        """
        self.config = config
        
        # API connection settings
        self.api_url = self._get_env_var("TRANSPORT_API_URL")
        self.api_key = self._get_env_var("TRANSPORT_API_KEY")
        self.api_secret = self._get_env_var("TRANSPORT_API_SECRET")
        
        # Request timeout and retry settings
        self.timeout = config.api_timeout_seconds
        self.max_retries = config.api_retry_attempts
        self.retry_delay = config.api_retry_delay_seconds
        
        logger.info(f"Transport API connector initialized: {self.api_url}")

    def _get_env_var(self, var_name: str) -> str:
        """
        Get environment variable with error handling.
        
        Args:
            var_name: Name of the environment variable
            
        Returns:
            Value of the environment variable
            
        Raises:
            ValueError: If the environment variable is not set
        """
        import os
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Environment variable {var_name} is not set")
        return value

    def _make_request(
        self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data
            
        Returns:
            API response data
            
        Raises:
            RequestException: If the request fails after all retries
        """
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=data,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                return response.json()
                
            except RequestException as e:
                logger.warning(
                    f"API request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}"
                )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"API request failed after {self.max_retries} attempts")
                    raise
        
        # This should never be reached due to the raise in the loop
        raise RequestException("API request failed")

    def get_active_shipments(self) -> Dict[str, Any]:
        """
        Get data for all active shipments.
        
        Returns:
            Dictionary containing data for all active shipments
        """
        logger.info("Retrieving data for all active shipments")
        
        try:
            response = self._make_request("GET", "shipments/active")
            logger.info(f"Retrieved data for {len(response)} active shipments")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve active shipment data: {str(e)}")
            # Return empty dict on failure to avoid breaking the agent
            return {}

    def get_shipment(self, shipment_id: str) -> Dict[str, Any]:
        """
        Get data for a specific shipment.
        
        Args:
            shipment_id: ID of the shipment
            
        Returns:
            Dictionary containing shipment data
        """
        logger.info(f"Retrieving data for shipment {shipment_id}")
        
        try:
            response = self._make_request("GET", f"shipments/{shipment_id}")
            logger.info(f"Retrieved data for shipment {shipment_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve data for shipment {shipment_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "id": shipment_id,
                "status": "unknown",
                "origin": "unknown",
                "destination": "unknown",
                "route": "unknown",
                "estimated_arrival": None
            }

    def get_route_details(self, route_id: str) -> Dict[str, Any]:
        """
        Get details for a specific route.
        
        Args:
            route_id: ID of the route
            
        Returns:
            Dictionary containing route details
        """
        logger.info(f"Retrieving details for route {route_id}")
        
        try:
            response = self._make_request("GET", f"routes/{route_id}")
            logger.info(f"Retrieved details for route {route_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve details for route {route_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "route_id": route_id,
                "origin": "unknown",
                "destination": "unknown",
                "distance_km": 0,
                "estimated_duration_hours": 0
            }

    def get_road_conditions(self, route_id: str) -> Dict[str, Any]:
        """
        Get road conditions for a specific route.
        
        Args:
            route_id: ID of the route
            
        Returns:
            Dictionary containing road condition data
        """
        logger.info(f"Retrieving road conditions for route {route_id}")
        
        try:
            response = self._make_request("GET", f"routes/{route_id}/conditions")
            logger.info(f"Retrieved road conditions for route {route_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve road conditions for route {route_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "route_id": route_id,
                "conditions": "unknown",
                "closed": False,
                "severe_damage": False,
                "flooding": False,
                "last_updated": None
            }

    def update_route(self, shipment_id: str, new_route_id: str) -> bool:
        """
        Update the route for a shipment.
        
        Args:
            shipment_id: ID of the shipment
            new_route_id: ID of the new route
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating route for shipment {shipment_id} to {new_route_id}")
        
        try:
            data = {
                "route_id": new_route_id,
                "updated_by": self.config.agent_name,
                "reason": "route_optimization"
            }
            
            response = self._make_request(
                "PUT", f"shipments/{shipment_id}/route", data=data
            )
            
            logger.info(f"Successfully updated route for shipment {shipment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update route for shipment {shipment_id}: {str(e)}")
            return False

    def update_schedule(self, shipment_id: str, schedule: Dict[str, Any]) -> bool:
        """
        Update the delivery schedule for a shipment.
        
        Args:
            shipment_id: ID of the shipment
            schedule: New schedule data
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Updating schedule for shipment {shipment_id}")
        
        try:
            data = {
                "estimated_arrival": schedule["estimated_arrival"].isoformat(),
                "delivery_window_start": schedule["delivery_window_start"].isoformat(),
                "delivery_window_end": schedule["delivery_window_end"].isoformat(),
                "updated_by": self.config.agent_name,
                "reason": "schedule_optimization"
            }
            
            response = self._make_request(
                "PUT", f"shipments/{shipment_id}/schedule", data=data
            )
            
            logger.info(f"Successfully updated schedule for shipment {shipment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update schedule for shipment {shipment_id}: {str(e)}")
            return False

    def get_alternative_routes(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        """
        Get alternative routes between origin and destination.
        
        Args:
            origin: Origin location ID
            destination: Destination location ID
            
        Returns:
            List of alternative route objects
        """
        logger.info(f"Retrieving alternative routes from {origin} to {destination}")
        
        try:
            params = {
                "origin": origin,
                "destination": destination,
                "max_alternatives": 5
            }
            
            response = self._make_request("GET", "routes/alternatives", params=params)
            
            routes = response.get("routes", [])
            logger.info(f"Retrieved {len(routes)} alternative routes from {origin} to {destination}")
            return routes
        except Exception as e:
            logger.error(f"Failed to retrieve alternative routes: {str(e)}")
            # Return empty list on failure to avoid breaking the agent
            return []

    def create_shipment(
        self, origin: str, destination: str, items: List[Dict[str, Any]], priority: int
    ) -> Optional[str]:
        """
        Create a new shipment.
        
        Args:
            origin: Origin warehouse ID
            destination: Destination warehouse ID
            items: List of items to ship
            priority: Shipment priority (1-10)
            
        Returns:
            Shipment ID if successful, None otherwise
        """
        logger.info(f"Creating shipment from {origin} to {destination} with {len(items)} items")
        
        try:
            data = {
                "origin": origin,
                "destination": destination,
                "items": items,
                "priority": priority,
                "created_by": self.config.agent_name
            }
            
            response = self._make_request("POST", "shipments", data=data)
            
            shipment_id = response.get("shipment_id")
            if shipment_id:
                logger.info(f"Successfully created shipment {shipment_id}")
                return shipment_id
            else:
                logger.error("Failed to create shipment: No shipment ID in response")
                return None
        except Exception as e:
            logger.error(f"Failed to create shipment: {str(e)}")
            return None

    def cancel_shipment(self, shipment_id: str, reason: str) -> bool:
        """
        Cancel a shipment.
        
        Args:
            shipment_id: ID of the shipment
            reason: Reason for cancellation
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Cancelling shipment {shipment_id} (reason: {reason})")
        
        try:
            data = {
                "reason": reason,
                "cancelled_by": self.config.agent_name
            }
            
            response = self._make_request("POST", f"shipments/{shipment_id}/cancel", data=data)
            
            logger.info(f"Successfully cancelled shipment {shipment_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel shipment {shipment_id}: {str(e)}")
            return False
