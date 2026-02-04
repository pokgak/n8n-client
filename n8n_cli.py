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
    uv run n8n-cli workflows
    uv run n8n-cli workflows --active

    # Get workflow details
    uv run n8n-cli workflow <id>

    # Update workflow from JSON file
    uv run n8n-cli update <id> workflow.json

    # Activate/deactivate workflows
    uv run n8n-cli activate <id>
    uv run n8n-cli deactivate <id>

    # List nodes in a workflow
    uv run n8n-cli nodes <workflow_id>

    # View/edit specific node
    uv run n8n-cli node <workflow_id> "node name" --code
    uv run n8n-cli node <workflow_id> "node name" --set-code script.js
    uv run n8n-cli node <workflow_id> "old name" --rename "new name"
    uv run n8n-cli node <workflow_id> "HTTP Request" --set-param url="https://example.com"
    uv run n8n-cli node <workflow_id> "Agent" --set-param-json '{"options": {"systemMessage": "Hello"}}'

    # Create a new node
    uv run n8n-cli node <workflow_id> --add --type code --name "My Code Node"
    uv run n8n-cli node <workflow_id> --add --type switch --name "My Switch" --position 400,300

    # Add rule to Switch node
    uv run n8n-cli node <workflow_id> "Switch Name" --add-rule --field title --op contains --match-value "Error" --output-key errors

    # Manage connections between nodes
    uv run n8n-cli connect <workflow_id> "Source Node" "Target Node" --output 0
    uv run n8n-cli disconnect <workflow_id> "Source Node" "Target Node"

    # Export/import Code node scripts
    uv run n8n-cli export-code <workflow_id> ./nodes/
    uv run n8n-cli import-code <workflow_id> ./nodes/

    # Credentials management
    uv run n8n-cli credentials
    uv run n8n-cli credential-schema <type>
    uv run n8n-cli create-credential --name "My API" --type httpHeaderAuth --data '{"name": "X-API-Key", "value": "secret"}'
    uv run n8n-cli delete-credential <id>

    # List executions
    uv run n8n-cli executions
    uv run n8n-cli executions --workflow <id>
    uv run n8n-cli executions --status error

    # Get execution details
    uv run n8n-cli execution <id>
    uv run n8n-cli execution <id> --data

    # Retry failed execution
    uv run n8n-cli retry <id>
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from n8n_client import N8nClient


NODE_TYPE_SHORTCUTS = {
    "code": "n8n-nodes-base.code",
    "switch": "n8n-nodes-base.switch",
    "http": "n8n-nodes-base.httpRequest",
    "webhook": "n8n-nodes-base.webhook",
    "set": "n8n-nodes-base.set",
    "if": "n8n-nodes-base.if",
}

SWITCH_OPERATORS = {
    "contains": {"type": "string", "operation": "contains"},
    "equals": {"type": "string", "operation": "equals"},
    "not-equals": {"type": "string", "operation": "notEquals"},
    "starts-with": {"type": "string", "operation": "startsWith"},
    "ends-with": {"type": "string", "operation": "endsWith"},
    "regex": {"type": "string", "operation": "regex"},
}


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


def set_nested_param(obj: dict, key: str, value):
    """Set a nested parameter using dot notation (e.g., 'options.systemMessage')."""
    parts = key.split('.')
    for part in parts[:-1]:
        if part not in obj:
            obj[part] = {}
        obj = obj[part]
    obj[parts[-1]] = value


def get_node_type_full(shorthand: str) -> str:
    """Convert type shorthand to full n8n type."""
    return NODE_TYPE_SHORTCUTS.get(shorthand, shorthand)


def calculate_node_position(nodes: list) -> list:
    """Calculate position for new node (rightmost + 200px offset)."""
    if not nodes:
        return [200, 200]
    max_x = max(n.get("position", [0, 0])[0] for n in nodes)
    avg_y = sum(n.get("position", [0, 0])[1] for n in nodes) // len(nodes)
    return [max_x + 200, avg_y]


