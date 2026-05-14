# agentscore

> **Lighthouse for AI agent development environments**

[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/calintzy/agentscore?style=flat)](https://github.com/calintzy/agentscore/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/calintzy/agentscore)](https://github.com/calintzy/agentscore/issues)

**언어:** 한국어 | [English](README.md) | [中文](README.zh.md)

Claude Code 사용자의 MCP 서버, 플러그인, 스킬 환경을 분석해 점수와 개선 방향을 제시하는 CLI 도구.

```
$ agentscore

  A등급  82.0점  프로필: backend

 Context Efficiency   17.0  /25  ████████░░░░
 Coverage             20.0  /20  ████████████
 Conflict Detection   12.0  /20  ███████░░░░░
 Config Quality       15.0  /15  ████████████
 Security              8.0  /10  █████████░░░
 Freshness            10.0  /10  ████████████
```

## 왜 필요한가

Claude Code 환경이 복잡해지면서 Kubernetes 클러스터 수준의 설정이 됐지만, `kubectl describe`에 해당하는 진단 도구가 없다.

| 문제 | 설명 |
|------|------|
| 가시성 없음 | 내 설정이 잘 됐는지 알 방법이 없음 |
| 격차 모름 | 중요한 도구가 빠진 것을 인식하지 못함 |
| 충돌 모름 | 20개 플러그인 중 3개가 충돌하는지 알 수 없음 |
| 컨텍스트 낭비 | 어떤 도구가 불필요하게 컨텍스트를 소비하는지 모름 |

## 설치

```bash
git clone https://github.com/calintzy/agentscore
cd agentscore
pip install -e .
```

**요구사항:** Python 3.11+, Claude Code 설치됨

## 사용법

```bash
# 즉시 스캔 (프로필 자동 감지)
agentscore

# 역할 직접 지정
agentscore --profile backend

# JSON 출력
agentscore --json

# 색상 없이 출력 (CI 환경 등)
agentscore --no-color

# 새 도구 설치 전 영향 시뮬레이션
agentscore check https://github.com/upstash/context7

# 점수 추이 조회
agentscore history

# 특정 시점 대비 비교
agentscore diff
agentscore diff 2026-05-01

# 프로필 설정 저장
agentscore setup

# 버전 확인
agentscore --version
```

## 평가 기준 (100점 만점)

| 차원 | 배점 | 설명 |
|------|------|------|
| Context Efficiency | 25점 | CLAUDE.md 크기, Dead Weight 도구, 중복 지시사항 |
| Coverage | 20점 | 프로필에 필요한 기능 카테고리 커버리지 |
| Conflict Detection | 20점 | 동일 기능을 제공하는 도구 중복 여부 |
| Config Quality | 15점 | model 설정, 비활성 플러그인, CLAUDE.md 존재 |
| Security | 10점 | 위험한 권한 허용 패턴 (`Bash(*)`, `Bash(sudo:*)` 등) |
| Freshness | 10점 | 플러그인 최종 업데이트 시점 |

### 점수 등급

| 등급 | 점수 | 의미 |
|------|------|------|
| S | 90-100 | 최적화된 환경 |
| A | 75-89 | 잘 설정됨, 소규모 개선 필요 |
| B | 55-74 | 기본은 갖춰짐, 중요 개선 필요 |
| C | 35-54 | 상당한 격차 존재 |
| D | 0-34 | 재구성 권장 |

## Context ROI 개념

컨텍스트 비용을 절대값이 아닌 **가치 대비 비율**로 측정.

```
Context ROI = (프로필 적합성 × 0.6 + 설정 우선순위 × 0.4) / 컨텍스트 비용
```

- ROI < 0.3: **Dead Weight** — 사용하지 않는 고비용 도구 (감점)
- ROI > 2.0 + 저비용: **Ideal** — 적은 비용으로 높은 가치 (가산)

### 설정 우선순위 신호

로그 파싱 없이 설정 파일만으로 "얼마나 의도적으로 사용하는가"를 측정.

| 신호 | 우선순위 |
|------|---------|
| CLAUDE.md에 직접 언급됨 | 높음 |
| `enabledPlugins`에 활성화됨 | 중간 |
| `enabledMcpjsonServers`에 등록됨 | 중간 |
| `mcp.json`에 설정됨 | 중간 |
| 설치만 됐고 어디에도 없음 | 낮음 |

## 프로필 시스템

```bash
agentscore                    # Tier 0: 범용 (즉시 실행, 프로필 없음)
agentscore --profile backend  # Tier 1: 역할 기반 평가
agentscore setup              # 역할 저장 → 이후 자동 적용
```

지원 역할: `backend`, `frontend`, `fullstack`, `ml`, `devops`

프로필이 없으면 현재 디렉토리의 파일 패턴으로 자동 감지 (`.py` 파일 다수 → backend/ml, `package.json` → frontend, `Dockerfile` + k8s → devops).

## agentscore check

새 GitHub 프로젝트를 설치하기 전 영향을 분석.

```bash
$ agentscore check https://github.com/some-org/some-tool

agentscore check — some-org/some-tool
⭐ 1,234stars  📄 MIT  🟢 최근 업데이트

✅ 설치 권장  점수 +3.0점 향상 예상

점수 예측:  82.0 → 85.0 (+3.0)

 차원                      현재    설치 후   변화
 Context Efficiency        17.0     17.0       —
 Coverage                  20.0     20.0       —
 Conflict Detection        12.0     14.0    +2.0
 ...
```

## 히스토리

```bash
agentscore history        # 최근 10회 점수 추이
agentscore history --limit 30

agentscore diff           # 직전 스캔과 비교
agentscore diff 2026-05-01  # 특정 날짜와 비교
```

히스토리는 `~/.agentscore/history/`에 저장, 30일치 자동 유지.

## 설계 원칙

1. **컨텍스트 0 추가** — agentscore 자체는 Claude Code 세션에 컨텍스트를 추가하지 않음
2. **On-demand 실행** — 평소엔 완전 침묵, 필요할 때만 실행
3. **로컬 전용** — 모든 데이터는 `~/.agentscore/`에 로컬 저장, 외부 서버 없음
4. **신뢰할 수 있는 추정** — 불확실한 값은 "(estimated)"로 명시

## 스캔 대상 파일

```
~/.claude/settings.json              enabledPlugins, model 설정
~/.claude/settings.local.json        permissions.allow, enabledMcpjsonServers
~/.claude/mcp.json                   MCP 서버 목록
~/.claude/CLAUDE.md                  전역 지시사항
~/.claude/plugins/installed_plugins.json  설치된 플러그인 + 업데이트 시점
.claude/CLAUDE.md                    프로젝트별 지시사항
CLAUDE.md                            프로젝트 루트 지시사항
```

## 기술 스택

- **Python 3.11+**
- `click` — CLI
- `rich` — 터미널 출력
- `httpx` — GitHub API (`agentscore check`용)
- stdlib만 사용: `json`, `pathlib`, `re`, `datetime`

## 라이선스

MIT
