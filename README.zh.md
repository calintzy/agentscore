# agentscore

> **AI 代理开发环境的灯塔**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/calintzy/agentscore?style=flat)](https://github.com/calintzy/agentscore/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/calintzy/agentscore)](https://github.com/calintzy/agentscore/issues)

**语言：** [한국어](README.ko.md) | [English](README.md) | 中文

分析 Claude Code 用户的 MCP 服务器、插件和技能环境，提供评分和改进建议的 CLI 工具。

```
$ agentscore

  A 级  82.0分  配置文件: backend

 Context Efficiency   17.0  /25  ████████░░░░
 Coverage             20.0  /20  ████████████
 Conflict Detection   12.0  /20  ███████░░░░░
 Config Quality       15.0  /15  ████████████
 Security              8.0  /10  █████████░░░
 Freshness            10.0  /10  ████████████
```

## 为什么需要 agentscore？

Claude Code 环境已变得像 Kubernetes 集群一样复杂，但缺少类似 `kubectl describe` 的诊断工具。

| 问题 | 说明 |
|------|------|
| 缺乏可见性 | 无法判断当前配置是否正确 |
| 不知道差距 | 意识不到重要工具的缺失 |
| 不知道冲突 | 20 个插件中有 3 个冲突却无从得知 |
| 浪费上下文 | 不清楚哪些工具在无谓消耗上下文 |

## 安装

```bash
pip install agentscore-cli
```

**要求：** Python 3.11+，已安装 Claude Code

从源码安装：

```bash
git clone https://github.com/calintzy/agentscore
cd agentscore
pip install -e .
```

## 使用方法

```bash
# 立即扫描（自动检测配置文件）
agentscore

# 直接指定角色
agentscore --profile backend

# JSON 输出
agentscore --json

# 无颜色输出（适用于 CI 环境）
agentscore --no-color

# 安装新工具前模拟影响
agentscore check https://github.com/upstash/context7

# 查看历史评分
agentscore history

# 与特定时间点对比
agentscore diff
agentscore diff 2026-05-01

# 保存配置文件设置
agentscore setup

# 查看版本
agentscore --version
```

## 评分标准（满分 100 分）

| 维度 | 分值 | 说明 |
|------|------|------|
| Context Efficiency | 25 | CLAUDE.md 大小、无用工具、重复指令 |
| Coverage | 20 | 配置文件所需功能类别的覆盖率 |
| Conflict Detection | 20 | 提供相同功能的工具重复情况 |
| Config Quality | 15 | 模型设置、未激活插件、CLAUDE.md 存在与否 |
| Security | 10 | 危险权限模式（`Bash(*)`、`Bash(sudo:*)` 等） |
| Freshness | 10 | 插件最后更新时间 |

### 评分等级

| 等级 | 分数 | 含义 |
|------|------|------|
| S | 90-100 | 优化环境 |
| A | 75-89 | 配置良好，需少量改进 |
| B | 55-74 | 基础完善，需重要改进 |
| C | 35-54 | 存在较大差距 |
| D | 0-34 | 建议重新配置 |

## Context ROI 概念

将上下文成本衡量为**价值对比率**，而非绝对值。

```
Context ROI = (配置文件适配性 × 0.6 + 配置优先级 × 0.4) / 上下文成本
```

- ROI < 0.3：**无用负担（Dead Weight）** — 高成本且未使用的工具（扣分）
- ROI > 2.0 + 低成本：**理想工具（Ideal）** — 低成本高价值（加分）

### 配置优先级信号

仅通过配置文件衡量"使用意图"，无需日志解析。

| 信号 | 优先级 |
|------|--------|
| 在 CLAUDE.md 中直接提及 | 高 |
| 在 `enabledPlugins` 中已激活 | 中 |
| 在 `enabledMcpjsonServers` 中已注册 | 中 |
| 在 `mcp.json` 中已配置 | 中 |
| 仅安装，未出现在任何地方 | 低 |

## 配置文件系统

```bash
agentscore                    # Tier 0: 通用（即时运行，无配置文件）
agentscore --profile backend  # Tier 1: 基于角色评估
agentscore setup              # 保存角色 → 之后自动应用
```

支持的角色：`backend`、`frontend`、`fullstack`、`ml`、`devops`

无配置文件时，agentscore 通过当前目录的文件模式自动检测（大量 `.py` 文件 → backend/ml，`package.json` → frontend，`Dockerfile` + k8s → devops）。

## agentscore check

在安装新 GitHub 项目之前分析其影响。

```bash
$ agentscore check https://github.com/some-org/some-tool

agentscore check — some-org/some-tool
⭐ 1,234 stars  📄 MIT  🟢 最近更新

✅ 推荐安装  预计评分提升 +3.0 分

评分预测:  82.0 → 85.0 (+3.0)

 维度                   当前     安装后   变化
 Context Efficiency     17.0     17.0      —
 Coverage               20.0     20.0      —
 Conflict Detection     12.0     14.0   +2.0
 ...
```

## 历史记录

```bash
agentscore history        # 最近 10 次评分趋势
agentscore history --limit 30

agentscore diff           # 与上次扫描对比
agentscore diff 2026-05-01  # 与特定日期对比
```

历史记录保存在 `~/.agentscore/history/`，自动保留 30 天。

## 设计原则

1. **零上下文开销** — agentscore 本身不向 Claude Code 会话添加上下文
2. **按需运行** — 平时完全静默，仅在需要时执行
3. **纯本地** — 所有数据存储在 `~/.agentscore/`，无外部服务器
4. **可信估算** — 不确定的值标注为"(estimated)"

## 扫描目标文件

```
~/.claude/settings.json              enabledPlugins、模型设置
~/.claude/settings.local.json        permissions.allow、enabledMcpjsonServers
~/.claude/mcp.json                   MCP 服务器列表
~/.claude/CLAUDE.md                  全局指令
~/.claude/plugins/installed_plugins.json  已安装插件 + 更新时间
.claude/CLAUDE.md                    项目级指令
CLAUDE.md                            项目根目录指令
```

## 技术栈

- **Python 3.11+**
- `click` — CLI 框架
- `rich` — 终端输出
- `httpx` — GitHub API（用于 `agentscore check`）
- 仅使用标准库：`json`、`pathlib`、`re`、`datetime`

## 环境变量

| 变量 | 说明 |
|------|------|
| `GITHUB_TOKEN` | GitHub 个人访问令牌（将 `agentscore check` 的请求限制从 60 次/小时提升至 5,000 次/小时） |

## 许可证

MIT
