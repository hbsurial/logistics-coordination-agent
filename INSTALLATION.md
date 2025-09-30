# Installation and Setup Instructions

This document provides detailed instructions for setting up and running the Logistics Coordination Agent.

## Prerequisites

Before installing the agent, ensure you have the following prerequisites:

- Python 3.8 or higher
- Docker and Docker Compose
- PostgreSQL 12 or higher
- Redis 6 or higher
- API credentials for all external systems (inventory, transportation, weather)

## Installation Options

### Option 1: Docker Installation (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/logistics-coordination-agent.git
   cd logistics-coordination-agent
   ```

2. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your specific configuration settings, including API keys.

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

4. Initialize the database:
   ```bash
   docker-compose exec app python -m agent.setup.initialize_db
   ```

5. Verify the installation:
   ```bash
   docker-compose exec app python -m agent.setup.verify_installation
   ```

### Option 2: Manual Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/logistics-coordination-agent.git
   cd logistics-coordination-agent
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit the `.env` file with your specific configuration settings, including API keys.

5. Set up the database:
   ```bash
   python -m agent.setup.initialize_db
   ```

6. Verify the installation:
   ```bash
   python -m agent.setup.verify_installation
   ```

## Configuration

### API Connections

The agent requires connections to several external APIs. Configure these in the `.env` file:

```
# Inventory API Configuration
INVENTORY_API_URL=https://your-inventory-system.com/api
INVENTORY_API_KEY=your_api_key
INVENTORY_API_SECRET=your_api_secret

# Transportation API Configuration
TRANSPORT_API_URL=https://your-transport-system.com/api
TRANSPORT_API_KEY=your_api_key
TRANSPORT_API_SECRET=your_api_secret

# Weather API Configuration
WEATHER_API_URL=https://weather-service.com/api
WEATHER_API_KEY=your_api_key
```

### Database Configuration

Configure the database connection in the `.env` file:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=logistics_agent
DB_USER=postgres
DB_PASSWORD=your_password
```

### Redis Configuration

Configure Redis for caching and message queuing:

```
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
```

### Agent Settings

Configure the agent's behavior:

```
# General Settings
AGENT_NAME=LogisticsCoordinator
LOG_LEVEL=INFO

# Monitoring Intervals (in seconds)
INVENTORY_CHECK_INTERVAL=300
SHIPMENT_CHECK_INTERVAL=120
WEATHER_CHECK_INTERVAL=3600

# Decision Thresholds
REROUTE_DELAY_THRESHOLD=3600  # Reroute if delay > 1 hour
INVENTORY_ALERT_THRESHOLD=0.2  # Alert if inventory < 20% of capacity
```

## Running the Agent

### Starting the Agent

To start the agent:

```bash
# If using Docker
docker-compose up -d

# If installed manually
python -m agent.run
```

### Monitoring the Agent

Monitor the agent's logs:

```bash
# If using Docker
docker-compose logs -f app

# If installed manually
tail -f logs/agent.log
```

### Stopping the Agent

To stop the agent:

```bash
# If using Docker
docker-compose down

# If installed manually
pkill -f "python -m agent.run"
```

## Troubleshooting

### Common Issues

1. **API Connection Failures**
   - Verify API credentials in the `.env` file
   - Check network connectivity to API endpoints
   - Ensure API rate limits haven't been exceeded

2. **Database Connection Issues**
   - Verify database credentials and connection settings
   - Ensure PostgreSQL service is running
   - Check database permissions

3. **Agent Not Making Decisions**
   - Verify decision thresholds in configuration
   - Check if required data is available from APIs
   - Review logs for decision-making process details

### Getting Help

If you encounter issues not covered in this guide:

1. Check the detailed logs in the `logs/` directory
2. Review the [Troubleshooting Guide](docs/troubleshooting.md)
3. Submit an issue on the project's GitHub repository

## Next Steps

After installation, proceed to:

1. [Data Integration Guide](docs/data_integration.md) for connecting your specific data sources
2. [Agent Configuration Guide](docs/agent_configuration.md) for fine-tuning the agent's behavior
3. [User Guide](docs/user_guide.md) for day-to-day operation instructions
