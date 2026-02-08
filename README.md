# n8n-client

Python CLI for managing n8n workflows and troubleshooting executions.

## Installation

```bash
pip install n8n-client
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install n8n-client
```

## Setup

### 1. Get your n8n API key

1. Open your n8n instance
2. Go to **Settings** → **n8n API**
3. Click **Create API Key**
4. Copy the generated key

### 2. Set environment variables

```bash
export N8N_API_KEY="your-api-key-here"
export N8N_BASE_URL="https://your-instance.app.n8n.cloud"
```

Or create a `.envrc` file (if using [direnv](https://direnv.net/)):

```bash
export N8N_API_KEY="your-api-key-here"
export N8N_BASE_URL="https://your-instance.app.n8n.cloud"
```

### 3. Verify installation

```bash
n8n-client --help
```

## CLI Usage

### Workflows

```bash
# List all workflows
n8n-client workflows
n8n-client workflows --active
n8n-client workflows --json

# Get workflow details
n8n-client workflow <workflow_id>
n8n-client workflow <workflow_id> --json

# Update workflow from JSON file
n8n-client update <workflow_id> workflow.json

# Activate/deactivate workflows
n8n-client activate <workflow_id>
n8n-client deactivate <workflow_id>
```

### Nodes (view and edit workflow nodes)

```bash
# List all nodes in a workflow
n8n-client nodes <workflow_id>

# View node details
n8n-client node <workflow_id> "node name"
n8n-client node <workflow_id> "node name" --json

# View Code node's JavaScript
n8n-client node <workflow_id> "node name" --code

# Update Code node from file
n8n-client node <workflow_id> "node name" --set-code script.js

# Rename a node
n8n-client node <workflow_id> "old name" --rename "new name"

# Rename and update code in one command
n8n-client node <workflow_id> "old name" --rename "new name" --set-code script.js
```

### Export/Import Code Nodes

Useful for editing Code node scripts in a proper editor with syntax highlighting.

```bash
# Export all Code nodes to a directory
n8n-client export-code <workflow_id> ./nodes/
# Creates: ./nodes/node_name.js, ./nodes/_manifest.json

# Edit the scripts with your editor...

# Import updated scripts back to workflow
n8n-client import-code <workflow_id> ./nodes/
```

### Trigger Workflows

```bash
# Trigger workflow by name via webhook
n8n-client trigger "Alerting"

# Trigger with JSON payload
n8n-client trigger "Alerting" --data '{"key": "value"}'

# Trigger with payload from file
n8n-client trigger "Alerting" --file payload.json

# Use test webhook URL (for debugging)
n8n-client trigger "Alerting" --test --data '{"test": true}'

# Run workflow directly (not via webhook)
n8n-client run <workflow_id>
n8n-client run <workflow_id> --data '{"input": "data"}'
n8n-client run <workflow_id> --output  # show node outputs
```

### Executions

```bash
# List executions
n8n-client executions
n8n-client executions --workflow <workflow_id>
n8n-client executions --status error
n8n-client executions -n 100

# Get execution details (includes error info for failed executions)
n8n-client execution <execution_id>
n8n-client execution <execution_id> --data  # full execution data

# Retry failed execution
n8n-client retry <execution_id>
n8n-client retry <execution_id> --latest  # use current workflow version
```

## Python API Usage

```python
# /// script
# dependencies = ["httpx"]
# ///
from n8n_client import N8nClient

client = N8nClient()

# List workflows
workflows = client.get_workflows()
for wf in workflows.data:
    print(f"{wf['id']}: {wf['name']}")

# Get all pages
all_workflows = client.get_all_pages(client.get_workflows, active=True)

# Get workflow details
wf = client.get_workflow("workflow_id")

# Get executions for a workflow
executions = client.get_executions(workflow_id="workflow_id", status="error")

# Get execution with full data
ex = client.get_execution("execution_id", include_data=True)

# Retry failed execution
client.retry_execution("execution_id")

# Activate/deactivate
client.activate_workflow("workflow_id")
client.deactivate_workflow("workflow_id")
```

## Common Workflows

### Editing Code Nodes

```bash
# 1. Export all Code nodes to files
n8n-client export-code <workflow_id> ./nodes/

# 2. Edit scripts in your editor (with syntax highlighting)
code ./nodes/

# 3. Import changes back
n8n-client import-code <workflow_id> ./nodes/
```

### Quick Node Update

```bash
# View current code
n8n-client node <workflow_id> "node name" --code > script.js

# Edit and update
n8n-client node <workflow_id> "node name" --set-code script.js
```

### Troubleshooting Executions

```bash
# Find failed executions
n8n-client executions --status error

# Get error details
n8n-client execution <id>

# Get full execution data for debugging
n8n-client execution <id> --data --json
```

### Testing Webhook Workflows

```bash
# Trigger with test payload
n8n-client trigger "Workflow Name" --test --file test_payload.json

# Check execution result
n8n-client executions --workflow <id> -n 1
```

## API Endpoints Covered

- **Workflows**: list, get, create, update, delete, activate, deactivate, tags
- **Executions**: list, get, delete, retry
- **Tags**: list, get, create, update, delete
- **Credentials**: create, delete, schema
- **Users**: list
- **Audit**: generate security audit
- **Variables**: list, create, delete
- **Projects**: list
