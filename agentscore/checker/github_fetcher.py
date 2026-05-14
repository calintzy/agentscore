from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import os

import httpx

GITHUB_API = "https://api.github.com"
RAW_BASE = "https://raw.githubusercontent.com"
TIMEOUT = 15.0


def _make_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@dataclass
class RepoInfo:
    owner: str
    repo: str
    stars: int
    description: str
    license: str
    default_branch: str
    last_pushed_at: str
    open_issues: int
    topics: list[str]
    files: list[str]
    readme: str
    claude_md: str
    raw_files: dict[str, str] = field(default_factory=dict)


def parse_github_url(url: str) -> tuple[str, str]:
    url = url.strip().rstrip("/")
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.\s]+?)(?:\.git)?$",
        r"^([^/]+)/([^/.\s]+)$",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1), m.group(2)
    raise ValueError(f"GitHub URL 파싱 실패: {url}")


def fetch_repo_info(url: str) -> RepoInfo:
    owner, repo = parse_github_url(url)

    with httpx.Client(timeout=TIMEOUT, headers=_make_headers()) as client:
        resp = client.get(f"{GITHUB_API}/repos/{owner}/{repo}")
        resp.raise_for_status()
        data = resp.json()

        branch = data.get("default_branch", "main")

        contents_resp = client.get(f"{GITHUB_API}/repos/{owner}/{repo}/contents/")
        files = []
        if contents_resp.status_code == 200:
            files = [f["name"] for f in contents_resp.json() if isinstance(f, dict)]

        readme = _fetch_raw(client, owner, repo, branch, "README.md")
        claude_md = _fetch_raw(client, owner, repo, branch, "CLAUDE.md") or \
                    _fetch_raw(client, owner, repo, branch, ".claude/CLAUDE.md")

        raw_files: dict[str, str] = {}
        for fname in ["pyproject.toml", "package.json", "mcp.json", ".mcp.json"]:
            content = _fetch_raw(client, owner, repo, branch, fname)
            if content:
                raw_files[fname] = content

    license_name = ""
    if data.get("license"):
        license_name = data["license"].get("spdx_id") or data["license"].get("name", "")

    return RepoInfo(
        owner=owner,
        repo=repo,
        stars=data.get("stargazers_count", 0),
        description=data.get("description") or "",
        license=license_name,
        default_branch=branch,
        last_pushed_at=data.get("pushed_at") or "",
        open_issues=data.get("open_issues_count", 0),
        topics=data.get("topics") or [],
        files=files,
        readme=readme,
        claude_md=claude_md,
        raw_files=raw_files,
    )


def _fetch_raw(client: httpx.Client, owner: str, repo: str, branch: str, path: str) -> str:
    try:
        r = client.get(f"{RAW_BASE}/{owner}/{repo}/{branch}/{path}")
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""
