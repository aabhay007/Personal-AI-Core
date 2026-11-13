"""Async GitHub API client for repository synchronization and inspection."""
import base64
import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Client for interacting with GitHub REST API v3."""

    def __init__(self, token: Optional[str] = None):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Personal-AI-Core-Developer-Assistant",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.headers = headers

    async def test_connection(self, owner: Optional[str] = None, repo: Optional[str] = None) -> Dict[str, Any]:
        """Test authentication or repository accessibility."""
        async with httpx.AsyncClient(timeout=10.0, headers=self.headers) as client:
            try:
                if owner and repo:
                    res = await client.get(f"{GITHUB_API_BASE}/repos/{owner}/{repo}")
                else:
                    res = await client.get(f"{GITHUB_API_BASE}/user")

                if res.status_code == 200:
                    data = res.json()
                    return {
                        "success": True,
                        "login": data.get("login") or data.get("owner", {}).get("login"),
                        "name": data.get("name") or data.get("full_name"),
                        "rate_limit_remaining": res.headers.get("x-ratelimit-remaining"),
                        "error": None
                    }
                else:
                    err_msg = res.json().get("message", res.text)
                    return {
                        "success": False,
                        "error": f"GitHub API error ({res.status_code}): {err_msg}"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to connect to GitHub: {str(e)}"
                }

    async def get_tree(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve the git commit tree for the repository branch."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}"
        params = {"recursive": "1"} if recursive else {}

        async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
            res = await client.get(url, params=params)
            if res.status_code != 200:
                raise ValueError(f"Failed to fetch repository tree: {res.text}")
            tree_data = res.json()
            return tree_data.get("tree", [])

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = "main"
    ) -> Optional[str]:
        """Fetch and decode a text file's contents from GitHub."""
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": branch}

        async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
            res = await client.get(url, params=params)
            if res.status_code != 200:
                return None
            data = res.json()
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    raw_bytes = base64.b64decode(data["content"])
                    return raw_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    logger.warning(f"Failed to decode file {path}: {e}")
                    return None
            return None
