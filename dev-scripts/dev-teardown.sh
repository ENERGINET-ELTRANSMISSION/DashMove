#!/bin/bash

# Development Environment Teardown Script
# Cleans up kind cluster and related resources

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
        print_error "kind is not installed."
        exit 1
    fi
    
    if ! command_exists kubectl; then
        print_error "kubectl is not installed."
        exit 1
    fi
    
    if ! command_exists helm; then
        print_error "helm is not installed."
        exit 1
    fi
    
    print_success "All prerequisites are available"
}

# Uninstall helm releases
uninstall_helm_releases() {
    print_status "Uninstalling helm releases..."
    
    # Check if cluster exists first
    if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        print_warning "Cluster '${CLUSTER_NAME}' does not exist. Skipping helm cleanup."
        return 0
    fi
    
    # Check if context is available
    if ! kubectl config get-contexts "${CONTEXT_NAME}" >/dev/null 2>&1; then
        print_warning "Context '${CONTEXT_NAME}' not available. Skipping helm cleanup."
        return 0
    fi
    
    # Uninstall Grafana instances
    if helm --kube-context "${CONTEXT_NAME}" list -n grafana-1 | grep -q "grafana-1"; then
        print_status "Uninstalling grafana-1..."
        helm --kube-context "${CONTEXT_NAME}" uninstall grafana-1 -n grafana-1
        print_success "Uninstalled grafana-1"
    else
        print_warning "Release 'grafana-1' not found"
    fi
    
    if helm --kube-context "${CONTEXT_NAME}" list -n grafana-2 | grep -q "grafana-2"; then
        print_status "Uninstalling grafana-2..."
        helm --kube-context "${CONTEXT_NAME}" uninstall grafana-2 -n grafana-2
        print_success "Uninstalled grafana-2"
    else
        print_warning "Release 'grafana-2' not found"
    fi
}

# Delete persistent volumes and claims
cleanup_storage() {
    print_status "Cleaning up persistent storage..."
    
    # Check if cluster exists first
    if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        print_warning "Cluster '${CLUSTER_NAME}' does not exist. Skipping storage cleanup."
        return 0
    fi
    
    # Delete PVCs in Grafana namespaces
    for ns in grafana-1 grafana-2; do
        if kubectl --context "${CONTEXT_NAME}" get namespace "${ns}" >/dev/null 2>&1; then
            print_status "Deleting PVCs in namespace ${ns}..."
            kubectl --context "${CONTEXT_NAME}" delete pvc --all -n "${ns}" --timeout=60s || true
        fi
    done
    
    print_success "Storage cleanup completed"
}

# Delete namespaces
delete_namespaces() {
    print_status "Deleting namespaces..."
    
    # Check if cluster exists first
    if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        print_warning "Cluster '${CLUSTER_NAME}' does not exist. Skipping namespace cleanup."
        return 0
    fi
    
    # Delete Grafana namespaces
    for ns in grafana-1 grafana-2; do
        if kubectl --context "${CONTEXT_NAME}" get namespace "${ns}" >/dev/null 2>&1; then
            print_status "Deleting namespace ${ns}..."
            kubectl --context "${CONTEXT_NAME}" delete namespace "${ns}" --timeout=120s || true
        else
            print_warning "Namespace '${ns}' not found"
        fi
    done
    
    print_success "Namespaces deleted"
}

# Delete kind cluster
delete_cluster() {
    print_status "Deleting kind cluster..."
    
    # Check if cluster exists
    if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
        print_warning "Cluster '${CLUSTER_NAME}' does not exist. Nothing to delete."
        return 0
    fi
    
    # Delete the cluster
    kind delete cluster --name "${CLUSTER_NAME}"
    
    print_success "Kind cluster deleted successfully"
}

# Clean up docker resources
cleanup_docker() {
    print_status "Cleaning up docker resources..."
    
    # Remove dangling images
    if command_exists docker; then
        print_status "Removing dangling docker images..."
        docker image prune -f >/dev/null 2>&1 || true
        
        print_status "Removing unused docker volumes..."
        docker volume prune -f >/dev/null 2>&1 || true
        
        print_success "Docker cleanup completed"
    else
        print_warning "Docker not available, skipping docker cleanup"
    fi
}

# Display final status
display_final_status() {
    print_status "Teardown complete!"
    echo
    
    print_status "Checking remaining kind clusters:"
    if kind get clusters 2>/dev/null | grep -q .; then
        kind get clusters
    else
        echo "No kind clusters remaining"
    fi
    echo
    
    print_status "Checking kubectl contexts:"
    kubectl config get-contexts | grep -E "(CURRENT|kind)" || echo "No kind contexts remaining"
    echo
    
    print_success "Development environment teardown completed successfully!"
}

# Confirmation prompt
confirm_teardown() {
    echo -e "${YELLOW}WARNING: This will completely destroy the development environment!${NC}"
    echo "This includes:"
    echo "- Kind cluster '${CLUSTER_NAME}'"
    echo "- All deployed applications and data"
    echo "- All persistent volumes and claims"
    echo "- All namespaces and resources"
    echo
    
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Teardown cancelled."
        exit 0
    fi
}

# Main execution
main() {
    print_status "Starting development environment teardown..."
    echo
    
    # Skip confirmation if --force flag is provided
    if [[ "$1" != "--force" ]]; then
        confirm_teardown
    fi
    
    check_prerequisites
    uninstall_helm_releases
    cleanup_storage
    delete_namespaces
    delete_cluster
    cleanup_docker
    display_final_status
}

# Run main function
main "$@"
