#!/bin/bash

echo "🚀 Setting up InfluxDB bucket for Citi Bike data..."

# InfluxDB connection details
INFLUXDB_URL="http://localhost:8086"
INFLUXDB_TOKEN="data-infra-super-secret-auth-token-2025"
INFLUXDB_ORG="data-infra-org"
BUCKET_NAME="citi-bike-data"

# Function to check if InfluxDB is running
check_influxdb() {
    echo "🔍 Checking InfluxDB connectivity..."
    if curl -s "${INFLUXDB_URL}/health" > /dev/null; then
        echo "✅ InfluxDB is running"
        return 0
    else
        echo "❌ InfluxDB is not accessible at ${INFLUXDB_URL}"
        echo "   Please make sure InfluxDB is running:"
        echo "   docker-compose -f ../Data-Infrastrucuture/Docker/influxdb-docker.yaml up -d"
        return 1
    fi
}

# Function to create bucket
create_bucket() {
    echo "🪣 Creating bucket: ${BUCKET_NAME}"
    
    # Check if bucket already exists
    existing_bucket=$(curl -s \
        -H "Authorization: Token ${INFLUXDB_TOKEN}" \
        "${INFLUXDB_URL}/api/v2/buckets?name=${BUCKET_NAME}" | \
        python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    buckets = data.get('buckets', [])
    if buckets:
        print('exists')
    else:
        print('not_found')
except:
    print('error')
")

    if [ "$existing_bucket" = "exists" ]; then
        echo "✅ Bucket '${BUCKET_NAME}' already exists"
        return 0
    fi

    # Get organization ID
    echo "🔍 Getting organization ID..."
    org_id=$(curl -s \
        -H "Authorization: Token ${INFLUXDB_TOKEN}" \
        "${INFLUXDB_URL}/api/v2/orgs?org=${INFLUXDB_ORG}" | \
        python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    orgs = data.get('orgs', [])
    if orgs:
        print(orgs[0]['id'])
    else:
        print('error')
except:
    print('error')
")

    if [ "$org_id" = "error" ]; then
        echo "❌ Failed to get organization ID"
        return 1
    fi

    echo "📋 Organization ID: ${org_id}"

    # Create the bucket
    echo "🏗️ Creating bucket..."
    response=$(curl -s -w "%{http_code}" \
        -X POST \
        -H "Authorization: Token ${INFLUXDB_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"${BUCKET_NAME}\",
            \"orgID\": \"${org_id}\",
            \"retentionRules\": [
                {
                    \"type\": \"expire\",
                    \"everySeconds\": 2592000
                }
            ]
        }" \
        "${INFLUXDB_URL}/api/v2/buckets")

    http_code="${response: -3}"
    response_body="${response%???}"

    if [ "$http_code" = "201" ]; then
        echo "✅ Bucket '${BUCKET_NAME}' created successfully!"
        return 0
    else
        echo "❌ Failed to create bucket (HTTP ${http_code})"
        echo "Response: ${response_body}"
        return 1
    fi
}

# Function to verify bucket
verify_bucket() {
    echo "🔍 Verifying bucket exists..."
    curl -s \
        -H "Authorization: Token ${INFLUXDB_TOKEN}" \
        "${INFLUXDB_URL}/api/v2/buckets?name=${BUCKET_NAME}" | \
        python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    buckets = data.get('buckets', [])
    if buckets:
        bucket = buckets[0]
        print(f'✅ Bucket verified: {bucket[\"name\"]} (ID: {bucket[\"id\"]})')
        print(f'   Organization: {bucket.get(\"orgID\", \"N/A\")}')
        print(f'   Created: {bucket.get(\"createdAt\", \"N/A\")}')
    else:
        print('❌ Bucket not found after creation')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error verifying bucket: {e}')
    sys.exit(1)
"
}

# Main execution
main() {
    echo "🚀 InfluxDB Bucket Setup for Citi Bike Data"
    echo "=" * 50
    
    if ! check_influxdb; then
        exit 1
    fi
    
    if ! create_bucket; then
        exit 1
    fi
    
    verify_bucket
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "📊 InfluxDB Access Information:"
    echo "   URL: ${INFLUXDB_URL}"
    echo "   Organization: ${INFLUXDB_ORG}"
    echo "   Bucket: ${BUCKET_NAME}"
    echo "   Token: ${INFLUXDB_TOKEN}"
    echo ""
    echo "🚀 You can now restart the consumer:"
    echo "   docker-compose -f docker-compose.consumer-only.yml restart"
}

main
