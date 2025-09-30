"""
Inventory API connector for the Logistics Coordination Agent.

This module provides the interface to interact with the inventory management system,
retrieving inventory data and initiating inventory transfers.
"""

import logging
import time
from typing import Dict, List, Any, Optional

import requests
from requests.exceptions import RequestException

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class InventoryAPI:
    """
    Connector for the inventory management system API.
    
    This class handles all interactions with the inventory management system,
    including retrieving inventory data and initiating inventory transfers.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Inventory API connector.
        
        Args:
            config: Agent configuration settings
        """
        self.config = config
        
        # API connection settings
        self.api_url = self._get_env_var("INVENTORY_API_URL")
        self.api_key = self._get_env_var("INVENTORY_API_KEY")
        self.api_secret = self._get_env_var("INVENTORY_API_SECRET")
        
        # Request timeout and retry settings
        self.timeout = config.api_timeout_seconds
        self.max_retries = config.api_retry_attempts
        self.retry_delay = config.api_retry_delay_seconds
        
        logger.info(f"Inventory API connector initialized: {self.api_url}")

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

    def get_all_inventory(self) -> Dict[str, Any]:
        """
        Get inventory data for all warehouses.
        
        Returns:
            Dictionary containing inventory data for all warehouses
        """
        logger.info("Retrieving inventory data for all warehouses")
        
        try:
            response = self._make_request("GET", "inventory")
            logger.info(f"Retrieved inventory data for {len(response)} warehouses")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve inventory data: {str(e)}")
            # Return empty dict on failure to avoid breaking the agent
            return {}

    def get_warehouse_inventory(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Get inventory data for a specific warehouse.
        
        Args:
            warehouse_id: ID of the warehouse
            
        Returns:
            Dictionary containing inventory data for the warehouse
        """
        logger.info(f"Retrieving inventory data for warehouse {warehouse_id}")
        
        try:
            response = self._make_request("GET", f"inventory/{warehouse_id}")
            logger.info(f"Retrieved inventory data for warehouse {warehouse_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve inventory data for warehouse {warehouse_id}: {str(e)}")
            # Return empty dict on failure to avoid breaking the agent
            return {}

    def get_warehouse_info(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Get information about a specific warehouse.
        
        Args:
            warehouse_id: ID of the warehouse
            
        Returns:
            Dictionary containing warehouse information
        """
        logger.info(f"Retrieving information for warehouse {warehouse_id}")
        
        try:
            response = self._make_request("GET", f"warehouses/{warehouse_id}")
            logger.info(f"Retrieved information for warehouse {warehouse_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve information for warehouse {warehouse_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "id": warehouse_id,
                "name": f"Warehouse {warehouse_id}",
                "location": "Unknown",
                "capacity": 1000
            }

    def get_item_info(self, item_id: str) -> Dict[str, Any]:
        """
        Get information about a specific inventory item.
        
        Args:
            item_id: ID of the inventory item
            
        Returns:
            Dictionary containing item information
        """
        logger.info(f"Retrieving information for item {item_id}")
        
        try:
            response = self._make_request("GET", f"items/{item_id}")
            logger.info(f"Retrieved information for item {item_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve information for item {item_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "id": item_id,
                "name": f"Item {item_id}",
                "category": "Unknown",
                "unit": "unit"
            }

    def update_inventory_quantity(
        self, warehouse_id: str, item_id: str, quantity: int, reason: str
    ) -> bool:
        """
        Update the quantity of an item in a warehouse.
        
        Args:
            warehouse_id: ID of the warehouse
            item_id: ID of the inventory item
            quantity: New quantity value
            reason: Reason for the update
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(
            f"Updating quantity of item {item_id} in warehouse {warehouse_id} "
            f"to {quantity} units (reason: {reason})"
        )
        
        try:
            data = {
                "quantity": quantity,
                "reason": reason
            }
            
            response = self._make_request(
                "PUT", f"inventory/{warehouse_id}/items/{item_id}", data=data
            )
            
            logger.info(
                f"Successfully updated quantity of item {item_id} "
                f"in warehouse {warehouse_id}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to update quantity of item {item_id} "
                f"in warehouse {warehouse_id}: {str(e)}"
            )
            return False

    def create_inventory_transfer(
        self, source_warehouse: str, destination_warehouse: str, items: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Create an inventory transfer between warehouses.
        
        Args:
            source_warehouse: ID of the source warehouse
            destination_warehouse: ID of the destination warehouse
            items: List of items to transfer, each with id, quantity, and unit
            
        Returns:
            Transfer ID if successful, None otherwise
        """
        logger.info(
            f"Creating inventory transfer from {source_warehouse} to {destination_warehouse} "
            f"for {len(items)} items"
        )
        
        try:
            data = {
                "source_warehouse": source_warehouse,
                "destination_warehouse": destination_warehouse,
                "items": items,
                "requested_by": self.config.agent_name
            }
            
            response = self._make_request("POST", "transfers", data=data)
            
            transfer_id = response.get("transfer_id")
            if transfer_id:
                logger.info(f"Successfully created inventory transfer {transfer_id}")
                return transfer_id
            else:
                logger.error("Failed to create inventory transfer: No transfer ID in response")
                return None
        except Exception as e:
            logger.error(f"Failed to create inventory transfer: {str(e)}")
            return None

    def get_transfer_status(self, transfer_id: str) -> Dict[str, Any]:
        """
        Get the status of an inventory transfer.
        
        Args:
            transfer_id: ID of the transfer
            
        Returns:
            Dictionary containing transfer status information
        """
        logger.info(f"Retrieving status for transfer {transfer_id}")
        
        try:
            response = self._make_request("GET", f"transfers/{transfer_id}")
            logger.info(f"Retrieved status for transfer {transfer_id}: {response.get('status')}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve status for transfer {transfer_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "transfer_id": transfer_id,
                "status": "unknown",
                "created_at": None,
                "completed_at": None
            }

    def cancel_transfer(self, transfer_id: str, reason: str) -> bool:
        """
        Cancel an inventory transfer.
        
        Args:
            transfer_id: ID of the transfer
            reason: Reason for cancellation
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Cancelling transfer {transfer_id} (reason: {reason})")
        
        try:
            data = {
                "reason": reason,
                "cancelled_by": self.config.agent_name
            }
            
            response = self._make_request("POST", f"transfers/{transfer_id}/cancel", data=data)
            
            logger.info(f"Successfully cancelled transfer {transfer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel transfer {transfer_id}: {str(e)}")
            return False
