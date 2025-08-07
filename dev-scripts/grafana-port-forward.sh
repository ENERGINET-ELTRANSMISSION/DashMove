#!/bin/bash

# Script to set up port forwarding for both Grafana instances
# and load secrets and URLs into environment variables

echo "Setting up Grafana port forwarding and environment variables..."

# Get Grafana 1 admin password and store in env var
GRAFANA_1_PASSWORD=$(kubectl get secret --namespace grafana-1 grafana-1 -o jsonpath="{.data.admin-password}" | base64 --decode)
export GRAFANA_1_PASSWORD

# Get Grafana 2 admin password and store in env var
GRAFANA_2_PASSWORD=$(kubectl get secret --namespace grafana-2 grafana-2 -o jsonpath="{.data.admin-password}" | base64 --decode)
export GRAFANA_2_PASSWORD

# Set Grafana URLs
export GRAFANA_1_URL="http://localhost:4000"
export GRAFANA_2_URL="http://localhost:4001"

# Set Grafana usernames (same for both)
export GRAFANA_USERNAME="admin"

# Display the environment variables
echo "Environment variables set:"
echo "GRAFANA_USERNAME=$GRAFANA_USERNAME"
echo "GRAFANA_1_PASSWORD=$GRAFANA_1_PASSWORD"
echo "GRAFANA_2_PASSWORD=$GRAFANA_2_PASSWORD"
echo "GRAFANA_1_URL=$GRAFANA_1_URL"
echo "GRAFANA_2_URL=$GRAFANA_2_URL"

echo "\nStarting port forwarding for Grafana instances..."
echo "Access Grafana 1 at: $GRAFANA_1_URL"
echo "Access Grafana 2 at: $GRAFANA_2_URL"

echo "\nTo access Grafana instances:"
echo "1. Grafana 1 - Username: $GRAFANA_USERNAME, Password: $GRAFANA_1_PASSWORD"
echo "2. Grafana 2 - Username: $GRAFANA_USERNAME, Password: $GRAFANA_2_PASSWORD"

echo "\nStarting port forwarding in background..."

# Get pod names
GRAFANA_1_POD=$(kubectl get pods --namespace grafana-1 -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=grafana-1" -o jsonpath="{.items[0].metadata.name}")
GRAFANA_2_POD=$(kubectl get pods --namespace grafana-2 -l "app.kubernetes.io/name=grafana,app.kubernetes.io/instance=grafana-2" -o jsonpath="{.items[0].metadata.name}")

# Start port forwarding for both instances in background
kubectl --namespace grafana-1 port-forward $GRAFANA_1_POD 4000:3000 &
GRAFANA_1_PID=$!

echo "Grafana 1 port forwarding started with PID: $GRAFANA_1_PID"

kubectl --namespace grafana-2 port-forward $GRAFANA_2_POD 4001:3000 &
GRAFANA_2_PID=$!

echo "Grafana 2 port forwarding started with PID: $GRAFANA_2_PID"

echo "\nPort forwarding is now active."
echo "Press Ctrl+C to stop port forwarding."

echo "\nOpening Grafana instances in browser..."
# Open in browser (if xdg-open is available)
if command -v xdg-open &> /dev/null; then
    sleep 2  # Give port forwarding a moment to establish
    xdg-open "$GRAFANA_1_URL" &
    xdg-open "$GRAFANA_2_URL" &
else
    echo "xdg-open not available. Please manually open the URLs in your browser."
fi

# Wait for background processes
wait $GRAFANA_1_PID $GRAFANA_2_PID
