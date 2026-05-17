from __future__ import annotations
import base64
import json
from pathlib import Path

import httpx

_GH_API = "https://api.github.com"


async def push_files_to_github(
    files: dict[str, str],  # {repo_path: content_str}
    commit_message: str,
    github_token: str,
    repo: str,  # "richaqp/sortirs-paris"
    branch: str = "main",
) -> str | None:
    """Push one or more text files to GitHub via the Contents API. Returns commit SHA or None."""
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    pushed = []
    async with httpx.AsyncClient(timeout=30) as client:
        for repo_path, content in files.items():
            encoded = base64.b64encode(content.encode()).decode()
            url = f"{_GH_API}/repos/{repo}/contents/{repo_path}"

            # Get current SHA if file exists (needed for updates)
            r = await client.get(url, headers=headers, params={"ref": branch})
            sha = r.json().get("sha") if r.status_code == 200 else None

            body: dict = {
                "message": commit_message,
                "content": encoded,
                "branch": branch,
            }
            if sha:
                body["sha"] = sha

            r = await client.put(url, headers=headers, json=body)
            if r.status_code in (200, 201):
                pushed.append(repo_path)
                commit_sha = r.json().get("commit", {}).get("sha", "")[:7]
            else:
                print(f"  [github] Error {r.status_code} en {repo_path}: {r.text[:120]}")
                return None

    if pushed:
        print(f"  [github] Pusheado: {', '.join(pushed)} → {commit_sha}")
        return commit_sha
    return None
