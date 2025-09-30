"""
Weather API connector for the Logistics Coordination Agent.

This module provides the interface to interact with weather data services,
retrieving weather conditions along routes.
"""

import logging
import time
from typing import Dict, List, Any, Optional

import requests
from requests.exceptions import RequestException

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class WeatherAPI:
    """
    Connector for weather data services API.
    
    This class handles all interactions with weather data services,
    retrieving weather conditions that may affect logistics operations.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the Weather API connector.
        
        Args:
            config: Agent configuration settings
        """
        self.config = config
        
        # API connection settings
        self.api_url = self._get_env_var("WEATHER_API_URL")
        self.api_key = self._get_env_var("WEATHER_API_KEY")
        
        # Request timeout and retry settings
        self.timeout = config.api_timeout_seconds
        self.max_retries = config.api_retry_attempts
        self.retry_delay = config.api_retry_delay_seconds
        
        logger.info(f"Weather API connector initialized: {self.api_url}")

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
        
        # Add API key to params
        if params is None:
            params = {}
        params["key"] = self.api_key
        
        headers = {
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

    def get_conditions_along_route(self, route_id: str) -> Dict[str, Any]:
        """
        Get weather conditions along a specific route.
        
        Args:
            route_id: ID of the route
            
        Returns:
            Dictionary containing weather condition data along the route
        """
        logger.info(f"Retrieving weather conditions along route {route_id}")
        
        try:
            params = {
                "route_id": route_id,
                "include_forecast": "true",
                "resolution": "medium"  # medium resolution for balance of detail and performance
            }
            
            response = self._make_request("GET", "route-weather", params=params)
            logger.info(f"Retrieved weather conditions along route {route_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve weather conditions along route {route_id}: {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "route_id": route_id,
                "conditions": "unknown",
                "severe_weather": False,
                "visibility_meters": 10000,  # Default to good visibility
                "wind_speed_kmh": 0,
                "precipitation_mm": 0,
                "temperature_c": 20,
                "last_updated": None
            }

    def get_location_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get current weather conditions at a specific location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            Dictionary containing weather condition data at the location
        """
        logger.info(f"Retrieving weather conditions at location ({latitude}, {longitude})")
        
        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "include_forecast": "true"
            }
            
            response = self._make_request("GET", "current", params=params)
            logger.info(f"Retrieved weather conditions at location ({latitude}, {longitude})")
            return response
        except Exception as e:
            logger.error(f"Failed to retrieve weather at location ({latitude}, {longitude}): {str(e)}")
            # Return minimal info on failure to avoid breaking the agent
            return {
                "location": f"{latitude},{longitude}",
                "conditions": "unknown",
                "severe_weather": False,
                "visibility_meters": 10000,  # Default to good visibility
                "wind_speed_kmh": 0,
                "precipitation_mm": 0,
                "temperature_c": 20,
                "last_updated": None
            }

    def get_weather_alerts(self, region: str) -> List[Dict[str, Any]]:
        """
        Get active weather alerts for a specific region.
        
        Args:
            region: Region code or name
            
        Returns:
            List of active weather alerts for the region
        """
        logger.info(f"Retrieving weather alerts for region {region}")
        
        try:
            params = {
                "region": region
            }
            
            response = self._make_request("GET", "alerts", params=params)
            alerts = response.get("alerts", [])
            logger.info(f"Retrieved {len(alerts)} weather alerts for region {region}")
            return alerts
        except Exception as e:
            logger.error(f"Failed to retrieve weather alerts for region {region}: {str(e)}")
            # Return empty list on failure to avoid breaking the agent
            return []

    def get_weather_forecast(
        self, latitude: float, longitude: float, days: int = 5
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a specific location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            days: Number of days to forecast (default: 5)
            
        Returns:
            Dictionary containing weather forecast data
        """
        logger.info(f"Retrieving {days}-day weather forecast for location ({latitude}, {longitude})")
        
        try:
            params = {
                "lat": latitude,
                "lon": longitude,
                "days": days
            }
            
            response = self._make_request("GET", "forecast", params=params)
            logger.info(f"Retrieved {days}-day forecast for location ({latitude}, {longitude})")
            return response
        except Exception as e:
            logger.error(
                f"Failed to retrieve forecast for location ({latitude}, {longitude}): {str(e)}"
            )
            # Return minimal info on failure to avoid breaking the agent
            return {
                "location": f"{latitude},{longitude}",
                "forecast_days": days,
                "daily_forecasts": []
            }
