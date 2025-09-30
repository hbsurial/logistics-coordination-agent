"""
Configuration settings for the Logistics Coordination Agent.

This module defines the configuration structure and default values
for the agent's behavior and decision-making parameters.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AgentConfig:
    """Configuration settings for the Logistics Coordination Agent."""
    
    # General settings
    agent_name: str = "LogisticsCoordinator"
    log_level: str = "INFO"
    
    # Monitoring intervals (in seconds)
    main_loop_interval: int = 60
    inventory_check_interval: int = 300  # 5 minutes
    shipment_check_interval: int = 120   # 2 minutes
    weather_check_interval: int = 3600   # 1 hour
    
    # Inventory thresholds
    inventory_alert_threshold: float = 0.2  # Alert if inventory < 20% of capacity
    inventory_target_level: float = 0.7     # Target inventory level (70% of capacity)
    
    # Shipment thresholds
    reroute_delay_threshold_minutes: int = 60  # Reroute if delay > 60 minutes
    
    # Weather and road condition thresholds
    min_visibility_meters: int = 200      # Minimum safe visibility
    max_wind_speed_kmh: int = 80          # Maximum safe wind speed
    
    # Decision weights
    decision_weights: Dict[str, float] = field(default_factory=lambda: {
        "time": 0.4,       # Weight for time-based factors
        "cost": 0.3,       # Weight for cost-based factors
        "reliability": 0.2,  # Weight for reliability factors
        "sustainability": 0.1  # Weight for sustainability factors
    })
    
    # Notification settings
    notification_channels: Dict[str, bool] = field(default_factory=lambda: {
        "email": True,
        "sms": True,
        "dashboard": True,
        "api_webhook": False
    })
    
    # API connection settings
    api_timeout_seconds: int = 30
    api_retry_attempts: int = 3
    api_retry_delay_seconds: int = 5
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """
        Create configuration from environment variables.
        
        Returns:
            AgentConfig object with values from environment variables
        """
        config = cls()
        
        # General settings
        if os.getenv("AGENT_NAME"):
            config.agent_name = os.getenv("AGENT_NAME")
        
        if os.getenv("LOG_LEVEL"):
            config.log_level = os.getenv("LOG_LEVEL")
        
        # Monitoring intervals
        if os.getenv("MAIN_LOOP_INTERVAL"):
            config.main_loop_interval = int(os.getenv("MAIN_LOOP_INTERVAL"))
        
        if os.getenv("INVENTORY_CHECK_INTERVAL"):
            config.inventory_check_interval = int(os.getenv("INVENTORY_CHECK_INTERVAL"))
        
        if os.getenv("SHIPMENT_CHECK_INTERVAL"):
            config.shipment_check_interval = int(os.getenv("SHIPMENT_CHECK_INTERVAL"))
        
        if os.getenv("WEATHER_CHECK_INTERVAL"):
            config.weather_check_interval = int(os.getenv("WEATHER_CHECK_INTERVAL"))
        
        # Inventory thresholds
        if os.getenv("INVENTORY_ALERT_THRESHOLD"):
            config.inventory_alert_threshold = float(os.getenv("INVENTORY_ALERT_THRESHOLD"))
        
        if os.getenv("INVENTORY_TARGET_LEVEL"):
            config.inventory_target_level = float(os.getenv("INVENTORY_TARGET_LEVEL"))
        
        # Shipment thresholds
        if os.getenv("REROUTE_DELAY_THRESHOLD_MINUTES"):
            config.reroute_delay_threshold_minutes = int(os.getenv("REROUTE_DELAY_THRESHOLD_MINUTES"))
        
        # Weather and road condition thresholds
        if os.getenv("MIN_VISIBILITY_METERS"):
            config.min_visibility_meters = int(os.getenv("MIN_VISIBILITY_METERS"))
        
        if os.getenv("MAX_WIND_SPEED_KMH"):
            config.max_wind_speed_kmh = int(os.getenv("MAX_WIND_SPEED_KMH"))
        
        # Decision weights
        for weight_name in ["TIME_WEIGHT", "COST_WEIGHT", "RELIABILITY_WEIGHT", "SUSTAINABILITY_WEIGHT"]:
            env_var = f"DECISION_{weight_name}"
            if os.getenv(env_var):
                weight_key = weight_name.lower().replace("_weight", "")
                config.decision_weights[weight_key] = float(os.getenv(env_var))
        
        # Notification settings
        for channel in ["EMAIL", "SMS", "DASHBOARD", "API_WEBHOOK"]:
            env_var = f"NOTIFY_{channel}"
            if os.getenv(env_var):
                channel_key = channel.lower()
                config.notification_channels[channel_key] = os.getenv(env_var).lower() == "true"
        
        # API connection settings
        if os.getenv("API_TIMEOUT_SECONDS"):
            config.api_timeout_seconds = int(os.getenv("API_TIMEOUT_SECONDS"))
        
        if os.getenv("API_RETRY_ATTEMPTS"):
            config.api_retry_attempts = int(os.getenv("API_RETRY_ATTEMPTS"))
        
        if os.getenv("API_RETRY_DELAY_SECONDS"):
            config.api_retry_delay_seconds = int(os.getenv("API_RETRY_DELAY_SECONDS"))
        
        return config


# Default configuration instance
default_config = AgentConfig()


def get_config() -> AgentConfig:
    """
    Get the agent configuration, using environment variables if available.
    
    Returns:
        AgentConfig object with appropriate settings
    """
    return AgentConfig.from_env()
