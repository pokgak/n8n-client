#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
n8n CLI - Command-line tool for managing workflows and troubleshooting executions

Usage:
    # List workflows
    uv run n8n-cli.py workflows
    uv run n8n-cli.py workflows --active

    # Get workflow details
    uv run n8n-cli.py workflow <id>

    # Update workflow from JSON file
    uv run n8n-cli.py update <id> workflow.json

    # Activate/deactivate workflows
    uv run n8n-cli.py activate <id>
    uv run n8n-cli.py deactivate <id>

    # List nodes in a workflow
    uv run n8n-cli.py nodes <workflow_id>

    # View/edit specific node
    uv run n8n-cli.py node <workflow_id> "node name" --code
    uv run n8n-cli.py node <workflow_id> "node name" --set-code script.js
    uv run n8n-cli.py node <workflow_id> "old name" --rename "new name"

    # Export/import Code node scripts
    uv run n8n-cli.py export-code <workflow_id> ./nodes/
    uv run n8n-cli.py import-code <workflow_id> ./nodes/

    # List executions
    uv run n8n-cli.py executions
    uv run n8n-cli.py executions --workflow <id>
    uv run n8n-cli.py executions --status error

    # Get execution details
    uv run n8n-cli.py execution <id>
    uv run n8n-cli.py execution <id> --data

    # Retry failed execution
    uv run n8n-cli.py retry <id>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from n8n_client import N8nClient


def format_time(iso_string: str | None) -> str:
    if not iso_string:
        return "-"
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_string


def print_json(data):
    print(json.dumps(data, indent=2))


def cmd_workflows(client: N8nClient, args):
    active = None
    if args.active:
        active = True
    elif args.inactive:
        active = False

    result = client.get_all_pages(client.get_workflows, active=active)

    if args.json:
        print_json(result)
        return

    if not result:
        print("No workflows found.")
        return

    print(f"{'ID':<20} {'NAME':<40} {'ACTIVE':<8} {'UPDATED':<20}")
    print("-" * 90)
    for wf in result:
        print(f"{wf['id']:<20} {wf['name'][:38]:<40} {str(wf.get('active', False)):<8} {format_time(wf.get('updatedAt')):<20}")


def cmd_workflow(client: N8nClient, args):
    wf = client.get_workflow(args.id)

    if args.json:
        print_json(wf)
        return

    print(f"ID:        {wf['id']}")
    print(f"Name:      {wf['name']}")
    print(f"Active:    {wf.get('active', False)}")
    print(f"Created:   {format_time(wf.get('createdAt'))}")
    print(f"Updated:   {format_time(wf.get('updatedAt'))}")
    print(f"Archived:  {wf.get('isArchived', False)}")

    nodes = wf.get("nodes", [])
    print(f"\nNodes ({len(nodes)}):")
    for node in nodes:
        print(f"  - {node.get('name', 'unnamed')} ({node.get('type', 'unknown')})")


def cmd_create(client: N8nClient, args):
    with open(args.file) as f:
        workflow = json.load(f)

    if args.name:
        workflow["name"] = args.name

    result = client.create_workflow(workflow)
    workflow_id = result.get('id')

    if args.project:
        client.transfer_workflow(workflow_id, args.project)

    if args.json:
        print_json(result)
        return

    print(f"Workflow created: {result.get('name')}")
    print(f"ID: {workflow_id}")
    if args.project:
        print(f"Project: {args.project}")
    print(f"Active: {result.get('active', False)}")


def cmd_update(client: N8nClient, args):
    with open(args.file) as f:
        workflow_data = json.load(f)

    # Extract only the fields that can be updated
    update_payload = {
        'name': workflow_data.get('name'),
        'nodes': workflow_data.get('nodes'),
        'connections': workflow_data.get('connections'),
        'settings': workflow_data.get('settings', {}),
        'staticData': workflow_data.get('staticData'),
    }

    # Remove None values
    update_payload = {k: v for k, v in update_payload.items() if v is not None}

    result = client.update_workflow(args.id, update_payload)

    if args.json:
        print_json(result)
        return

    print(f"Workflow updated: {result.get('name')}")
    print(f"ID: {result.get('id')}")


