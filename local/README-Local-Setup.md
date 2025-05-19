# Suna AI - Local Development Setup

This guide provides comprehensive instructions for setting up and running Suna AI completely locally, with only the LLM API as an external dependency. By following these steps, you'll have a fully functional local development environment with Daytona, Supabase, Redis, RabbitMQ, and all other services running locally.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Instructions](#detailed-setup-instructions)
  - [1. Setting Up Daytona](#1-setting-up-daytona)
  - [2. Starting Daytona](#2-starting-daytona)
  - [3. Setting Up Docker Services](#3-setting-up-docker-services)
  - [4. Starting Suna AI](#4-starting-suna-ai)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Overview

Suna AI can be run entirely locally, eliminating the need for external services except for the LLM API (OpenAI/Anthropic). This setup includes:

- **Local Daytona** - Secure sandbox for agent execution
- **Local Supabase** - Database, authentication, and storage
- **Local Redis** - Caching and session management
- **Local RabbitMQ** - Message queue
- **Local Backend & Frontend** - Suna AI services

## Prerequisites

- Docker and Docker Compose
- Git
- Bash shell (Linux/macOS) or Git Bash/WSL (Windows)
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space
- API keys for LLM providers (Anthropic/OpenAI)

## Quick Start

For those who want to get started quickly, we provide automated setup scripts:

```bash
# 1. Clone the repository
git clone https://github.com/kortix-ai/suna.git
cd suna

# 2. Set up Daytona
chmod +x merged_setup_daytona_local.sh
./merged_setup_daytona_local.sh

# 3. Start Daytona
source ~/.bashrc  # or ~/.zshrc if using zsh
daytona-start

# 4. Start Suna AI services
chmod +x start-suna-local.sh
./start-suna-local.sh

# To stop all services when done
./stop-suna-local.sh
```

## Detailed Setup Instructions

### 1. Setting Up Daytona

Daytona provides the secure sandbox environment for Suna AI's agent execution. Our enhanced setup script automates the installation process:

```bash
# Make the script executable
chmod +x merged_setup_daytona_local.sh

# Run the setup script
./merged_setup_daytona_local.sh
```

This script will:
- Download and install the Daytona CLI
- Create necessary directories and configuration files
- Set up shell aliases for convenient usage
- Generate default configuration and create backups
- Prepare the environment for starting Daytona
- **Automatically register the Suna AgentDocker image with Daytona**

After running the setup script, load the new aliases:
```bash
source ~/.bashrc  # or ~/.zshrc if using zsh
```

### 2. Starting Daytona

Once Daytona is set up, you can start it using our enhanced startup script:

```bash
# Using the alias (if you sourced your shell config)
daytona-start

# Or directly
./enhanced_start_daytona_local.sh
```

This script will:
- Start the FRP (Fast Reverse Proxy) server in a Docker container
- Configure Daytona to use the local FRP server
- Start the Daytona daemon
- Verify that all components are running correctly

You can verify Daytona is running by accessing the dashboard at http://localhost:3986

### 3. Setting Up Docker Services

Suna AI requires several services that run in Docker containers. We provide a comprehensive `docker-compose-local.yml` file that includes all necessary services:

```bash
# Navigate to the Suna AI directory
cd /path/to/suna

# Review the docker-compose-local.yml file
cat docker-compose-local.yml
```

The Docker Compose file includes:
- Supabase (PostgreSQL database and REST API)
- Redis for caching
- RabbitMQ for message queue
- Backend service (optional)
- Frontend service (optional)

#### Database Schema Initialization

The docker-compose-local.yml file is configured to automatically initialize the database schema:

```yaml
supabase-db:
  volumes:
    - supabase-db-data:/var/lib/postgresql/data
    - ./suna/backend/supabase/migrations:/docker-entrypoint-initdb.d
```

By mounting the migrations directory to `/docker-entrypoint-initdb.d`, PostgreSQL will automatically execute all SQL files in that directory during container initialization. This means you don't need to manually run any SQL scripts to set up the database schema.

#### Environment Configuration

Before starting the services, configure the environment variables:

1. **Backend Configuration**:
   Create or update the `.env` file in the `suna/backend` directory:

   ```
   # Environment Mode
   ENV_MODE=local

   # DATABASE - Local Supabase
   SUPABASE_URL=http://localhost:54321
   SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU

   # Local Redis
   REDIS_HOST=redis
   REDIS_PORT=6379
   REDIS_PASSWORD=
   REDIS_SSL=false

   # Local RabbitMQ
   RABBITMQ_HOST=rabbitmq
   RABBITMQ_PORT=5672

   # LLM Providers (still external)
   ANTHROPIC_API_KEY=your_anthropic_key_here
   OPENAI_API_KEY=your_openai_key_here
   MODEL_TO_USE=anthropic/claude-3-7-sonnet-latest

   # Local Daytona configuration
   DAYTONA_SERVER_URL=http://host.docker.internal:3986/api
   DAYTONA_TARGET=local

   # Optional APIs (can be left empty for fully local setup)
   TAVILY_API_KEY=
   FIRECRAWL_API_KEY=
   RAPID_API_KEY=
   ```

2. **Frontend Configuration**:
   Create or update the `.env.local` file in the `suna/frontend` directory:

   ```
   # API URL (pointing to local backend)
   NEXT_PUBLIC_API_URL=http://localhost:8000

   # Local Supabase configuration
   NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
   NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

   # Environment mode
   NEXT_PUBLIC_ENV_MODE=local
   ```

### 4. Starting Suna AI

We provide a comprehensive startup script that handles starting all services in the correct order:

```bash
# Make the script executable
chmod +x start-suna-local.sh

# Run the startup script
./start-suna-local.sh
```

This script will:
1. Start Daytona using the enhanced_start_daytona_local.sh script
2. Launch Docker services (Supabase, Redis, RabbitMQ) using docker-compose-local.yml
3. Start the Suna AI backend service
4. Start the Suna AI frontend service
5. Provide URLs for accessing all services

Once all services are running, you can access:
- Suna AI Frontend: http://localhost:3000
- Suna AI Backend API: http://localhost:8000
- Supabase Studio: http://localhost:54321
- Daytona Dashboard: http://localhost:3986

To stop all services when you're done:
```bash
./stop-suna-local.sh
```

## Configuration

### Daytona Configuration

The Daytona configuration is stored in:
- macOS: `~/Library/Application Support/daytona/server/config.json`
- Linux: `~/.config/daytona/server/config.json`

Our setup scripts automatically configure Daytona for local development, but you can manually modify these files if needed.

### AgentDocker Image

The setup script automatically registers the Suna AgentDocker image with Daytona:
- Image name: `kortix/suna:0.1.2`
- Entrypoint: `/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf`

If you need to register it manually for any reason:
```bash
daytona image add --name "kortix/suna:0.1.2" --entrypoint "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"
```

### Docker Compose Configuration

The `docker-compose-local.yml` file contains all the configuration for Docker services. Key aspects you might want to customize:

- **Ports**: If you have port conflicts, you can change the exposed ports
- **Volumes**: Data persistence locations can be customized
- **Environment Variables**: Service-specific settings can be adjusted

### Environment Variables

The most important environment variables for local development:

- `ENV_MODE=local`: Ensures Suna AI runs in local mode, bypassing Stripe and other external services
- `DAYTONA_TARGET=local`: Configures Daytona for local execution
- `DAYTONA_SERVER_URL`: Points to your local Daytona instance
- `SUPABASE_URL` and `SUPABASE_ANON_KEY`: Connect to your local Supabase instance

## Troubleshooting

### Daytona Issues

If you encounter issues with Daytona:

1. Check if the FRP container is running: `docker ps | grep frps`
2. Verify Daytona is running: `daytona server status`
3. Check Daytona logs: `daytona server logs`
4. Restart Daytona: `daytona server stop && daytona server -y`
5. Ensure Docker is running and accessible

### AgentDocker Image Issues

If you encounter issues with the AgentDocker image:

1. Verify the image is registered: `daytona image list`
2. If not registered, register it manually: `daytona image add --name "kortix/suna:0.1.2" --entrypoint "/usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf"`
3. Check if Docker can pull the image: `docker pull kortix/suna:0.1.2`

### Docker Services Issues

If Docker services aren't starting:

1. Check Docker Compose logs: `docker-compose -f docker-compose-local.yml logs`
2. Ensure ports are not in use by other services
3. Verify Docker has sufficient resources allocated
4. Try restarting Docker: `docker restart`

### Database Issues

If you encounter database schema issues:

1. The schema should be automatically created during the first startup of the Supabase container
2. If you need to reset the database: `docker-compose -f docker-compose-local.yml down -v` and then start again
3. To manually apply migrations: `cat suna/backend/supabase/migrations/*.sql | docker exec -i $(docker-compose -f docker-compose-local.yml ps -q supabase-db) psql -U postgres`

### Connection Issues

If services can't communicate:

1. For Docker containers connecting to Daytona, ensure `host.docker.internal` resolves correctly
2. Check that hostnames and ports are correctly configured
3. Verify no firewall is blocking the connections
4. Ensure all services are on the same Docker network

### Common Errors

1. **"Connection refused" errors**: Usually indicate a service isn't running or a port conflict
2. **"Authentication failed" errors**: Check your API keys and Supabase configuration
3. **"Resource limit" errors**: Increase Docker's allocated resources
4. **"File not found" errors**: Verify paths in your configuration files

## Maintenance

### Updating Services

To update the services:

1. Pull the latest code: `git pull`
2. Pull the latest Docker images: `docker-compose -f docker-compose-local.yml pull`
3. Restart the services: `./start-suna-local.sh`

### Database Management

For Supabase database management:

1. Access Supabase Studio at http://localhost:54321
2. Default credentials: email `supabase`, password `this_password_is_insecure_and_should_be_updated`
3. Use the Studio interface to manage tables, run SQL, and configure authentication

### Logs and Monitoring

- Daytona logs: `daytona server logs`
- Docker service logs: `docker-compose -f docker-compose-local.yml logs [service_name]`
- Suna AI backend logs: Check the `logs/backend.log` file
- Suna AI frontend logs: Check the `logs/frontend.log` file

### Cleaning Up

To completely remove the local setup:

1. Stop all services: `./stop-suna-local.sh`
2. Remove Docker volumes: `docker-compose -f docker-compose-local.yml down -v`
3. Uninstall Daytona: `daytona uninstall`
