#!/bin/bash

# Development Environment Setup Script
# Uses kind (Kubernetes in Docker) and helm for local development

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLUSTER_NAME="kind"
CONTEXT_NAME="kind-kind"
NAMESPACE="dashmove-dev"
RELEASE_NAME="dashmove"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command_exists kind; then
        print_error "kind is not installed. Please install kind first."
        exit 1
    fi
    
    if ! command_exists kubectl; then
        print_error "kubectl is not installed. Please install kubectl first."
        exit 1
    fi
    
    if ! command_exists helm; then
        print_error "helm is not installed. Please install helm first."
        exit 1
    fi
    
    if ! command_exists docker; then
        print_error "docker is not installed. Please install docker first."
        exit 1
    fi
    
    print_success "All prerequisites are available"
}

# Create kind cluster
create_cluster() {
    print_status "Creating kind cluster..."
    
    # Check if cluster already exists
    if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        print_warning "Cluster '${CLUSTER_NAME}' already exists. Skipping creation."
        return 0
    fi
    
    # Create the cluster
    kind create cluster --name "${CLUSTER_NAME}"
    
    # Verify cluster is running
    kubectl cluster-info --context "${CONTEXT_NAME}" >/dev/null
    print_success "Kind cluster created successfully"
}

# Setup helm repositories
setup_helm_repos() {
    print_status "Setting up helm repositories..."
    
    # Add common repositories
    helm repo add grafana https://grafana.github.io/helm-charts
    
    # Update repositories
    helm repo update
    
    print_success "Helm repositories configured"
}

# Create namespaces
create_namespaces() {
    print_status "Creating namespaces..."
    
    # Create grafana namespaces for monitoring
    kubectl --context "${CONTEXT_NAME}" create namespace grafana-1 --dry-run=client -o yaml | kubectl --context "${CONTEXT_NAME}" apply -f -
    kubectl --context "${CONTEXT_NAME}" create namespace grafana-2 --dry-run=client -o yaml | kubectl --context "${CONTEXT_NAME}" apply -f -
    
    print_success "Namespaces created"
}

# Deploy applications
deploy_applications() {
    print_status "Deploying Grafana instances..."
    
    # Deploy Grafana instances
    helm --kube-context "${CONTEXT_NAME}" upgrade --install grafana-1 grafana/grafana \
        --namespace grafana-1 \
        --create-namespace
    
    helm --kube-context "${CONTEXT_NAME}" upgrade --install grafana-2 grafana/grafana \
        --namespace grafana-2 \
        --create-namespace
    
    print_success "Grafana instances deployed"
}

# Wait for deployments to be ready
wait_for_deployments() {
    print_status "Waiting for deployments to be ready..."
    
    # Wait for Grafana deployments
    kubectl --context "${CONTEXT_NAME}" wait --for=condition=available --timeout=300s deployment --all -n grafana-1
    kubectl --context "${CONTEXT_NAME}" wait --for=condition=available --timeout=300s deployment --all -n grafana-2
    
    print_success "Deployments are ready"
}

# Display cluster information
display_info() {
    print_status "Development environment information:"
    echo
    echo "Cluster: ${CLUSTER_NAME}"
    echo "Context: ${CONTEXT_NAME}"
    echo "Grafana namespaces: grafana-1, grafana-2"
    echo
    
    print_status "Getting cluster info..."
    kubectl cluster-info --context "${CONTEXT_NAME}"
    echo
    
    print_status "Available nodes:"
    kubectl --context "${CONTEXT_NAME}" get nodes
    echo
    
    print_status "Grafana deployments:"
    kubectl --context "${CONTEXT_NAME}" get deployments -n grafana-1
    kubectl --context "${CONTEXT_NAME}" get deployments -n grafana-2
    echo
    
    print_status "Grafana services:"
    kubectl --context "${CONTEXT_NAME}" get services -n grafana-1
    kubectl --context "${CONTEXT_NAME}" get services -n grafana-2
    echo
    
    print_status "Grafana admin passwords:"
    echo "Grafana-1: $(kubectl --context "${CONTEXT_NAME}" get secret --namespace grafana-1 grafana-1 -o jsonpath="{.data.admin-password}" | base64 --decode 2>/dev/null || echo "Not available yet")"
    echo "Grafana-2: $(kubectl --context "${CONTEXT_NAME}" get secret --namespace grafana-2 grafana-2 -o jsonpath="{.data.admin-password}" | base64 --decode 2>/dev/null || echo "Not available yet")"
    echo
    
    print_success "Development environment is ready!"
    echo
    print_status "For Grafana access:"
    echo "kubectl --context ${CONTEXT_NAME} port-forward -n grafana-1 svc/grafana-1 4000:80"
    echo "kubectl --context ${CONTEXT_NAME} port-forward -n grafana-2 svc/grafana-2 4001:80"
}

# Main execution
main() {
    print_status "Starting development environment setup..."
    echo
    
    check_prerequisites
    create_cluster
    setup_helm_repos
    create_namespaces
    deploy_applications
    wait_for_deployments
    display_info
}

# Run main function
main "$@"