def cmd_nodes(client: N8nClient, args):
    wf = client.get_workflow(args.id)
    nodes = wf.get("nodes", [])

    if args.json:
        print_json(nodes)
        return

    if not nodes:
        print("No nodes found.")
        return

    print(f"{'NAME':<40} {'TYPE':<50}")
    print("-" * 92)
    for node in nodes:
        name = node.get('name', 'unnamed')[:38]
        node_type = node.get('type', 'unknown')
        # Mark Code nodes
        if node_type == 'n8n-nodes-base.code':
            node_type = f"{node_type} *"
        print(f"{name:<40} {node_type:<50}")

    code_count = sum(1 for n in nodes if n.get('type') == 'n8n-nodes-base.code')
    if code_count:
        print(f"\n* {code_count} Code node(s) - use 'node <id> <name> --code' to view")


def cmd_node(client: N8nClient, args):
    wf = client.get_workflow(args.id)
    nodes = wf.get("nodes", [])

    # Find the node by name
    node = None
    for n in nodes:
        if n.get('name') == args.name:
            node = n
            break

    if not node:
        print(f"Node '{args.name}' not found.", file=sys.stderr)
        print("\nAvailable nodes:")
        for n in nodes:
            print(f"  - {n.get('name')}")
        sys.exit(1)

    # Handle --set-code
    if args.set_code:
        if node.get('type') != 'n8n-nodes-base.code':
            print(f"Node '{args.name}' is not a Code node.", file=sys.stderr)
            sys.exit(1)

        with open(args.set_code) as f:
            new_code = f.read()

        node['parameters']['jsCode'] = new_code

        # Handle rename if provided
        old_name = node['name']
        if args.rename:
            node['name'] = args.rename
            # Update connections
            if old_name in wf['connections']:
                wf['connections'][args.rename] = wf['connections'].pop(old_name)
            for conn_name, conn in wf['connections'].items():
                if 'main' in conn:
                    for outputs in conn['main']:
                        for output in outputs:
                            if output.get('node') == old_name:
                                output['node'] = args.rename

        update_payload = {
            'name': wf['name'],
            'nodes': nodes,
            'connections': wf['connections'],
            'settings': wf.get('settings', {}),
            'staticData': wf.get('staticData'),
        }

        client.update_workflow(args.id, update_payload)
        if args.rename:
            print(f"Node '{old_name}' renamed to '{args.rename}' and code updated.")
        else:
            print(f"Node '{args.name}' code updated.")
        return

    # Handle --rename only
    if args.rename:
        old_name = node['name']
        node['name'] = args.rename

        # Update connections
        if old_name in wf['connections']:
            wf['connections'][args.rename] = wf['connections'].pop(old_name)
        for conn_name, conn in wf['connections'].items():
            if 'main' in conn:
                for outputs in conn['main']:
                    for output in outputs:
                        if output.get('node') == old_name:
                            output['node'] = args.rename

        update_payload = {
            'name': wf['name'],
            'nodes': nodes,
            'connections': wf['connections'],
            'settings': wf.get('settings', {}),
            'staticData': wf.get('staticData'),
        }

        client.update_workflow(args.id, update_payload)
        print(f"Node '{old_name}' renamed to '{args.rename}'.")
        return

    # Handle --code (view code)
    if args.code:
        if node.get('type') != 'n8n-nodes-base.code':
            print(f"Node '{args.name}' is not a Code node.", file=sys.stderr)
            sys.exit(1)

        code = node.get('parameters', {}).get('jsCode', '')
        print(code)
        return

    # Default: show node details
    if args.json:
        print_json(node)
        return

    print(f"Name:       {node.get('name')}")
    print(f"Type:       {node.get('type')}")
    print(f"ID:         {node.get('id')}")

    params = node.get('parameters', {})
    if params:
        print(f"\nParameters:")
        for key, value in params.items():
            if key == 'jsCode':
                lines = value.count('\n') + 1
                print(f"  {key}: <{lines} lines>")
            elif isinstance(value, str) and len(value) > 50:
                print(f"  {key}: {value[:50]}...")
            else:
                print(f"  {key}: {value}")


def sanitize_filename(name: str) -> str:
    """Convert node name to safe filename."""
    # Replace spaces and special chars with underscores
    safe = re.sub(r'[^\w\-]', '_', name)
    # Remove consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_').lower()


def cmd_export_code(client: N8nClient, args):
    wf = client.get_workflow(args.id)
    nodes = wf.get("nodes", [])

    # Filter to Code nodes only
    code_nodes = [n for n in nodes if n.get('type') == 'n8n-nodes-base.code']

    if not code_nodes:
        print("No Code nodes found in workflow.")
        return

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest file for import
    manifest = {
        'workflow_id': args.id,
        'workflow_name': wf.get('name'),
        'nodes': {}
    }

    exported = 0
    for node in code_nodes:
        name = node.get('name', 'unnamed')
        code = node.get('parameters', {}).get('jsCode', '')

        filename = sanitize_filename(name) + '.js'
        filepath = output_dir / filename

        with open(filepath, 'w') as f:
            f.write(code)

        manifest['nodes'][filename] = name
        exported += 1
        print(f"Exported: {name} -> {filename}")

    # Write manifest
    manifest_path = output_dir / '_manifest.json'
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\nExported {exported} Code node(s) to {output_dir}/")
    print(f"Manifest: {manifest_path}")