def build_workflow_payload(wf: dict, nodes: list) -> dict:
    """Build the payload for updating a workflow."""
    return {
        'name': wf['name'],
        'nodes': nodes,
        'connections': wf['connections'],
        'settings': wf.get('settings', {}),
        'staticData': wf.get('staticData'),
    }


def handle_add_node(client: N8nClient, wf: dict, args) -> None:
    """Create a new node in the workflow."""
    nodes = wf.get("nodes", [])

    if not args.node_type:
        print("--type is required when using --add", file=sys.stderr)
        sys.exit(1)
    if not args.new_name:
        print("--name is required when using --add", file=sys.stderr)
        sys.exit(1)

    for n in nodes:
        if n.get('name') == args.new_name:
            print(f"Node with name '{args.new_name}' already exists.", file=sys.stderr)
            sys.exit(1)

    node_type = get_node_type_full(args.node_type)

    if args.position:
        try:
            x, y = args.position.split(',')
            position = [int(x), int(y)]
        except ValueError:
            print("Invalid position format. Use X,Y (e.g., 200,300)", file=sys.stderr)
            sys.exit(1)
    else:
        position = calculate_node_position(nodes)

    new_node = {
        'id': str(uuid.uuid4()),
        'name': args.new_name,
        'type': node_type,
        'typeVersion': 1,
        'position': position,
        'parameters': {},
    }

    if node_type == 'n8n-nodes-base.code':
        new_node['typeVersion'] = 2
        new_node['parameters'] = {
            'jsCode': '// Add your code here\nreturn items;',
            'mode': 'runOnceForAllItems',
        }
    elif node_type == 'n8n-nodes-base.switch':
        new_node['typeVersion'] = 3
        new_node['parameters'] = {
            'rules': {
                'values': []
            },
            'options': {}
        }

    if args.param:
        for param in args.param:
            if '=' not in param:
                print(f"Invalid parameter format: {param}. Use key=value", file=sys.stderr)
                sys.exit(1)
            key, value = param.split('=', 1)
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
            set_nested_param(new_node['parameters'], key, value)

    nodes.append(new_node)
    client.update_workflow(args.id, build_workflow_payload(wf, nodes))
    print(f"Node '{args.new_name}' created.")
    print(f"Type: {node_type}")
    print(f"Position: {position[0]}, {position[1]}")


def handle_add_switch_rule(client: N8nClient, wf: dict, node: dict, args) -> None:
    """Add a rule to a Switch node."""
    nodes = wf.get("nodes", [])

    if node.get('type') != 'n8n-nodes-base.switch':
        print(f"Node '{args.name}' is not a Switch node.", file=sys.stderr)
        sys.exit(1)

    if not args.field:
        print("--field is required when using --add-rule", file=sys.stderr)
        sys.exit(1)
    if not args.op:
        print("--op is required when using --add-rule", file=sys.stderr)
        sys.exit(1)
    if not args.match_value:
        print("--match-value is required when using --add-rule", file=sys.stderr)
        sys.exit(1)
    if not args.output_key:
        print("--output-key is required when using --add-rule", file=sys.stderr)
        sys.exit(1)

    op_config = SWITCH_OPERATORS.get(args.op)
    if not op_config:
        print(f"Unknown operator: {args.op}", file=sys.stderr)
        print(f"Available operators: {', '.join(SWITCH_OPERATORS.keys())}")
        sys.exit(1)

    if 'parameters' not in node:
        node['parameters'] = {}
    if 'rules' not in node['parameters']:
        node['parameters']['rules'] = {'values': []}
    if 'values' not in node['parameters']['rules']:
        node['parameters']['rules']['values'] = []

    new_rule = {
        'id': str(uuid.uuid4()),
        'conditions': {
            'options': {
                'caseSensitive': True,
                'leftValue': '',
                'typeValidation': 'strict',
            },
            'conditions': [
                {
                    'id': str(uuid.uuid4()),
                    'leftValue': f'={{{{ $json.{args.field} }}}}',
                    'rightValue': args.match_value,
                    'operator': op_config,
                }
            ],
            'combinator': 'and',
        },
        'renameOutput': True,
        'outputKey': args.output_key,
    }

    rules = node['parameters']['rules']['values']
    fallback_idx = None
    for i, rule in enumerate(rules):
        if rule.get('outputKey') == 'fallback' or rule.get('outputKey') == 'Fallback':
            fallback_idx = i
            break

    if fallback_idx is not None:
        rules.insert(fallback_idx, new_rule)
    else:
        rules.append(new_rule)

    client.update_workflow(args.id, build_workflow_payload(wf, nodes))
    rule_idx = fallback_idx if fallback_idx is not None else len(rules) - 1
    print(f"Rule added to '{args.name}' at index {rule_idx}.")
    print(f"Condition: {args.field} {args.op} '{args.match_value}'")
    print(f"Output key: {args.output_key}")


