#!/usr/bin/env bash
set -euo pipefail

# Build script for Symbology Docker images
# This script builds all images locally and exports them as tars for deployment

echo "Building Symbology Docker images..."

# Default environment (can be overridden)
ENV="${1:-staging}"

echo "Building for environment: $ENV"

# Build API image
echo "Building API image..."
just build api
nerdctl save symbology-api:latest -o /tmp/symbology-api-latest.tar
echo "✅ API image exported to /tmp/symbology-api-latest.tar"

# Build UI image with environment configuration
echo "Building UI image for $ENV environment..."
pushd ui
    just build-for-deploy "$ENV"
    echo "✅ UI image exported to /tmp/symbology-ui-latest.tar"
popd

# Pull and export Postgres image
echo "Pulling and exporting Postgres image..."
nerdctl pull postgres:17.4
nerdctl save postgres:17.4 -o /tmp/postgres-17.4.tar
echo "✅ Postgres image exported to /tmp/postgres-17.4.tar"

echo ""
echo "🎉 All images built and exported successfully!"
echo "Ready for deployment with: ansible-playbook -i infra/inventories/$ENV infra/deploy-symbology.yml"
