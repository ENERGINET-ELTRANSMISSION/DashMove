#!/bin/bash

# Development Environment Manager
# Wrapper script for easy setup and teardown of development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    echo "Development Environment Manager"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  up, setup     - Setup the development environment"
    echo "  down, teardown - Teardown the development environment"
    echo "  status        - Show current environment status"
    echo "  help          - Show this help message"
    echo
    echo "Options:"
    echo "  --force       - Skip confirmation prompts (for teardown)"
    echo
    echo "Examples:"
    echo "  $0 up         - Setup development environment"
    echo "  $0 down       - Teardown development environment (with confirmation)"
    echo "  $0 down --force - Teardown development environment (no confirmation)"
    echo "  $0 status     - Check current status"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_status() {
    print_status "Development Environment Status"
    echo
    
    # Check if kind is available
    if ! command -v kind >/dev/null 2>&1; then
        print_error "kind is not installed"
        return 1
    fi
    
    # Check for kind clusters
    print_status "Kind clusters:"
    if kind get clusters 2>/dev/null | grep -q .; then
        kind get clusters
    else
        echo "No kind clusters found"
    fi
    echo
    
    # Check kubectl contexts
    print_status "Kubectl contexts:"
    kubectl config get-contexts | grep -E "(CURRENT|kind)" || echo "No kind contexts found"
    echo
    
    # If kind cluster exists, show more details
    if kind get clusters 2>/dev/null | grep -q "^kind$"; then
        print_status "Cluster details:"
        kubectl cluster-info --context kind-kind 2>/dev/null || echo "Cluster not accessible"
        echo
        
        print_status "Nodes:"
        kubectl --context kind-kind get nodes 2>/dev/null || echo "Cannot access nodes"
        echo
        
        print_status "Namespaces:"
        kubectl --context kind-kind get namespaces 2>/dev/null | grep -E "grafana" || echo "No grafana namespaces found"
        echo
        
        # Show Grafana credentials if namespaces exist
        if kubectl --context kind-kind get namespace grafana-1 >/dev/null 2>&1 && kubectl --context kind-kind get namespace grafana-2 >/dev/null 2>&1; then
            print_status "Grafana Admin Credentials:"
            echo "Username: admin"
            echo "Grafana-1 Password: $(kubectl --context kind-kind get secret --namespace grafana-1 grafana-1 -o jsonpath="{.data.admin-password}" 2>/dev/null | base64 --decode || echo "Not available")"
            echo "Grafana-2 Password: $(kubectl --context kind-kind get secret --namespace grafana-2 grafana-2 -o jsonpath="{.data.admin-password}" 2>/dev/null | base64 --decode || echo "Not available")"
            echo
            
            print_status "Access URLs (with port-forwarding):"
            echo "Grafana-1: http://localhost:4000 (kubectl --context kind-kind port-forward -n grafana-1 svc/grafana-1 4000:80)"
            echo "Grafana-2: http://localhost:4001 (kubectl --context kind-kind port-forward -n grafana-2 svc/grafana-2 4001:80)"
        fi
    fi
}

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$1" in
    "up"|"setup")
        print_status "Starting development environment setup..."
        exec "${SCRIPT_DIR}/dev-setup.sh"
        ;;
    "down"|"teardown")
        print_status "Starting development environment teardown..."
        exec "${SCRIPT_DIR}/dev-teardown.sh" "$2"
        ;;
    "status")
        show_status
        ;;
    "help"|"--help"|"-h")
        print_usage
        ;;
    "")
        print_error "No command specified"
        echo
        print_usage
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        echo
        print_usage
        exit 1
        ;;
esac
