#!/bin/bash
set -e

echo "--- Ensuring log files exist... ---"
touch chat_history.csv
touch feedback_log.csv
touch activity_log.csv

echo "--- Tearing down old container (if it exists)... ---"
# This command stops and removes the containers defined in the docker-compose.yml file
docker-compose down

echo "--- Starting new deployment with Docker Compose ---"
# This command builds the new image and starts the new container
docker-compose up --build -d

echo "--- Deployment successful! ---"