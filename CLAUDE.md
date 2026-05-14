# agentscore

Claude Code AI 개발 환경 품질 평가 CLI 도구.

## 프로젝트 개요

- **목적**: Claude Code 사용자의 MCP/플러그인/스킬 환경을 분석해 점수와 개선 방향 제시
- **문서**: docs/PRD.md (요구사항), docs/DESIGN.md (아키텍처)
- **언어**: Python 3.11+
- **배포 형태**: CLI 독립 도구 (Claude Code 플러그인 아님)

## 핵심 설계 원칙

1. agentscore 자체는 Claude Code 세션에 컨텍스트를 추가하지 않는다
2. 실행할 때만 작동한다. 평소엔 완전 침묵
3. 외부 서버 없음. 모든 데이터는 로컬 저장

## 디렉토리 구조

```
agentscore/   # 메인 패키지
  scanner/    # 환경 스캔 (설정 파일 파싱)
  evaluator/  # 6개 평가 차원 엔진
  profile/    # 프로필 감지 및 가중치
  checker/    # agentscore check (GitHub 분석)
  history/    # 히스토리 저장/조회
  reporter/   # 터미널/JSON 출력
  data/       # tool_registry.json, profile_weights.json
docs/         # PRD.md, DESIGN.md
tests/
```

## 평가 차원 (6개)

| 차원 | 배점 | 파일 |
|------|------|------|
| Context Efficiency | 25 | evaluator/context_efficiency.py |
| Coverage | 20 | evaluator/coverage.py |
| Conflict Detection | 20 | evaluator/conflict.py |
| Configuration Quality | 15 | evaluator/config_quality.py |
| Security | 10 | evaluator/security.py |
| Freshness | 10 | evaluator/freshness.py |

## 코딩 규칙

- 함수당 단일 책임. 하나의 evaluator가 다른 evaluator를 직접 호출하지 않는다
- 모든 평가는 `EnvSnapshot`과 `Profile` 두 인자만 받는다
- 외부 API 호출은 `checker/github_fetcher.py`에만 존재한다
- 새 도구 추가는 코드가 아닌 `data/tool_registry.json`에 한다

## 스캔 대상 경로

```
~/.claude/settings.json
~/.claude/CLAUDE.md
~/.claude/plugins/
.claude/settings.json
.claude/CLAUDE.md
.mcp.json
```

## 실행 방법 (개발 중)

```bash
pip install -e .
agentscore               # 즉시 스캔
agentscore check <url>   # 도구 사전 평가
agentscore history       # 점수 추이
```