def cmd_import_code(client: N8nClient, args):
    input_dir = Path(args.input_dir)

    # Read manifest
    manifest_path = input_dir / '_manifest.json'
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        print("Run 'export-code' first to create the manifest.")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Get current workflow
    wf = client.get_workflow(args.id)
    nodes = wf.get("nodes", [])

    # Create node name lookup
    node_map = {n.get('name'): n for n in nodes}

    updated = 0
    for filename, node_name in manifest['nodes'].items():
        filepath = input_dir / filename

        if not filepath.exists():
            print(f"Skipping: {filename} (file not found)")
            continue

        if node_name not in node_map:
            print(f"Skipping: {node_name} (node not in workflow)")
            continue

        node = node_map[node_name]
        if node.get('type') != 'n8n-nodes-base.code':
            print(f"Skipping: {node_name} (not a Code node)")
            continue

        with open(filepath) as f:
            new_code = f.read()

        old_code = node.get('parameters', {}).get('jsCode', '')
        if new_code == old_code:
            print(f"Unchanged: {node_name}")
            continue

        node['parameters']['jsCode'] = new_code
        updated += 1
        print(f"Updated: {node_name}")

    if updated == 0:
        print("\nNo changes to import.")
        return

    # Push update
    update_payload = {
        'name': wf['name'],
        'nodes': nodes,
        'connections': wf['connections'],
        'settings': wf.get('settings', {}),
        'staticData': wf.get('staticData'),
    }

    client.update_workflow(args.id, update_payload)
    print(f"\nImported {updated} Code node(s).")


def cmd_activate(client: N8nClient, args):
    result = client.activate_workflow(args.id)
    print(f"Workflow '{result.get('name', args.id)}' activated.")


def cmd_deactivate(client: N8nClient, args):
    result = client.deactivate_workflow(args.id)
    print(f"Workflow '{result.get('name', args.id)}' deactivated.")


def cmd_executions(client: N8nClient, args):
    result = client.get_all_pages(
        client.get_executions,
        workflow_id=args.workflow,
        status=args.status,
        limit=args.limit,
    )

    if args.json:
        print_json(result)
        return

    if not result:
        print("No executions found.")
        return

    print(f"{'ID':<12} {'WORKFLOW':<30} {'STATUS':<10} {'STARTED':<20} {'FINISHED':<20}")
    print("-" * 95)
    for ex in result[:args.limit or 50]:
        wf_name = ex.get("workflowData", {}).get("name", ex.get("workflowId", "-"))[:28]
        print(
            f"{ex['id']:<12} "
            f"{wf_name:<30} "
            f"{ex.get('status', '-'):<10} "
            f"{format_time(ex.get('startedAt')):<20} "
            f"{format_time(ex.get('stoppedAt')):<20}"
        )


def cmd_execution(client: N8nClient, args):
    ex = client.get_execution(args.id, include_data=args.data)

    if args.json:
        print_json(ex)
        return

    print(f"ID:         {ex['id']}")
    print(f"Status:     {ex.get('status', '-')}")
    print(f"Mode:       {ex.get('mode', '-')}")
    print(f"Started:    {format_time(ex.get('startedAt'))}")
    print(f"Finished:   {format_time(ex.get('stoppedAt'))}")
    print(f"Workflow:   {ex.get('workflowData', {}).get('name', ex.get('workflowId', '-'))}")

    if ex.get("status") == "error":
        print("\n--- ERROR INFO ---")
        data = ex.get("data", {})
        result_data = data.get("resultData", {})

        if "error" in result_data:
            err = result_data["error"]
            print(f"Message:    {err.get('message', '-')}")
            if err.get("description"):
                print(f"Details:    {err.get('description')}")
            if err.get("node"):
                print(f"Node:       {err.get('node')}")

        last_node = result_data.get("lastNodeExecuted")
        if last_node:
            print(f"Last Node:  {last_node}")

    if args.data and ex.get("data"):
        print("\n--- EXECUTION DATA ---")
        print_json(ex["data"])