def cmd_connect(client: N8nClient, args) -> None:
    """Add connection between nodes."""
    wf = client.get_workflow(args.workflow_id)
    nodes = wf.get("nodes", [])

    source_node = None
    target_node = None
    for n in nodes:
        if n.get('name') == args.source:
            source_node = n
        if n.get('name') == args.target:
            target_node = n

    if not source_node:
        print(f"Source node '{args.source}' not found.", file=sys.stderr)
        sys.exit(1)
    if not target_node:
        print(f"Target node '{args.target}' not found.", file=sys.stderr)
        sys.exit(1)

    connections = wf.get('connections', {})

    if args.source not in connections:
        connections[args.source] = {'main': []}

    main_outputs = connections[args.source]['main']

    while len(main_outputs) <= args.output:
        main_outputs.append([])

    new_connection = {
        'node': args.target,
        'type': 'main',
        'index': 0,
    }

    for conn in main_outputs[args.output]:
        if conn.get('node') == args.target:
            print(f"Connection already exists from '{args.source}' output {args.output} to '{args.target}'.")
            return

    main_outputs[args.output].append(new_connection)

    wf['connections'] = connections
    client.update_workflow(args.workflow_id, build_workflow_payload(wf, nodes))
    print(f"Connected '{args.source}' (output {args.output}) -> '{args.target}'")


def cmd_disconnect(client: N8nClient, args) -> None:
    """Remove connection between nodes."""
    wf = client.get_workflow(args.workflow_id)
    nodes = wf.get("nodes", [])

    connections = wf.get('connections', {})

    if args.source not in connections:
        print(f"No connections from '{args.source}' found.", file=sys.stderr)
        sys.exit(1)

    main_outputs = connections[args.source].get('main', [])

    if args.output is not None:
        if args.output >= len(main_outputs):
            print(f"Output index {args.output} does not exist for '{args.source}'.", file=sys.stderr)
            sys.exit(1)

        original_len = len(main_outputs[args.output])
        main_outputs[args.output] = [
            c for c in main_outputs[args.output]
            if c.get('node') != args.target
        ]
        if len(main_outputs[args.output]) == original_len:
            print(f"No connection found from '{args.source}' output {args.output} to '{args.target}'.", file=sys.stderr)
            sys.exit(1)
        print(f"Disconnected '{args.source}' (output {args.output}) -> '{args.target}'")
    else:
        removed = False
        for i, output in enumerate(main_outputs):
            original_len = len(output)
            main_outputs[i] = [c for c in output if c.get('node') != args.target]
            if len(main_outputs[i]) < original_len:
                removed = True
                print(f"Disconnected '{args.source}' (output {i}) -> '{args.target}'")
        if not removed:
            print(f"No connection found from '{args.source}' to '{args.target}'.", file=sys.stderr)
            sys.exit(1)

    wf['connections'] = connections
    client.update_workflow(args.workflow_id, build_workflow_payload(wf, nodes))


