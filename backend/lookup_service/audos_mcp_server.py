# audos_mcp_server.py

from typing import Any, Dict, List
import os
import httpx
from fastmcp import FastMCP

# This name will show up in Cursor
mcp = FastMCP("audos-dev")

# Use the folder this file lives in as the project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Your app.py does app.run(debug=True), so default is port 5000
BACKEND_URL = "http://localhost:5000"


# ---------- FILESYSTEM TOOLS ----------

@mcp.tool
def list_repo_files(subdir: str = "") -> List[str]:
    """
    List files under the project root (relative paths).
    Use `subdir` to narrow (e.g. 'react-business-lookup', 'lookup', etc.).
    """
    base = os.path.join(PROJECT_ROOT, subdir)
    results: List[str] = []
    for root, _, files in os.walk(base):
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, PROJECT_ROOT)
            results.append(rel_path)
    return results


@mcp.tool
def read_repo_file(path: str) -> str:
    """
    Read a file from the repo (path is relative to PROJECT_ROOT).
    """
    full_path = os.path.join(PROJECT_ROOT, path)
    if not full_path.startswith(PROJECT_ROOT):
        raise ValueError("Path escapes project root")
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------- LIVE LOOKUP TOOLS (matching your app.py) ----------

@mcp.tool
def lookup_single(business_id: str) -> Dict[str, Any]:
    """
    Call the live /lookup-single endpoint with a business_id.
    """
    url = BACKEND_URL + "/lookup-single"
    payload = {"business_id": business_id}
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


@mcp.tool
def lookup_bulk(business_ids: List[str]) -> Dict[str, Any]:
    """
    Call the live /lookup-bulk endpoint with a list of business_ids.
    """
    url = BACKEND_URL + "/lookup-bulk"
    payload = {"business_ids": business_ids}
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    # Start MCP server over stdio (what Cursor expects)
    mcp.run()
