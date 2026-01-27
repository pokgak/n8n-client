"""
n8n API Client - Python wrapper for n8n REST API

Usage:
    from n8n_client import N8nClient

    client = N8nClient()  # Uses N8N_API_KEY and N8N_BASE_URL env vars
    # or
    client = N8nClient(api_key="your-key", base_url="https://your-instance.app.n8n.cloud")

    workflows = client.get_workflows()
    executions = client.get_executions(workflow_id="123")
"""

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class PaginatedResponse:
    data: list[dict[str, Any]]
    next_cursor: str | None


class N8nClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        self.api_key = api_key or os.environ.get("N8N_API_KEY")
        self.base_url = (base_url or os.environ.get("N8N_BASE_URL", "")).rstrip("/")

        if not self.api_key:
            raise ValueError("API key required. Set N8N_API_KEY env var or pass api_key parameter.")
        if not self.base_url:
            raise ValueError("Base URL required. Set N8N_BASE_URL env var or pass base_url parameter.")

        self._client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"X-N8N-API-KEY": self.api_key},
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
    ) -> dict[str, Any]:
        response = self._client.request(method, path, params=params, json=json)
        response.raise_for_status()
        return response.json()

    def _paginated_request(
        self,
        path: str,
        params: dict | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedResponse:
        params = params or {}
        if limit:
            params["limit"] = limit
        if cursor:
            params["cursor"] = cursor

        result = self._request("GET", path, params=params)
        return PaginatedResponse(
            data=result.get("data", []),
            next_cursor=result.get("nextCursor"),
        )

    # ==================== Workflows ====================

    def get_workflows(
        self,
        active: bool | None = None,
        tags: str | None = None,
        name: str | None = None,
        project_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedResponse:
        """Retrieve all workflows."""
        params = {}
        if active is not None:
            params["active"] = active
        if tags:
            params["tags"] = tags
        if name:
            params["name"] = name
        if project_id:
            params["projectId"] = project_id
        return self._paginated_request("/workflows", params, limit, cursor)

    def get_workflow(self, workflow_id: str, exclude_pinned_data: bool = False) -> dict[str, Any]:
        """Retrieve a specific workflow by ID."""
        params = {}
        if exclude_pinned_data:
            params["excludePinnedData"] = True
        return self._request("GET", f"/workflows/{workflow_id}", params=params)

    def create_workflow(self, workflow: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow."""
        return self._request("POST", "/workflows", json=workflow)

    def update_workflow(self, workflow_id: str, workflow: dict[str, Any]) -> dict[str, Any]:
        """Update an existing workflow."""
        return self._request("PUT", f"/workflows/{workflow_id}", json=workflow)

    def delete_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Delete a workflow."""
        return self._request("DELETE", f"/workflows/{workflow_id}")

    def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Activate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/activate")

    def deactivate_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Deactivate a workflow."""
        return self._request("POST", f"/workflows/{workflow_id}/deactivate")

    def run_workflow(self, workflow_id: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute a workflow manually.

        Args:
            workflow_id: The workflow to run
            data: Optional input data to pass to the workflow
        """
        json_data = {}
        if data:
            json_data["data"] = data
        return self._request("POST", f"/workflows/{workflow_id}/run", json=json_data or None)

    def transfer_workflow(self, workflow_id: str, project_id: str) -> None:
        """Transfer a workflow to a different project."""
        self._client.request(
            "PUT",
            f"/api/v1/workflows/{workflow_id}/transfer",
            json={"destinationProjectId": project_id},
        ).raise_for_status()

    def get_workflow_tags(self, workflow_id: str) -> list[dict[str, Any]]:
        """Get tags for a workflow."""
        return self._request("GET", f"/workflows/{workflow_id}/tags")

    def update_workflow_tags(self, workflow_id: str, tag_ids: list[str]) -> list[dict[str, Any]]:
        """Update tags for a workflow."""
        return self._request("PUT", f"/workflows/{workflow_id}/tags", json=tag_ids)

    # ==================== Executions ====================

    def get_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
        project_id: str | None = None,
        include_data: bool = False,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedResponse:
        """
        Retrieve executions.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status (canceled, error, running, success, waiting)
            project_id: Filter by project ID
            include_data: Include execution data in response
            limit: Max results per page
            cursor: Pagination cursor
        """
        params = {}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        if project_id:
            params["projectId"] = project_id
        if include_data:
            params["includeData"] = True
        return self._paginated_request("/executions", params, limit, cursor)

    def get_execution(self, execution_id: str, include_data: bool = False) -> dict[str, Any]:
        """Retrieve a specific execution by ID."""
        params = {}
        if include_data:
            params["includeData"] = True
        return self._request("GET", f"/executions/{execution_id}", params=params)

    def delete_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an execution."""
        return self._request("DELETE", f"/executions/{execution_id}")

    def retry_execution(self, execution_id: str, load_workflow: bool = False) -> dict[str, Any]:
        """
        Retry an execution.

        Args:
            execution_id: The execution to retry
            load_workflow: If True, use current workflow version instead of the one from execution time
        """
        json_data = {}
        if load_workflow:
            json_data["loadWorkflow"] = True
        return self._request("POST", f"/executions/{execution_id}/retry", json=json_data or None)

    # ==================== Tags ====================

    def get_tags(self, limit: int | None = None, cursor: str | None = None) -> PaginatedResponse:
        """Retrieve all tags."""
        return self._paginated_request("/tags", limit=limit, cursor=cursor)

    def get_tag(self, tag_id: str) -> dict[str, Any]:
        """Retrieve a specific tag by ID."""
        return self._request("GET", f"/tags/{tag_id}")

    def create_tag(self, name: str) -> dict[str, Any]:
        """Create a new tag."""
        return self._request("POST", "/tags", json={"name": name})

    def update_tag(self, tag_id: str, name: str) -> dict[str, Any]:
        """Update a tag."""
        return self._request("PUT", f"/tags/{tag_id}", json={"name": name})

    def delete_tag(self, tag_id: str) -> dict[str, Any]:
        """Delete a tag."""
        return self._request("DELETE", f"/tags/{tag_id}")

    # ==================== Credentials ====================

    def get_credentials(
        self,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedResponse:
        """Retrieve all credentials (metadata only, not secret values)."""
        return self._paginated_request("/credentials", limit=limit, cursor=cursor)

    def create_credential(self, credential: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new credential.

        Args:
            credential: Dict with 'name', 'type', and 'data' fields.
                       Example: {'name': 'My API Key', 'type': 'httpHeaderAuth', 'data': {'name': 'X-API-Key', 'value': 'secret'}}
        """
        return self._request("POST", "/credentials", json=credential)

    def delete_credential(self, credential_id: str) -> dict[str, Any]:
        """Delete a credential."""
        return self._request("DELETE", f"/credentials/{credential_id}")

    def get_credential_schema(self, credential_type: str) -> dict[str, Any]:
        """Get the schema for a credential type."""
        return self._request("GET", f"/credentials/schema/{credential_type}")

    # ==================== Users ====================

    def get_users(self, limit: int | None = None, cursor: str | None = None) -> PaginatedResponse:
        """Retrieve all users."""
        return self._paginated_request("/users", limit=limit, cursor=cursor)

    # ==================== Audit ====================

    def generate_audit(
        self,
        days_abandoned_workflow: int | None = None,
        categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a security audit.

        Args:
            days_abandoned_workflow: Days for workflow to be considered abandoned
            categories: List of categories to audit (credentials, database, nodes, filesystem, instance)
        """
        json_data = {}
        if days_abandoned_workflow or categories:
            json_data["additionalOptions"] = {}
            if days_abandoned_workflow:
                json_data["additionalOptions"]["daysAbandonedWorkflow"] = days_abandoned_workflow
            if categories:
                json_data["additionalOptions"]["categories"] = categories
        return self._request("POST", "/audit", json=json_data or None)

    # ==================== Variables ====================

    def get_variables(self) -> list[dict[str, Any]]:
        """Retrieve all variables."""
        return self._request("GET", "/variables")

    def create_variable(self, key: str, value: str) -> dict[str, Any]:
        """Create a new variable."""
        return self._request("POST", "/variables", json={"key": key, "value": value})

    def delete_variable(self, variable_id: str) -> dict[str, Any]:
        """Delete a variable."""
        return self._request("DELETE", f"/variables/{variable_id}")

    # ==================== Projects ====================

    def get_projects(self, limit: int | None = None, cursor: str | None = None) -> PaginatedResponse:
        """Retrieve all projects."""
        return self._paginated_request("/projects", limit=limit, cursor=cursor)

    # ==================== Utilities ====================

    def get_all_pages(
        self,
        method,
        *args,
        max_pages: int = 100,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        Fetch all pages from a paginated endpoint.

        Args:
            method: The paginated method to call (e.g., client.get_workflows)
            max_pages: Maximum number of pages to fetch (safety limit)
            *args, **kwargs: Arguments to pass to the method

        Returns:
            Combined list of all items from all pages
        """
        all_data = []
        cursor = None

        for _ in range(max_pages):
            result = method(*args, cursor=cursor, **kwargs)
            all_data.extend(result.data)

            if not result.next_cursor:
                break
            cursor = result.next_cursor

        return all_data

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