def cmd_retry(client: N8nClient, args):
    result = client.retry_execution(args.id, load_workflow=args.latest)
    print(f"Execution retried. New execution ID: {result.get('id', 'unknown')}")
    print(f"Status: {result.get('status', '-')}")


def cmd_run(client: N8nClient, args):
    data = None
    if args.data:
        data = json.loads(args.data)

    result = client.run_workflow(args.id, data=data)

    if args.json:
        print_json(result)
        return

    print(f"Workflow executed.")
    print(f"Execution ID: {result.get('data', {}).get('executionId', 'unknown')}")
    if "data" in result and "data" in result["data"]:
        run_data = result["data"]["data"]
        if "resultData" in run_data:
            last_node = run_data["resultData"].get("lastNodeExecuted")
            if last_node:
                print(f"Last Node: {last_node}")
            run_result = run_data["resultData"].get("runData", {})
            for node_name, node_runs in run_result.items():
                for run in node_runs:
                    status = run.get("executionStatus", "-")
                    print(f"  {node_name}: {status}")
                    if args.output and run.get("data", {}).get("main"):
                        for items in run["data"]["main"]:
                            if items:
                                for item in items:
                                    print(f"    Output: {json.dumps(item.get('json', {}), indent=2)}")


def cmd_trigger(client: N8nClient, args):
    import httpx

    # Find workflow by name
    workflows = client.get_all_pages(client.get_workflows)
    matching = [w for w in workflows if args.name.lower() in w['name'].lower()]

    if not matching:
        print(f"No workflow found matching '{args.name}'", file=sys.stderr)
        sys.exit(1)

    if len(matching) > 1:
        print(f"Multiple workflows match '{args.name}':")
        for w in matching:
            print(f"  - {w['id']}: {w['name']}")
        sys.exit(1)

    workflow = client.get_workflow(matching[0]['id'])

    # Find webhook node
    webhook_node = None
    for node in workflow.get('nodes', []):
        if node.get('type') == 'n8n-nodes-base.webhook':
            webhook_node = node
            break

    if not webhook_node:
        print(f"Workflow '{workflow['name']}' has no webhook trigger", file=sys.stderr)
        sys.exit(1)

    # Build webhook URL
    path = webhook_node['parameters'].get('path', webhook_node.get('webhookId', ''))
    base_url = os.environ.get('N8N_BASE_URL', '').rstrip('/')

    # Use test webhook if --test flag is set
    webhook_type = "webhook-test" if args.test else "webhook"
    webhook_url = f"{base_url}/{webhook_type}/{path}"

    method = webhook_node['parameters'].get('httpMethod', 'GET')

    # Build payload
    payload = {}
    if args.file:
        with open(args.file) as f:
            payload = json.load(f)
    elif args.data:
        payload = json.loads(args.data)

    # Call webhook
    with httpx.Client(timeout=60.0) as http:
        if method == 'GET':
            response = http.get(webhook_url, params=payload if payload else None)
        else:
            response = http.post(webhook_url, json=payload)

    if args.json:
        try:
            print_json(response.json())
        except Exception:
            print(response.text)
        return

    print(f"Triggered: {workflow['name']}")
    print(f"Webhook: {webhook_url}")
    print(f"Status: {response.status_code}")
    if payload:
        print(f"Payload: {json.dumps(payload)[:100]}{'...' if len(json.dumps(payload)) > 100 else ''}")
    try:
        result = response.json()
        if isinstance(result, dict):
            for key, value in result.items():
                if key != 'issues':
                    print(f"{key}: {value}")
    except Exception:
        print(response.text[:500])


