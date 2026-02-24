"""
VOLO — GitHub Integration Service
Live GitHub API interaction for managing repos, PRs, issues.
"""

import os
from typing import Optional
import httpx


class GitHubService:
    """Handles all GitHub API calls."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def headers(self) -> dict:
        h = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=self.headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _check_token(self) -> Optional[dict]:
        """Return error dict if no token configured."""
        if not self.token:
            return {
                "error": "GitHub not connected. Ask the user to provide a GitHub Personal Access Token.",
                "setup_hint": "Go to github.com/settings/tokens → Generate new token (classic) → scopes: repo, read:org, read:user",
            }
        return None

    async def list_repos(
        self, sort: str = "updated", limit: int = 20
    ) -> dict:
        """List authenticated user's repos."""
        err = self._check_token()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(
            "/user/repos",
            params={
                "sort": sort,
                "per_page": min(limit, 100),
                "type": "all",
            },
        )

        if resp.status_code != 200:
            return {"error": f"GitHub API error: {resp.status_code} — {resp.text[:200]}"}

        repos = resp.json()
        return {
            "repos": [
                {
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "description": r.get("description", ""),
                    "language": r.get("language", ""),
                    "stars": r.get("stargazers_count", 0),
                    "forks": r.get("forks_count", 0),
                    "open_issues": r.get("open_issues_count", 0),
                    "private": r.get("private", False),
                    "updated_at": r.get("updated_at", ""),
                    "html_url": r.get("html_url", ""),
                }
                for r in repos
            ],
            "total": len(repos),
        }

    async def get_repo(self, repo: str) -> dict:
        """Get detailed info about a specific repo (owner/name format)."""
        err = self._check_token()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(f"/repos/{repo}")

        if resp.status_code != 200:
            return {"error": f"Repo not found or access denied: {repo}"}

        r = resp.json()

        # Also fetch recent commits
        commits_resp = await client.get(
            f"/repos/{repo}/commits", params={"per_page": 5}
        )
        recent_commits = []
        if commits_resp.status_code == 200:
            for c in commits_resp.json()[:5]:
                recent_commits.append({
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                })

        # Fetch languages
        lang_resp = await client.get(f"/repos/{repo}/languages")
        languages = lang_resp.json() if lang_resp.status_code == 200 else {}

        return {
            "name": r["name"],
            "full_name": r["full_name"],
            "description": r.get("description", ""),
            "language": r.get("language", ""),
            "languages": languages,
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "open_issues": r.get("open_issues_count", 0),
            "default_branch": r.get("default_branch", "main"),
            "private": r.get("private", False),
            "created_at": r.get("created_at", ""),
            "updated_at": r.get("updated_at", ""),
            "html_url": r.get("html_url", ""),
            "clone_url": r.get("clone_url", ""),
            "topics": r.get("topics", []),
            "recent_commits": recent_commits,
        }

    async def list_prs(
        self, repo: str, state: str = "open"
    ) -> dict:
        """List pull requests for a repo."""
        err = self._check_token()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get(
            f"/repos/{repo}/pulls",
            params={"state": state, "per_page": 20},
        )

        if resp.status_code != 200:
            return {"error": f"Could not fetch PRs for {repo}"}

        prs = resp.json()
        return {
            "repo": repo,
            "state": state,
            "pull_requests": [
                {
                    "number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "author": pr["user"]["login"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"],
                    "html_url": pr["html_url"],
                    "draft": pr.get("draft", False),
                    "labels": [l["name"] for l in pr.get("labels", [])],
                }
                for pr in prs
            ],
            "total": len(prs),
        }

    async def get_user(self) -> dict:
        """Get authenticated user profile."""
        err = self._check_token()
        if err:
            return err

        client = await self._get_client()
        resp = await client.get("/user")

        if resp.status_code != 200:
            return {"error": "Failed to authenticate with GitHub"}

        u = resp.json()
        return {
            "login": u["login"],
            "name": u.get("name", ""),
            "avatar_url": u.get("avatar_url", ""),
            "bio": u.get("bio", ""),
            "public_repos": u.get("public_repos", 0),
            "followers": u.get("followers", 0),
            "following": u.get("following", 0),
        }
