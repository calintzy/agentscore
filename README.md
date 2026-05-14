# agentscore

> **Lighthouse for AI agent development environments**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/calintzy/agentscore?style=flat)](https://github.com/calintzy/agentscore/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/calintzy/agentscore)](https://github.com/calintzy/agentscore/issues)

**Language:** [한국어](README.ko.md) | English | [中文](README.zh.md)

A CLI tool that analyzes Claude Code users' MCP servers, plugins, and skill environments — scoring them and suggesting improvements.

```
$ agentscore

  Grade A  82.0pts  Profile: backend

 Context Efficiency   17.0  /25  ████████░░░░
 Coverage             20.0  /20  ████████████
 Conflict Detection   12.0  /20  ███████░░░░░
 Config Quality       15.0  /15  ████████████
 Security              8.0  /10  █████████░░░
 Freshness            10.0  /10  ████████████
```

## Why agentscore?

Claude Code environments have grown as complex as Kubernetes clusters, yet there's no equivalent of `kubectl describe` to diagnose them.

| Problem | Description |
|---------|-------------|
| No visibility | No way to know if your setup is healthy |
| Unknown gaps | Critical tools may be missing without you knowing |
| Hidden conflicts | 3 of your 20 plugins might be conflicting |
| Context waste | No idea which tools are silently burning context |

## Installation

```bash
pip install agentscore-cli
```

**Requirements:** Python 3.11+, Claude Code installed

Or install from source:

```bash
git clone https://github.com/calintzy/agentscore
cd agentscore
pip install -e .
```

**Requirements:** Python 3.11+, Claude Code installed

## Usage

```bash
# Instant scan (auto-detect profile)
agentscore

# Specify role explicitly
agentscore --profile backend

# JSON output
agentscore --json

# No color (for CI environments)
agentscore --no-color

# Simulate impact before installing a new tool
agentscore check https://github.com/upstash/context7

# View score history
agentscore history

# Compare against a previous snapshot
agentscore diff
agentscore diff 2026-05-01

# Save profile setting
agentscore setup

# Show version
agentscore --version
```

## Scoring (100 points total)

| Dimension | Points | Description |
|-----------|--------|-------------|
| Context Efficiency | 25 | CLAUDE.md size, dead-weight tools, duplicate instructions |
| Coverage | 20 | Required tool category coverage for your profile |
| Conflict Detection | 20 | Duplicate tools providing the same capability |
| Config Quality | 15 | Model setting, inactive plugins, CLAUDE.md presence |
| Security | 10 | Dangerous permission patterns (`Bash(*)`, `Bash(sudo:*)`, etc.) |
| Freshness | 10 | Plugin last-updated timestamps |

### Grades

| Grade | Score | Meaning |
|-------|-------|---------|
| S | 90-100 | Optimized environment |
| A | 75-89 | Well configured, minor improvements needed |
| B | 55-74 | Basics covered, important improvements needed |
| C | 35-54 | Significant gaps exist |
| D | 0-34 | Reconfiguration recommended |

## Context ROI

Measures context cost as a **value-to-cost ratio**, not an absolute value.

```
Context ROI = (Profile Fit × 0.6 + Config Priority × 0.4) / Context Cost
```

- ROI < 0.3: **Dead Weight** — high-cost tool you're not using (penalty)
- ROI > 2.0 + low cost: **Ideal** — high value at low cost (bonus)

### Config Priority Signals

Measures "how intentionally are you using this?" from config files alone — no log parsing.

| Signal | Priority |
|--------|----------|
| Directly mentioned in CLAUDE.md | High |
| Activated in `enabledPlugins` | Medium |
| Registered in `enabledMcpjsonServers` | Medium |
| Configured in `mcp.json` | Medium |
| Installed but nowhere else | Low |

## Profile System

```bash
agentscore                    # Tier 0: generic (instant, no profile)
agentscore --profile backend  # Tier 1: role-based evaluation
agentscore setup              # Save role → applied automatically afterwards
```

Supported roles: `backend`, `frontend`, `fullstack`, `ml`, `devops`

Without a profile, agentscore auto-detects from file patterns in the current directory (many `.py` files → backend/ml, `package.json` → frontend, `Dockerfile` + k8s manifests → devops).

## agentscore check

Analyze the impact of a new GitHub project before installing it.

```bash
$ agentscore check https://github.com/some-org/some-tool

agentscore check — some-org/some-tool
⭐ 1,234 stars  📄 MIT  🟢 Recently updated

✅ Installation recommended  +3.0pts improvement expected

Score prediction:  82.0 → 85.0 (+3.0)

 Dimension               Before   After   Delta
 Context Efficiency       17.0     17.0     —
 Coverage                 20.0     20.0     —
 Conflict Detection       12.0     14.0   +2.0
 ...
```

## History

```bash
agentscore history        # Last 10 score snapshots
agentscore history --limit 30

agentscore diff           # Compare with previous scan
agentscore diff 2026-05-01  # Compare with specific date
```

History is stored in `~/.agentscore/history/` and auto-pruned after 30 days.

## Design Principles

1. **Zero context overhead** — agentscore itself never adds context to Claude Code sessions
2. **On-demand only** — completely silent during normal use, runs only when invoked
3. **Local only** — all data stored in `~/.agentscore/`, no external servers
4. **Honest estimates** — uncertain values are marked as "(estimated)"

## Scanned Files

```
~/.claude/settings.json              enabledPlugins, model settings
~/.claude/settings.local.json        permissions.allow, enabledMcpjsonServers
~/.claude/mcp.json                   MCP server list
~/.claude/CLAUDE.md                  Global instructions
~/.claude/plugins/installed_plugins.json  Installed plugins + update timestamps
.claude/CLAUDE.md                    Project-level instructions
CLAUDE.md                            Project root instructions
```

## Tech Stack

- **Python 3.11+**
- `click` — CLI framework
- `rich` — terminal output
- `httpx` — GitHub API (for `agentscore check`)
- stdlib only: `json`, `pathlib`, `re`, `datetime`

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub personal access token (raises rate limit from 60 to 5,000 req/hr for `agentscore check`) |

## License

MIT
