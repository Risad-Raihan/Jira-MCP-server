# Jira MCP Server
A Multi-Capability Protocol (MCP) server providing comprehensive JIRA integration for AI assistants like Claude and Gemini CLI. This server allows AI models to interact with your JIRA instance to perform various actions.

## Setup
Follow these steps:

### 1. clone the repository
```bash 
git clone <repo>
cd Jira MCP 
``` 

### 2. configure environmental variable
craetea a file name called .env with following information updates:

JIRA_BASE_URL=https://your-jira-instance.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_API_TOKEN=YOUR_JIRA_API_TOKEN # Generate this in your Atlassian account settings
JIRA_DEFAULT_PROJECT=YOUR_DEFAULT_PROJECT_KEY # e.g., DAV1

### 3. Run the Setup Script
Execute the setup.sh script to automate the installation of dependencies, make the server executable, and test your JIRA connection:

```bash
./setup.sh
This script performs the following actions:
```

Creates a requirements.txt file containing necessary Python packages
Installs all Python dependencies using pip
Makes the mcp_server.py script executable
Performs a test connection to your JIRA instance using the provided credentials


### 4. Running the Server
After successful setup, you can start the JIRA MCP server:

```bash
python3 mcp_server.py
```

The server will then be ready to accept requests via standard input/output (stdio), typically from an AI assistant or a CLI that implements the MCP protocol.

### Dependencies
The project relies on the following Python packages:

mcp>=1.0.0
aiohttp>=3.8.0
python-dotenv>=0.19.0 


### Usage with AI Assistants
This server exposes JIRA functionalities as tools, allowing AI assistants to programmatically interact with your JIRA projects (e.g., creating issues, fetching details, updating statuses) by sending MCP requests.

### Contributing
Contributions are welcome! Feel free to open issues or submit pull requests.

Developer
Risad Raihan Malik

License
Apache 2.0