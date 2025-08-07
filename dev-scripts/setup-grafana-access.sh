#!/bin/bash

# Script to set up Grafana access tokens for both instances
# This script assumes port forwarding is already set up via grafana-port-forward.sh

echo "Setting up Grafana access tokens for both instances..."

# Load environment variables if the port-forward script has been run
if [ -z "$GRAFANA_1_PASSWORD" ] || [ -z "$GRAFANA_2_PASSWORD" ]; then
    echo "Environment variables not found. Loading from Kubernetes secrets..."
    # Get Grafana 1 admin password
    GRAFANA_1_PASSWORD=$(kubectl get secret --namespace grafana-1 grafana-1 -o jsonpath="{.data.admin-password}" | base64 --decode)
    # Get Grafana 2 admin password
    GRAFANA_2_PASSWORD=$(kubectl get secret --namespace grafana-2 grafana-2 -o jsonpath="{.data.admin-password}" | base64 --decode)
    # Set Grafana URLs
    GRAFANA_1_URL="http://localhost:4000"
    GRAFANA_2_URL="http://localhost:4001"
    # Set Grafana username
    GRAFANA_USERNAME="admin"
fi

# Display current settings
echo "Using settings:"
echo "GRAFANA_USERNAME=$GRAFANA_USERNAME"
echo "GRAFANA_1_URL=$GRAFANA_1_URL"
echo "GRAFANA_2_URL=$GRAFANA_2_URL"

# Test connectivity to both instances
echo ""
echo "Testing connectivity to Grafana instances..."
curl -s -o /dev/null -w "Grafana 1: %{http_code}\n" $GRAFANA_1_URL/api/health
curl -s -o /dev/null -w "Grafana 2: %{http_code}\n" $GRAFANA_2_URL/api/health

# Function to test if an API key is valid
test_api_key() {
    local GRAFANA_URL=$1
    local API_KEY=$2
    
    if [ -z "$API_KEY" ]; then
        echo "API key is empty"
        return 1
    fi
    
    RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" \
        "$GRAFANA_URL/api/user" 2>/dev/null)
    
    if echo "$RESPONSE" | grep -q "login"; then
        return 0
    else
        return 1
    fi
}

# Function to delete a service account by name
delete_service_account() {
    local GRAFANA_URL=$1
    local USERNAME=$2
    local PASSWORD=$3
    local SA_NAME=$4
    
    SEARCH_RESPONSE=$(curl -s -H "Accept: application/json" \
        -u "$USERNAME:$PASSWORD" \
        "$GRAFANA_URL/api/serviceaccounts/search?query=$SA_NAME")
    
    # Try to extract SA ID
    SA_ID=$(echo "$SEARCH_RESPONSE" | jq -r ".serviceAccounts[] | select(.name==\"$SA_NAME\") | .id" 2>/dev/null)
    
    if [ -n "$SA_ID" ] && [ "$SA_ID" != "null" ]; then
        DELETE_RESPONSE=$(curl -s -X DELETE -H "Accept: application/json" \
            -u "$USERNAME:$PASSWORD" \
            "$GRAFANA_URL/api/serviceaccounts/$SA_ID")
        return 0
    else
        return 0
    fi
}

# Function to create a new service account and token
create_service_account_and_token() {
    local GRAFANA_URL=$1
    local USERNAME=$2
    local PASSWORD=$3
    local SA_NAME=$4
    
    # Create new service account
    CREATE_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
        -u "$USERNAME:$PASSWORD" \
        -d '{"name":"'$SA_NAME'", "role": "Admin"}' \
        "$GRAFANA_URL/api/serviceaccounts")
    
    # Extract new SA ID
    NEW_SA_ID=$(echo "$CREATE_RESPONSE" | jq -r '.id' 2>/dev/null)
    
    if [ -n "$NEW_SA_ID" ] && [ "$NEW_SA_ID" != "null" ] && [ "$NEW_SA_ID" != "" ]; then
        # Create service account token
        TOKEN_RESPONSE=$(curl -s -X POST -H "Content-Type: application/json" -H "Accept: application/json" \
            -u "$USERNAME:$PASSWORD" \
            -d '{"name":"'$SA_NAME'-token-$(date +%s)", "secondsToLive": 86400}' \
            "$GRAFANA_URL/api/serviceaccounts/$NEW_SA_ID/tokens")
        
        # Extract token
        API_KEY=$(echo "$TOKEN_RESPONSE" | jq -r '.key' 2>/dev/null)
        
        if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ] && [ "$API_KEY" != "" ]; then
            echo "$API_KEY"
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# Load existing keys from file if it exists
if [ -f "grafana-api-keys.env" ]; then
    source grafana-api-keys.env