def main():
    parser = argparse.ArgumentParser(
        description="n8n CLI - Manage workflows and troubleshoot executions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # workflows
    p_workflows = subparsers.add_parser("workflows", help="List all workflows")
    p_workflows.add_argument("--active", action="store_true", help="Show only active workflows")
    p_workflows.add_argument("--inactive", action="store_true", help="Show only inactive workflows")
    p_workflows.add_argument("--json", action="store_true", help="Output as JSON")
    p_workflows.set_defaults(func=cmd_workflows)

    # workflow
    p_workflow = subparsers.add_parser("workflow", help="Get workflow details")
    p_workflow.add_argument("id", help="Workflow ID")
    p_workflow.add_argument("--json", action="store_true", help="Output as JSON")
    p_workflow.set_defaults(func=cmd_workflow)

    # create
    p_create = subparsers.add_parser("create", help="Create a workflow from JSON file")
    p_create.add_argument("file", help="Path to workflow JSON file")
    p_create.add_argument("--name", "-n", help="Override workflow name")
    p_create.add_argument("--project", "-p", help="Project ID to create workflow in")
    p_create.add_argument("--json", action="store_true", help="Output as JSON")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = subparsers.add_parser("update", help="Update a workflow from JSON file")
    p_update.add_argument("id", help="Workflow ID")
    p_update.add_argument("file", help="Path to workflow JSON file")
    p_update.add_argument("--json", action="store_true", help="Output as JSON")
    p_update.set_defaults(func=cmd_update)

    # nodes
    p_nodes = subparsers.add_parser("nodes", help="List nodes in a workflow")
    p_nodes.add_argument("id", help="Workflow ID")
    p_nodes.add_argument("--json", action="store_true", help="Output as JSON")
    p_nodes.set_defaults(func=cmd_nodes)

    # node
    p_node = subparsers.add_parser("node", help="View or edit a specific node")
    p_node.add_argument("id", help="Workflow ID")
    p_node.add_argument("name", help="Node name")
    p_node.add_argument("--code", "-c", action="store_true", help="Show node code (Code nodes only)")
    p_node.add_argument("--set-code", "-s", metavar="FILE", help="Update node code from file")
    p_node.add_argument("--rename", "-r", metavar="NAME", help="Rename the node")
    p_node.add_argument("--json", action="store_true", help="Output as JSON")
    p_node.set_defaults(func=cmd_node)

    # export-code
    p_export = subparsers.add_parser("export-code", help="Export Code node scripts to files")
    p_export.add_argument("id", help="Workflow ID")
    p_export.add_argument("output_dir", help="Output directory for scripts")
    p_export.set_defaults(func=cmd_export_code)

    # import-code
    p_import = subparsers.add_parser("import-code", help="Import Code node scripts from files")
    p_import.add_argument("id", help="Workflow ID")
    p_import.add_argument("input_dir", help="Directory containing scripts and manifest")
    p_import.set_defaults(func=cmd_import_code)

    # activate
    p_activate = subparsers.add_parser("activate", help="Activate a workflow")
    p_activate.add_argument("id", help="Workflow ID")
    p_activate.set_defaults(func=cmd_activate)

    # deactivate
    p_deactivate = subparsers.add_parser("deactivate", help="Deactivate a workflow")
    p_deactivate.add_argument("id", help="Workflow ID")
    p_deactivate.set_defaults(func=cmd_deactivate)

    # executions
    p_executions = subparsers.add_parser("executions", help="List executions")
    p_executions.add_argument("--workflow", "-w", help="Filter by workflow ID")
    p_executions.add_argument("--status", "-s", choices=["canceled", "error", "running", "success", "waiting"], help="Filter by status")
    p_executions.add_argument("--limit", "-n", type=int, default=50, help="Max results (default: 50)")
    p_executions.add_argument("--json", action="store_true", help="Output as JSON")
    p_executions.set_defaults(func=cmd_executions)

    # execution
    p_execution = subparsers.add_parser("execution", help="Get execution details")
    p_execution.add_argument("id", help="Execution ID")
    p_execution.add_argument("--data", "-d", action="store_true", help="Include full execution data")
    p_execution.add_argument("--json", action="store_true", help="Output as JSON")
    p_execution.set_defaults(func=cmd_execution)

    # retry
    p_retry = subparsers.add_parser("retry", help="Retry a failed execution")
    p_retry.add_argument("id", help="Execution ID")
    p_retry.add_argument("--latest", action="store_true", help="Use latest workflow version instead of original")
    p_retry.set_defaults(func=cmd_retry)

    # run
    p_run = subparsers.add_parser("run", help="Execute a workflow manually")
    p_run.add_argument("id", help="Workflow ID")
    p_run.add_argument("--data", "-d", help="Input data as JSON string")
    p_run.add_argument("--output", "-o", action="store_true", help="Show node outputs")
    p_run.add_argument("--json", action="store_true", help="Output full result as JSON")
    p_run.set_defaults(func=cmd_run)

    # trigger
    p_trigger = subparsers.add_parser("trigger", help="Trigger a workflow by name (via webhook)")
    p_trigger.add_argument("name", help="Workflow name (partial match)")
    p_trigger.add_argument("--data", "-d", help="JSON payload to send")
    p_trigger.add_argument("--file", "-f", help="File containing JSON payload")
    p_trigger.add_argument("--test", "-t", action="store_true", help="Use test webhook URL")
    p_trigger.add_argument("--json", action="store_true", help="Output full result as JSON")
    p_trigger.set_defaults(func=cmd_trigger)

    args = parser.parse_args()

    try:
        client = N8nClient()
        args.func(client, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
