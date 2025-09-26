#!/bin/bash
set -e

# Create the environment file for Docker Compose to use
grep 'GOOGLE_API_KEY' .env > docker.env

echo "--- Tearing down old container (if it exists)... ---"
# This command stops and removes the containers defined in the docker-compose.yml file
docker-compose down

echo "--- Starting new deployment with Docker Compose ---"
# This command builds the new image and starts the new container
docker-compose up --build -d

echo "--- Deployment successful! ---"