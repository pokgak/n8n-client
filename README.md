# n8n CLI

Python CLI for managing n8n workflows and troubleshooting executions.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

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

### 3. Run the CLI

No installation needed - uses `uv run` with inline script dependencies:

```bash
uv run n8n-cli --help
```

## CLI Usage

### Workflows

```bash
# List all workflows
uv run n8n-cli workflows
uv run n8n-cli workflows --active
uv run n8n-cli workflows --json

# Get workflow details
uv run n8n-cli workflow <workflow_id>
uv run n8n-cli workflow <workflow_id> --json

# Update workflow from JSON file
uv run n8n-cli update <workflow_id> workflow.json

# Activate/deactivate workflows
uv run n8n-cli activate <workflow_id>
uv run n8n-cli deactivate <workflow_id>
```

### Nodes (view and edit workflow nodes)

```bash
# List all nodes in a workflow
uv run n8n-cli nodes <workflow_id>

# View node details
uv run n8n-cli node <workflow_id> "node name"
uv run n8n-cli node <workflow_id> "node name" --json

# View Code node's JavaScript
uv run n8n-cli node <workflow_id> "node name" --code

# Update Code node from file
uv run n8n-cli node <workflow_id> "node name" --set-code script.js

# Rename a node
uv run n8n-cli node <workflow_id> "old name" --rename "new name"

# Rename and update code in one command
uv run n8n-cli node <workflow_id> "old name" --rename "new name" --set-code script.js
```

### Export/Import Code Nodes

Useful for editing Code node scripts in a proper editor with syntax highlighting.

```bash
# Export all Code nodes to a directory
uv run n8n-cli export-code <workflow_id> ./nodes/
# Creates: ./nodes/node_name.js, ./nodes/_manifest.json

# Edit the scripts with your editor...

# Import updated scripts back to workflow
uv run n8n-cli import-code <workflow_id> ./nodes/
```

### Trigger Workflows

```bash
# Trigger workflow by name via webhook
uv run n8n-cli trigger "Alerting"

# Trigger with JSON payload
uv run n8n-cli trigger "Alerting" --data '{"key": "value"}'

# Trigger with payload from file
uv run n8n-cli trigger "Alerting" --file payload.json

# Use test webhook URL (for debugging)
uv run n8n-cli trigger "Alerting" --test --data '{"test": true}'

# Run workflow directly (not via webhook)
uv run n8n-cli run <workflow_id>
uv run n8n-cli run <workflow_id> --data '{"input": "data"}'
uv run n8n-cli run <workflow_id> --output  # show node outputs
```

### Executions

```bash
# List executions
uv run n8n-cli executions
uv run n8n-cli executions --workflow <workflow_id>
uv run n8n-cli executions --status error
uv run n8n-cli executions -n 100

# Get execution details (includes error info for failed executions)
uv run n8n-cli execution <execution_id>
uv run n8n-cli execution <execution_id> --data  # full execution data

# Retry failed execution
uv run n8n-cli retry <execution_id>
uv run n8n-cli retry <execution_id> --latest  # use current workflow version
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
uv run n8n-cli export-code <workflow_id> ./nodes/

# 2. Edit scripts in your editor (with syntax highlighting)
code ./nodes/

# 3. Import changes back
uv run n8n-cli import-code <workflow_id> ./nodes/
```

### Quick Node Update

```bash
# View current code
uv run n8n-cli node <workflow_id> "node name" --code > script.js

# Edit and update
uv run n8n-cli node <workflow_id> "node name" --set-code script.js
```

### Troubleshooting Executions

```bash
# Find failed executions
uv run n8n-cli executions --status error

# Get error details
uv run n8n-cli execution <id>

# Get full execution data for debugging
uv run n8n-cli execution <id> --data --json
```

### Testing Webhook Workflows

```bash
# Trigger with test payload
uv run n8n-cli trigger "Workflow Name" --test --file test_payload.json

# Check execution result
uv run n8n-cli executions --workflow <id> -n 1
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
