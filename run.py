#!/usr/bin/env python3
"""
Main entry point for the Logistics Coordination Agent.

This script initializes and runs the agent, setting up logging
and handling command line arguments.
"""

import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from agent.config import AgentConfig, get_config
from agent.core import LogisticsAgent
from connectors.inventory_api import InventoryAPI
from connectors.transport_api import TransportAPI
from connectors.weather_api import WeatherAPI


def setup_logging(log_level: str, log_file: str = None) -> None:
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
    """
    # Convert string log level to numeric value
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    # Configure logging
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    handlers.append(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers
    )


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Logistics Coordination Agent")
    
    parser.add_argument(
        "--config",
        help="Path to configuration file",
        default=None
    )
    
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO"
    )
    
    parser.add_argument(
        "--log-file",
        help="Path to log file",
        default="logs/agent.log"
    )
    
    return parser.parse_args()


def main() -> None:
    """
    Main entry point for the agent.
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Set up logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Logistics Coordination Agent")
        
        # Load configuration
        config = get_config()
        logger.info(f"Loaded configuration for agent: {config.agent_name}")
        
        # Initialize API connectors
        inventory_api = InventoryAPI(config)
        transport_api = TransportAPI(config)
        weather_api = WeatherAPI(config)
        
        # Initialize agent
        agent = LogisticsAgent(
            config=config,
            inventory_api=inventory_api,
            transport_api=transport_api,
            weather_api=weather_api
        )
        
        # Run agent
        agent.run()
        
    except KeyboardInterrupt:
        logger.info("Agent stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Agent failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
