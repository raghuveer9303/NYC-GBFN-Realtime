#!/bin/bash

echo "🔍 Validating Docker Compose file..."

# Check if the file exists
if [ ! -f "docker-compose.consumer-only.yml" ]; then
    echo "❌ File docker-compose.consumer-only.yml not found!"
    exit 1
fi

# Show first few characters to check for hidden characters
echo "📋 First line content (with hex dump):"
head -n 1 docker-compose.consumer-only.yml | hexdump -C

# Validate YAML syntax
echo ""
echo "📋 YAML validation:"
if command -v python3 &> /dev/null; then
    python3 -c "
import yaml
import sys
try:
    with open('docker-compose.consumer-only.yml', 'r') as f:
        yaml.safe_load(f)
    print('✅ YAML syntax is valid')
except yaml.YAMLError as e:
    print(f'❌ YAML syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error reading file: {e}')
    sys.exit(1)
"
else
    echo "⚠️ Python3 not found, skipping YAML validation"
fi

# Validate Docker Compose
echo ""
echo "📋 Docker Compose validation:"
docker-compose -f docker-compose.consumer-only.yml config --quiet
if [ $? -eq 0 ]; then
    echo "✅ Docker Compose file is valid"
else
    echo "❌ Docker Compose validation failed"
    echo ""
    echo "🔧 Attempting to fix line endings..."
    # Convert Windows line endings to Unix
    sed -i 's/\r$//' docker-compose.consumer-only.yml
    echo "✅ Line endings converted"
    
    echo ""
    echo "📋 Re-validating after fix:"
    docker-compose -f docker-compose.consumer-only.yml config --quiet
    if [ $? -eq 0 ]; then
        echo "✅ Docker Compose file is now valid"
    else
        echo "❌ Still invalid - manual inspection needed"
    fi
fi