fi

# Test Grafana 1 API key
GRAFANA_1_API_KEY_VALID=0
if test_api_key "$GRAFANA_1_URL" "$GRAFANA_1_API_KEY"; then
    GRAFANA_1_API_KEY_VALID=1
else
    # Delete existing service account if it exists
    delete_service_account "$GRAFANA_1_URL" "$GRAFANA_USERNAME" "$GRAFANA_1_PASSWORD" "dash-move-sa-1"
    # Create new service account and token
    NEW_KEY=$(create_service_account_and_token "$GRAFANA_1_URL" "$GRAFANA_USERNAME" "$GRAFANA_1_PASSWORD" "dash-move-sa-1" 2>/dev/null)
    if [ $? -eq 0 ]; then
        GRAFANA_1_API_KEY="$NEW_KEY"
        GRAFANA_1_API_KEY_VALID=1
    else
        GRAFANA_1_API_KEY_VALID=0
    fi
fi

# Test Grafana 2 API key
GRAFANA_2_API_KEY_VALID=0
if test_api_key "$GRAFANA_2_URL" "$GRAFANA_2_API_KEY"; then
    GRAFANA_2_API_KEY_VALID=1
else
    # Delete existing service account if it exists
    delete_service_account "$GRAFANA_2_URL" "$GRAFANA_USERNAME" "$GRAFANA_2_PASSWORD" "dash-move-sa-2"
    # Create new service account and token
    NEW_KEY=$(create_service_account_and_token "$GRAFANA_2_URL" "$GRAFANA_USERNAME" "$GRAFANA_2_PASSWORD" "dash-move-sa-2" 2>/dev/null)
    if [ $? -eq 0 ]; then
        GRAFANA_2_API_KEY="$NEW_KEY"
        GRAFANA_2_API_KEY_VALID=1
    else
        GRAFANA_2_API_KEY_VALID=0
    fi
fi

# Save API keys to a file for later use
cat > grafana-api-keys.env << EOF
# Grafana Service Account Tokens
GRAFANA_USERNAME=$GRAFANA_USERNAME
GRAFANA_1_URL=$GRAFANA_1_URL
GRAFANA_2_URL=$GRAFANA_2_URL
GRAFANA_1_API_KEY=$GRAFANA_1_API_KEY
GRAFANA_2_API_KEY=$GRAFANA_2_API_KEY
EOF

echo "Service account tokens have been saved to grafana-api-keys.env"

echo ""
echo "=== Final Status ==="
if [ $GRAFANA_1_API_KEY_VALID -eq 1 ]; then
    echo "✓ Grafana 1 API key is ready"
else
    echo "✗ Grafana 1 API key is not available"
fi

if [ $GRAFANA_2_API_KEY_VALID -eq 1 ]; then
    echo "✓ Grafana 2 API key is ready"
else
    echo "✗ Grafana 2 API key is not available"
fi

echo ""
echo "To use with dash-move.py, you can source this file:"
echo "  source grafana-api-keys.env"
echo ""
echo "Then use the service account tokens with dash-move.py like this:"
echo "  ./dash-move.py import --location <location> --secret \$GRAFANA_1_API_KEY --url \$GRAFANA_1_URL"
echo "  ./dash-move.py import --location <location> --secret \$GRAFANA_2_API_KEY --url \$GRAFANA_2_URL"
