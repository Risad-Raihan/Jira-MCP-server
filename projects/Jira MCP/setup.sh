#!/bin/bash

# JIRA MCP Setup Script for Risad
# Run this script in /home/risad/projects/Jira MCP/

echo "🚀 Setting up JIRA MCP Server for Gemini CLI..."

# Check if we're in the right directory
if [[ ! "$PWD" == *"Jira MCP"* ]]; then
    echo "⚠️  Please run this script from /home/risad/projects/Jira MCP/ directory"
    exit 1
fi

# Create .env file
echo "📝 Creating .env file..."
cat > .env << 'EOF'
JIRA_BASE_URL=https://r++++++n.atlassian.net
JIRA_USERNAME=r***@gmail.com
JIRA_API_TOKEN= your access token
JIRA_DEFAULT_PROJECT=DAV1
EOF

# Create requirements.txt
echo "📦 Creating requirements.txt..."
cat > requirements.txt << 'EOF'
mcp>=1.0.0
aiohttp>=3.8.0
python-dotenv>=0.19.0
EOF

# Install Python dependencies
echo "🔧 Installing Python dependencies..."
pip install -r requirements.txt

# Make the MCP server executable
echo "🔐 Making MCP server executable..."
chmod +x mcp_server.py

# Test the connection
echo "🧪 Testing JIRA connection..."
python3 -c "
import os
import sys
sys.path.append('.')
from dotenv import load_dotenv
load_dotenv()

import asyncio
import aiohttp
import base64

async def test_jira():
    base_url = os.getenv('JIRA_BASE_URL')
    username = os.getenv('JIRA_USERNAME') 
    api_token = os.getenv('JIRA_API_TOKEN')
    
    auth_string = f'{username}:{api_token}'
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Accept': 'application/json'
    }
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f'{base_url}/rest/api/3/myself') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f'✅ Successfully connected to JIRA as: {data.get(\"displayName\", \"Unknown\")}')
                    return True
                else:
                    print(f'❌ JIRA connection failed with status: {response.status}')
                    return False
    except Exception as e:
        print(f'❌ Connection error: {e}')
        return False

if asyncio.run(test_jira()):
    print('🎉 JIRA MCP Server setup completed successfully!')
else:
    print('❌ Setup failed. Please check your credentials.')
"

echo ""
echo "📋 Your JIRA Projects:"
echo "  1. Designing Agent-v0.1 (DAV1) - Default project"
echo "  2. Edtech Bangla text-generation model (BTS)"
echo ""
echo "🎯 Next steps for Gemini CLI integration:"
echo "  1. Find your Gemini CLI config directory"
echo "  2. Add MCP server configuration"
echo "  3. Restart Gemini CLI"
echo ""
echo "💡 MCP server path: $PWD/mcp_server.py"