"""
GitHub repository helper utilities.

This module provides a `GitHubFetcher` class that talks to the GitHub REST API
using a personal access token from the `GITHUB_TOKEN` environment variable.

Features:
- Parse GitHub repo URLs
- Fetch basic repo info
- List the repository file tree
- Locate important project files (README, requirements, etc.)
- Download file contents
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


load_dotenv()


@dataclass
class GitHubRepoInfo:
    name: str
    description: Optional[str]
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]


class GitHubFetcher:
    """
    Helper class for interacting with the GitHub API.

    Expects a personal access token in the `GITHUB_TOKEN` environment variable.
    """

    def __init__(self, token: Optional[str] = None, base_url: str = "https://api.github.com") -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise RuntimeError(
                "GITHUB_TOKEN is not set. Please add it to your environment or .env file."
            )

        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "codoc-github-fetcher",
            }
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Perform a GET request to the GitHub API with basic error handling."""
        url = path
        if not url.startswith("http"):
            url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            resp = self.session.get(url, params=params, timeout=15)
        except requests.RequestException as exc:
            raise RuntimeError(f"Network error while calling GitHub API: {exc}") from exc

        if resp.status_code == 404:
            raise RuntimeError(f"GitHub resource not found: {url}")
        if resp.status_code == 401:
            raise RuntimeError("Unauthorized. Check that your GITHUB_TOKEN is valid.")
        if resp.status_code == 403:
            raise RuntimeError(
                "Forbidden or rate-limited by GitHub. You may have exceeded rate limits."
            )
        if not resp.ok:
            raise RuntimeError(f"GitHub API error ({resp.status_code}): {resp.text}")

        try:
            return resp.json()
        except ValueError:
            # Some endpoints (like raw content) may not be JSON
            return resp.text

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    @staticmethod
    def parse_url(github_url: str) -> Tuple[str, str]:
        """
        Extract `owner` and `repo` from a GitHub repository URL.

        Examples:
        - https://github.com/octocat/Hello-World
        - https://github.com/octocat/Hello-World/
        - https://github.com/octocat/Hello-World.git
        """
        parsed = urlparse(github_url)
        if "github.com" not in (parsed.netloc or ""):
            raise ValueError(f"Not a GitHub URL: {github_url}")

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise ValueError(f"Could not parse owner/repo from URL: {github_url}")

        owner = parts[0]
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]

        return owner, repo

    def get_repo_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch basic repository metadata.

        Returns a dict with:
        - name
        - description
        - stars
        - forks
        - language
        - topics
        """
        data = self._get(f"/repos/{owner}/{repo}")

        info = GitHubRepoInfo(
            name=data.get("name", f"{owner}/{repo}"),
            description=data.get("description"),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            language=data.get("language"),
            topics=data.get("topics", []),
        )
        return {
            "name": info.name,
            "description": info.description,
            "stars": info.stars,
            "forks": info.forks,
            "language": info.language,
            "topics": info.topics,
        }

    def _get_default_branch(self, owner: str, repo: str) -> str:
        """Helper to obtain the repository's default branch name."""
        data = self._get(f"/repos/{owner}/{repo}")
        default_branch = data.get("default_branch")
        if not default_branch:
            raise RuntimeError("Could not determine default branch for repository.")
        return default_branch

    def get_file_tree(self, owner: str, repo: str, path: str = "") -> List[Dict[str, Any]]:
        """
        Recursively list all files in the repository (optionally under `path`).

        Uses the Git Trees API for efficiency.
        """
        branch = self._get_default_branch(owner, repo)
        tree_data = self._get(f"/repos/{owner}/{repo}/git/trees/{branch}", params={"recursive": 1})

        if "tree" not in tree_data:
            raise RuntimeError("Unexpected tree response from GitHub.")

        files: List[Dict[str, Any]] = []
        prefix = path.rstrip("/").lstrip("/")
        for item in tree_data["tree"]:
            if item.get("type") != "blob":
                continue

            file_path = item.get("path", "")
            if prefix and not file_path.startswith(prefix + "/") and file_path != prefix:
                continue

            files.append(
                {
                    "path": file_path,
                    "mode": item.get("mode"),
                    "type": item.get("type"),
                    "size": item.get("size"),
                    "sha": item.get("sha"),
                    "url": item.get("url"),
                }
            )

        return files

    def get_important_files(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """
        Return metadata for commonly important project files, such as:
        - README.*
        - requirements.txt
        - pyproject.toml
        - package.json
        - Pipfile
        - setup.py
        """
        important_names = {
            "README",
            "README.md",
            "README.rst",
            "requirements.txt",
            "pyproject.toml",
            "setup.py",
            "Pipfile",
            "Pipfile.lock",
            "package.json",
        }

        tree = self.get_file_tree(owner, repo)
        matches: List[Dict[str, Any]] = []

        for item in tree:
            path = item["path"]
            filename = path.split("/")[-1]
            if filename in important_names:
                # Use the contents API to get a download URL
                content_data = self._get(f"/repos/{owner}/{repo}/contents/{path}")
                download_url = content_data.get("download_url")
                matches.append(
                    {
                        "path": path,
                        "download_url": download_url,
                        "type": item.get("type"),
                        "size": item.get("size"),
                        "sha": item.get("sha"),
                    }
                )

        return matches

    def get_file_content(self, file_url: str) -> str:
        """
        Download and return the content of a file.

        `file_url` can be:
        - A `download_url` returned from the GitHub contents API
        - A regular GitHub `blob` URL (e.g., https://github.com/owner/repo/blob/branch/path)
        """
        # If it's a GitHub "blob" URL, convert it to a raw URL
        parsed = urlparse(file_url)
        if "github.com" in (parsed.netloc or "") and "/blob/" in parsed.path:
            # /owner/repo/blob/branch/path/to/file
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 5:
                owner, repo, _blob, branch = parts[:4]
                file_path = "/".join(parts[4:])
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}"
                file_url = raw_url

        try:
            resp = self.session.get(file_url, timeout=15)
        except requests.RequestException as exc:
            raise RuntimeError(f"Network error while downloading file: {exc}") from exc

        if not resp.ok:
            raise RuntimeError(
                f"Failed to download file ({resp.status_code}): {resp.text[:200]}"
            )

        return resp.text


if __name__ == "__main__":
    """
    Simple manual test using https://github.com/octocat/Hello-World.

    Run from project root:
        python -m backend.github_fetcher
    """

    TEST_URL = "https://github.com/octocat/Hello-World"

    fetcher = GitHubFetcher()
    owner, repo = fetcher.parse_url(TEST_URL)
    print(f"Parsed URL -> owner={owner}, repo={repo}")

    print("\n=== Repository info ===")
    repo_info = fetcher.get_repo_info(owner, repo)
    print(repo_info)

    print("\n=== File tree (first 10 files) ===")
    files = fetcher.get_file_tree(owner, repo)
    for f in files[:10]:
        print(f["path"])
    print(f"... total files: {len(files)}")

    print("\n=== Important files ===")
    important = fetcher.get_important_files(owner, repo)
    for item in important:
        print(f"- {item['path']} (download_url={item.get('download_url')})")

    if important and important[0].get("download_url"):
        print("\n=== First important file content (truncated) ===")
        content = fetcher.get_file_content(important[0]["download_url"])
        print(content[:400])
    else:
        print("\nNo important files with download URLs found.")