def cmd_node(client: N8nClient, args):
    wf = client.get_workflow(args.id)
    nodes = wf.get("nodes", [])

    if args.add:
        return handle_add_node(client, wf, args)

    if not args.name:
        print("Node name is required (unless using --add).", file=sys.stderr)
        sys.exit(1)

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

    if args.add_rule:
        return handle_add_switch_rule(client, wf, node, args)

    # Handle --set-param-json (bulk parameter update)
    if args.set_param_json:
        param_data = json.loads(args.set_param_json)
        if 'parameters' not in node:
            node['parameters'] = {}

        def deep_merge(base, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_merge(base[key], value)
                else:
                    base[key] = value

        deep_merge(node['parameters'], param_data)

        update_payload = {
            'name': wf['name'],
            'nodes': nodes,
            'connections': wf['connections'],
            'settings': wf.get('settings', {}),
            'staticData': wf.get('staticData'),
        }

        client.update_workflow(args.id, update_payload)
        print(f"Node '{args.name}' parameters updated.")
        return

    # Handle --set-param (single parameter update)
    if args.set_param:
        if 'parameters' not in node:
            node['parameters'] = {}

        for param in args.set_param:
            if '=' not in param:
                print(f"Invalid parameter format: {param}. Use key=value", file=sys.stderr)
                sys.exit(1)

            key, value = param.split('=', 1)

            # Try to parse value as JSON for complex types
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Keep as string

            set_nested_param(node['parameters'], key, value)

        update_payload = {
            'name': wf['name'],
            'nodes': nodes,
            'connections': wf['connections'],
            'settings': wf.get('settings', {}),
            'staticData': wf.get('staticData'),
        }

        client.update_workflow(args.id, update_payload)
        print(f"Node '{args.name}' parameters updated.")
        return

    # Handle --set-code
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


# ==================== Credentials Commands ====================


def cmd_credentials(client: N8nClient, args):
    result = client.get_all_pages(client.get_credentials)

    if args.json:
        print_json(result)
        return

    if not result:
        print("No credentials found.")
        return

    print(f"{'ID':<20} {'NAME':<40} {'TYPE':<30}")
    print("-" * 92)
    for cred in result:
        print(f"{cred['id']:<20} {cred['name'][:38]:<40} {cred.get('type', '-'):<30}")


def cmd_credential_schema(client: N8nClient, args):
    schema = client.get_credential_schema(args.type)

    if args.json:
        print_json(schema)
        return

    print(f"Schema for: {args.type}\n")

    properties = schema.get('properties', [])
    if not properties:
        print("No properties defined.")
        return

    print(f"{'NAME':<25} {'TYPE':<15} {'REQUIRED':<10} {'DESCRIPTION'}")
    print("-" * 90)
    for prop in properties:
        name = prop.get('name', prop.get('displayName', '-'))
        prop_type = prop.get('type', '-')
        required = 'yes' if prop.get('required') else 'no'
        desc = prop.get('description', '-')[:40]
        print(f"{name:<25} {prop_type:<15} {required:<10} {desc}")


def cmd_create_credential(client: N8nClient, args):
    data = {}
    if args.data:
        data = json.loads(args.data)
    elif args.data_file:
        with open(args.data_file) as f:
            data = json.load(f)

    credential = {
        'name': args.name,
        'type': args.type,
        'data': data,
    }

    result = client.create_credential(credential)

    if args.json:
        print_json(result)
        return

    print(f"Credential created: {result.get('name')}")
    print(f"ID: {result.get('id')}")
    print(f"Type: {result.get('type')}")


def cmd_delete_credential(client: N8nClient, args):
    client.delete_credential(args.id)
    print(f"Credential {args.id} deleted.")


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
    p_node = subparsers.add_parser("node", help="View, edit, or create nodes")
    p_node.add_argument("id", help="Workflow ID")
    p_node.add_argument("name", nargs="?", help="Node name (required except with --add)")
    p_node.add_argument("--code", "-c", action="store_true", help="Show node code (Code nodes only)")
    p_node.add_argument("--set-code", "-s", metavar="FILE", help="Update node code from file")
    p_node.add_argument("--set-param", "-p", action="append", metavar="KEY=VALUE", help="Set a node parameter (can be used multiple times, supports dot notation for nested keys)")
    p_node.add_argument("--set-param-json", metavar="JSON", help="Set node parameters from JSON object (deep merged)")
    p_node.add_argument("--rename", "-r", metavar="NAME", help="Rename the node")
    p_node.add_argument("--json", action="store_true", help="Output as JSON")
    p_node.add_argument("--add", action="store_true", help="Create a new node")
    p_node.add_argument("--type", dest="node_type", help="Node type for --add (e.g., 'code', 'switch', or full type)")
    p_node.add_argument("--name", dest="new_name", metavar="NAME", help="Node name for --add")
    p_node.add_argument("--position", help="Position as X,Y for --add")
    p_node.add_argument("--param", action="append", metavar="KEY=VALUE", help="Set a parameter for new node (--add)")
    p_node.add_argument("--add-rule", action="store_true", help="Add rule to Switch node")
    p_node.add_argument("--field", help="Field to match for --add-rule (e.g., 'title')")
    p_node.add_argument("--op", choices=["contains", "equals", "not-equals", "starts-with", "ends-with", "regex"],
                        help="Match operator for --add-rule")
    p_node.add_argument("--match-value", help="Value to match for --add-rule")
    p_node.add_argument("--output-key", help="Output key name for --add-rule")
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

    # connect
    p_connect = subparsers.add_parser("connect", help="Add connection between nodes")
    p_connect.add_argument("workflow_id", help="Workflow ID")
    p_connect.add_argument("source", help="Source node name")
    p_connect.add_argument("target", help="Target node name")
    p_connect.add_argument("--output", type=int, default=0, help="Output index (default: 0)")
    p_connect.set_defaults(func=cmd_connect)

    # disconnect
    p_disconnect = subparsers.add_parser("disconnect", help="Remove connection between nodes")
    p_disconnect.add_argument("workflow_id", help="Workflow ID")
    p_disconnect.add_argument("source", help="Source node name")
    p_disconnect.add_argument("target", help="Target node name")
    p_disconnect.add_argument("--output", type=int, help="Output index (removes from specific output)")
    p_disconnect.set_defaults(func=cmd_disconnect)

    # credentials
    p_credentials = subparsers.add_parser("credentials", help="List all credentials")
    p_credentials.add_argument("--json", action="store_true", help="Output as JSON")
    p_credentials.set_defaults(func=cmd_credentials)

    # credential-schema
    p_cred_schema = subparsers.add_parser("credential-schema", help="Get schema for a credential type")
    p_cred_schema.add_argument("type", help="Credential type (e.g., httpHeaderAuth, openAiApi)")
    p_cred_schema.add_argument("--json", action="store_true", help="Output as JSON")
    p_cred_schema.set_defaults(func=cmd_credential_schema)

    # create-credential
    p_create_cred = subparsers.add_parser("create-credential", help="Create a new credential")
    p_create_cred.add_argument("--name", "-n", required=True, help="Credential name")
    p_create_cred.add_argument("--type", "-t", required=True, help="Credential type")
    p_create_cred.add_argument("--data", "-d", help="Credential data as JSON string")
    p_create_cred.add_argument("--data-file", "-f", help="File containing credential data as JSON")
    p_create_cred.add_argument("--json", action="store_true", help="Output as JSON")
    p_create_cred.set_defaults(func=cmd_create_credential)

    # delete-credential
    p_delete_cred = subparsers.add_parser("delete-credential", help="Delete a credential")
    p_delete_cred.add_argument("id", help="Credential ID")
    p_delete_cred.set_defaults(func=cmd_delete_credential)

    args = parser.parse_args()

    try:
        client = N8nClient()
        args.func(client, args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
