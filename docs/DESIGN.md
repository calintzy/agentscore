# agentscore — Architecture Design v0.3

## 변경 이력
- v0.3: 실제 Claude Code 파일 구조 반영 (settings.json 키 교정), 누락 데이터모델 추가, 전체 evaluator 공식 완성, provides 기반 충돌 감지로 전환
- v0.2: 동적 분석 → 설정 우선순위 신호로 대체, tiktoken 제거, 점수 공식 완성, tool_registry 구조 단순화

---

## 1. 기술 스택

### 언어: Python 3.11+

### 핵심 의존성 (최소화)

```
필수:
- click          # CLI 인터페이스
- rich           # 터미널 출력 (색상, 표)
- httpx          # GitHub API 호출 (agentscore check용)

stdlib로 처리:
- json, pathlib, re, datetime, hashlib
```

**제거된 의존성:**
- `tiktoken` (제거) → `len(text) // 4` 근사치로 대체. 5MB 목표 달성 가능
- `watchdog` (v2로 미룸) → watch 모드는 v2
- `tomllib` (불필요) → 설정 파일이 모두 JSON

---

## 2. 디렉토리 구조

```
agentscore/
├── agentscore/
│   ├── __init__.py
│   ├── cli.py                   # CLI 진입점
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── config_reader.py     # 설정 파일 파싱
│   │   └── plugin_scanner.py    # 플러그인/MCP 목록 + config priority 분류
│   ├── evaluator/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── context_efficiency.py
│   │   ├── coverage.py
│   │   ├── conflict.py
│   │   ├── config_quality.py
│   │   ├── security.py
│   │   └── freshness.py
│   ├── profile/
│   │   ├── __init__.py
│   │   ├── detector.py          # 파일 패턴 기반 자동 감지
│   │   └── profiles.py          # 역할별 required_categories 정의
│   ├── checker/
│   │   ├── __init__.py
│   │   ├── github_fetcher.py
│   │   ├── tool_classifier.py   # 구조 기반 자동 분류
│   │   └── impact_simulator.py
│   ├── history/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   └── diff.py
│   ├── reporter/
│   │   ├── __init__.py
│   │   ├── terminal.py
│   │   └── json_reporter.py
│   └── data/
│       └── tool_registry.json
├── docs/
├── tests/
│   ├── fixtures/
│   └── test_evaluators.py
├── pyproject.toml
├── CLAUDE.md
└── README.md
```

---

## 3. 핵심 설계 원칙: 신뢰할 수 있는 추정

**기존 접근:** 정확한 측정 목표 → 구현 불가 지점 다수 발생  
**변경된 접근:** 신뢰할 수 있는 신호만 사용 + 불확실성 명시

```
"Context cost: ~800 tokens (estimated)"   ← 구조 기반 추정
"Context cost: 812 tokens (measured)"     ← --measure 플래그 실행 시
```

---

## 4. 실제 Claude Code 파일 구조

스캔 로직 작성의 기반이 되는 실제 파일 구조.

### `~/.claude/settings.json`
```json
{
  "model": "sonnet",
  "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"},
  "enabledPlugins": {
    "oh-my-claudecode@omc": true,
    "bkit@bkit-marketplace": true,
    "ouroboros@ouroboros": true
  },
  "extraKnownMarketplaces": {...}
}
```

### `~/.claude/settings.local.json`
```json
{
  "permissions": {
    "allow": ["Bash(curl:*)", "Bash(npm install)", "Bash(claude:*)"]
  },
  "enableAllProjectMcpServers": true,
  "enabledMcpjsonServers": ["context7", "filesystem"]
}
```

### `~/.claude/mcp.json`
```json
{
  "mcpServers": {
    "ouroboros": {"command": "uvx", "args": ["..."]}
  }
}
```

### `~/.claude/plugins/installed_plugins.json`
```json
{
  "version": 2,
  "plugins": {
    "oh-my-claudecode@omc": [
      {
        "scope": "user",
        "installPath": "...",
        "version": "4.13.5",
        "installedAt": "2026-03-31T12:28:12.407Z",
        "lastUpdated": "2026-05-03T04:51:40.000Z"
      }
    ]
  }
}
```

---

## 5. 설정 우선순위 신호

로그 파싱 대신 설정 파일에서 신호를 추출한다.

```python
def get_config_priority(tool_id: str, env: EnvSnapshot) -> str:
    # CLAUDE.md에 직접 언급 → 가장 강한 의도적 사용 신호
    if tool_mentioned_in_claude_md(tool_id, env.all_claude_md_content):
        return "high"

    # settings.json → enabledPlugins에 활성화됨
    # 형식: "pluginId@marketplace": true/false
    enabled_plugins = env.settings.get("enabledPlugins", {})
    plugin_key = _find_plugin_key(tool_id, enabled_plugins)
    if plugin_key and enabled_plugins[plugin_key] is True:
        return "medium"

    # settings.local.json → enabledMcpjsonServers에 등록된 MCP
    if tool_id in env.local_settings.get("enabledMcpjsonServers", []):
        return "medium"

    # mcp.json → mcpServers에 설정된 MCP
    if tool_id in env.mcp_settings.get("mcpServers", {}):
        return "medium"

    # 설치됐지만 활성화 안 됨
    return "low"


def _find_plugin_key(tool_id: str, enabled_plugins: dict) -> str | None:
    # "bkit" → "bkit@bkit-marketplace" 매칭
    # tool_id가 전체 키("bkit@bkit-marketplace")이면 직접 매칭
    if tool_id in enabled_plugins:
        return tool_id
    # tool_id가 플러그인명만일 때 "@" 앞부분으로 매칭
    for key in enabled_plugins:
        if key.split("@")[0] == tool_id:
            return key
    return None


CONFIG_PRIORITY_TO_SCORE = {
    "high": 1.0,
    "medium": 0.6,
    "low": 0.2,
}
```

**근거:** 실제 호출 횟수보다 "사용자가 이 도구를 얼마나 의도적으로 설정했는가"가 ROI 판단에 더 의미 있다.

---

## 6. 컨텍스트 비용 추정 (2단계)

### 1단계: tool_registry에 등록된 도구

registry에서 hardcoded 값 사용.

### 2단계: 미등록 도구 — 구조 기반 추정

```python
def estimate_context_cost(tool_path: Path | None) -> str:
    if tool_path is None:
        return "low"  # MCP 등 로컬 경로 없는 도구: 최소 가정
    has_always_on_hook = check_user_prompt_submit_hook(tool_path)
    skill_file_count = count_skill_files(tool_path)
    claude_md_tokens = estimate_tokens(read_claude_md(tool_path))

    if has_always_on_hook and (skill_file_count > 10 or claude_md_tokens > 5000):
        return "high"
    elif has_always_on_hook or skill_file_count > 5 or claude_md_tokens > 2000:
        return "medium"
    else:
        return "low"

def estimate_tokens(text: str) -> int:
    return len(text) // 4   # GPT-계열 근사치, tiktoken 불필요
```

### 정밀 모드 (선택적)

```bash
agentscore --measure
```

실제 `claude -p "hello"` 를 plugins 있음/없음으로 실행해서 토큰 차이를 측정. 출력에 "(measured)"로 표시.

---

## 7. Context ROI 공식

```python
COST_MAP = {"low": 0.2, "medium": 0.5, "high": 1.0}

def calculate_roi(tool: Tool, profile: Profile) -> float:
    # generic 프로필(Tier 0)은 중립값 사용 — 프로필 미선택 패널티 없음
    if profile.role == "generic":
        fit_score = 0.7
    else:
        fit_score = 1.0 if profile.role in tool.profile_fit else 0.3
    freq_score = CONFIG_PRIORITY_TO_SCORE[tool.config_priority]
    cost = COST_MAP[tool.context_cost]

    # 프로필 적합성(60%) + 설정 우선순위(40%) / 컨텍스트 비용
    return (fit_score * 0.6 + freq_score * 0.4) / cost

DEAD_WEIGHT_THRESHOLD = 0.3   # ROI가 이 이하면 Dead Weight
IDEAL_THRESHOLD = 2.0         # ROI가 이 이상이면 이상적 도구 (저비용 + 고적합)

def context_cost_to_penalty(cost: str) -> float:
    return {"low": 0.5, "medium": 2.0, "high": 4.0}[cost]
```

---

## 8. 전체 Evaluator 공식

### 8-1. Context Efficiency (25점)

```python
def evaluate_context_efficiency(env: EnvSnapshot, profile: Profile) -> float:
    score = 25.0

    # 1. CLAUDE.md 크기 감점
    total_tokens = estimate_tokens(env.all_claude_md_content)
    if total_tokens > 10000:
        score -= min(8.0, (total_tokens - 10000) / 1000)

    # 2. Dead Weight 감점 / Ideal 보너스
    # config_priority는 plugin_scanner.py에서 Tool 생성 시 이미 설정됨
    for tool in env.installed_tools:
        roi = calculate_roi(tool, profile)
        if roi < DEAD_WEIGHT_THRESHOLD:
            score -= context_cost_to_penalty(tool.context_cost)
        elif roi > IDEAL_THRESHOLD and tool.context_cost == "low":
            score = min(25.0, score + 0.5)  # 저비용 고적합 도구: 최대 25점 한도 내 가산

    # 3. 중복 지시사항 감점
    duplicates = detect_duplicate_instructions(env)
    score -= len(duplicates) * 2.0

    return max(0.0, score)

def detect_duplicate_instructions(env: EnvSnapshot) -> list[str]:
    seen = set()
    duplicates = []
    for clause in extract_key_clauses(env.all_claude_md_content):
        normalized = clause.lower().strip()
        if normalized in seen:
            duplicates.append(clause)
        seen.add(normalized)
    return duplicates

def extract_key_clauses(content: str) -> list[str]:
    # 의미 있는 지시문 추출: 50자 이상, 헤더/빈줄/코드블록 제외
    in_code_block = False
    clauses = []
    for line in content.splitlines():
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # bullet point("-")는 제외하지 않음 — CLAUDE.md 지시사항 대부분이 bullet 형식
        if len(stripped) >= 30:  # bullet 포함시 임계 낮춤
            clauses.append(stripped)
    return clauses
```

### 8-2. Coverage (20점)

```python
# profiles.py에서 정의
# ⚠️ tool_registry의 provides 어휘와 반드시 동일해야 함
# 허용 어휘: planning, git, qa, frontend, backend, database, documentation,
#            architecture, debugging, infra, data, memory
PROFILE_REQUIRED: dict[str, set[str]] = {
    "backend":   {"database", "qa", "git"},
    "frontend":  {"frontend", "qa", "git"},
    "fullstack": {"database", "frontend", "qa", "git"},
    "ml":        {"data", "qa", "git"},
    "devops":    {"infra", "qa", "git"},
    "generic":   set(),
}

def evaluate_coverage(env: EnvSnapshot, profile: Profile) -> float:
    required = PROFILE_REQUIRED.get(profile.role, set())
    if not required:
        return 15.0  # 범용 프로필: 기본 점수

    # category가 아닌 provides로 비교 (category는 "multi-tool" 같은 상위 분류라 vocab 불일치)
    installed_provides: set[str] = set()
    for t in env.installed_tools:
        installed_provides.update(t.provides)
    covered = installed_provides & required
    return round((len(covered) / len(required)) * 20.0, 1)
```

### 8-3. Conflict Detection (20점)

충돌 = **같은 기능 카테고리(`provides`)를 2개 이상 설치**

```python
def evaluate_conflict(env: EnvSnapshot, profile: Profile) -> float:
    score = 20.0
    conflicts = detect_conflicts(env.installed_tools)
    for conflict in conflicts:
        score -= 2.0  # 충돌 1건당 2점 감점 (경고 수준, omc+bkit 공존 허용)
    return max(0.0, score)

def detect_conflicts(installed_tools: list[Tool]) -> list[Conflict]:
    capability_map: dict[str, list[Tool]] = {}
    for tool in installed_tools:
        for cap in tool.provides:
            capability_map.setdefault(cap, []).append(tool)

    conflicts = []
    for cap, tools in capability_map.items():
        if len(tools) >= 2:
            conflicts.append(Conflict(
                category=cap,
                tools=tools,
                message=f"{cap} 기능을 제공하는 도구가 {len(tools)}개 설치됨",
            ))
    return conflicts
```

**`provides` 예시 (tool_registry.json):**
```
"oh-my-claudecode@omc" → provides: ["planning", "git", "qa", "frontend"]
"bkit@bkit-marketplace" → provides: ["planning", "qa", "git"]
→ planning, qa, git 충돌 감지
```

### 8-4. Config Quality (15점)

```python
def evaluate_config_quality(env: EnvSnapshot, profile: Profile) -> float:
    score = 15.0

    # model이 명시적으로 설정되지 않음
    if not env.settings.get("model"):
        score -= 3.0

    # enabledPlugins에 비활성화된 항목이 남아있음
    disabled = [
        k for k, v in env.settings.get("enabledPlugins", {}).items() if not v
    ]
    score -= min(5.0, len(disabled) * 1.5)

    # 전역 CLAUDE.md가 없거나 비어있음 (프로젝트 CLAUDE.md와 분리해서 체크)
    global_md = env.global_claude_md_content.strip()
    if not global_md:
        score -= 5.0
    elif estimate_tokens(global_md) < 50:
        score -= 2.0

    return max(0.0, score)
```

### 8-5. Security (10점)

```python
HIGH_RISK_PATTERNS = {"Bash(*)", "Bash(rm:*)", "Bash(sudo:*)"}
WARN_RISK_PATTERNS = {"Bash(curl:*)"}

def evaluate_security(env: EnvSnapshot, profile: Profile) -> float:
    score = 10.0
    allow_list = env.local_settings.get("permissions", {}).get("allow", [])

    for pattern in allow_list:
        if pattern in HIGH_RISK_PATTERNS:
            score -= 3.0
        elif pattern in WARN_RISK_PATTERNS:
            score -= 1.0

    # enableAllProjectMcpServers=true: 모든 프로젝트 MCP 자동 활성화
    if env.local_settings.get("enableAllProjectMcpServers", False):
        score -= 1.0

    return max(0.0, score)
```

### 8-6. Freshness (10점)

```python
def evaluate_freshness(env: EnvSnapshot, profile: Profile) -> float:
    score = 10.0
    now = datetime.now(tz=timezone.utc)

    for tool in env.installed_tools:
        if not tool.last_updated:
            continue
        days_old = (now - tool.last_updated).days
        if days_old > 180:
            score -= 1.5
        elif days_old > 90:
            score -= 0.5

    return max(0.0, score)
```

---

## 9. tool_registry.json 구조

```json
{
  "version": "1.0",
  "tools": {
    "oh-my-claudecode@omc": {
      "id": "oh-my-claudecode@omc",
      "display_name": "oh-my-claudecode",
      "category": "multi-tool",
      "context_cost": "high",
      "profile_fit": ["backend", "frontend", "fullstack", "ml", "devops"],
      "provides": ["planning", "git", "qa", "frontend", "debugging"],
      "github_url": "https://github.com/jasonsum/oh-my-claudecode"
    },
    "bkit@bkit-marketplace": {
      "id": "bkit@bkit-marketplace",
      "display_name": "bkit",
      "category": "multi-tool",
      "context_cost": "high",
      "profile_fit": ["backend", "frontend", "fullstack", "ml", "devops"],
      "provides": ["planning", "qa", "git", "frontend", "architecture"],
      "github_url": "https://github.com/team-bkit/bkit"
    },
    "ouroboros@ouroboros": {
      "id": "ouroboros@ouroboros",
      "display_name": "ouroboros",
      "category": "planning",
      "context_cost": "medium",
      "profile_fit": ["backend", "frontend", "fullstack", "ml", "devops"],
      "provides": ["planning"],
      "mcp_id": "ouroboros",
      "github_url": "https://github.com/ouro/ouroboros"
    },
    "context7": {
      "id": "context7",
      "display_name": "context7",
      "category": "documentation",
      "context_cost": "low",
      "profile_fit": ["backend", "frontend", "fullstack", "ml", "devops"],
      "provides": ["documentation"],
      "github_url": "https://github.com/upstash/context7"
    },
    "supabase@claude-plugins-official": {
      "id": "supabase@claude-plugins-official",
      "display_name": "Supabase MCP",
      "category": "database",
      "context_cost": "medium",
      "profile_fit": ["backend", "fullstack"],
      "provides": ["database"],
      "github_url": "https://github.com/supabase/mcp-server-supabase"
    }
  }
}
```

**`mcp_id` 필드:** 플러그인이면서 동시에 MCP 서버인 도구(예: ouroboros)는 `mcp_id`로 mcp.json 키를 명시. plugin_scanner가 두 소스에서 같은 도구를 발견하면 `mcp_id` 매칭으로 중복 제거하여 Tool 객체 1개만 생성.

**미등록 도구 처리:** 감점 없이 `"category": "unknown"`, `"provides": []` 로 표시.

---

## 10. 핵심 데이터 모델

```python
@dataclass
class Profile:
    role: str   # 'backend' | 'frontend' | 'fullstack' | 'ml' | 'devops' | 'generic'
    tier: int   # 0=범용, 1=역할선택, 2=상세설정


@dataclass
class Tool:
    id: str                        # "bkit@bkit-marketplace" 또는 "context7" 형식
    display_name: str
    path: Path | None              # 로컬 설치 경로 (MCP는 None일 수 있음)
    context_cost: str              # 'low' | 'medium' | 'high'
    config_priority: str           # 'high' | 'medium' | 'low'
    category: str
    profile_fit: list[str]
    provides: list[str]            # 기능 카테고리 (충돌 감지용)
    in_registry: bool
    last_updated: datetime | None  # installed_plugins.json의 lastUpdated


@dataclass
class Conflict:
    category: str       # 충돌하는 기능 카테고리 (예: "planning")
    tools: list[Tool]
    message: str


@dataclass
class Issue:
    severity: str       # 'error' | 'warning' | 'info'
    dimension: str      # 평가 차원 이름
    message: str
    recommendation: str


@dataclass
class ToolROI:
    tool_id: str
    config_priority: str
    context_cost: str
    roi_score: float
    verdict: str        # 'keep' | 'review' | 'remove'
    reason: str


@dataclass
class EnvSnapshot:
    claude_version: str
    global_claude_md_content: str      # ~/.claude/CLAUDE.md 단독
    all_claude_md_content: str         # 전역 + 프로젝트 CLAUDE.md 합산 (중복 감지용)
    installed_tools: list[Tool]
    settings: dict                     # ~/.claude/settings.json
    local_settings: dict               # ~/.claude/settings.local.json
    mcp_settings: dict                 # ~/.claude/mcp.json
    installed_plugins: dict            # ~/.claude/plugins/installed_plugins.json → plugins 키
    scan_timestamp: str


@dataclass
class ScanResult:
    timestamp: str
    profile: Profile
    scores: dict[str, float]           # dimension → score
    total_score: float
    grade: str                         # 'S' | 'A' | 'B' | 'C' | 'D'
    issues: list[Issue]
    recommendations: list[str]
    tool_rois: list[ToolROI]
    conflicts: list[Conflict]
```

---

## 11. 스캔 대상 파일

```
~/.claude/settings.json              # enabledPlugins (플러그인 활성화 여부), model, env
~/.claude/settings.local.json        # permissions.allow (허용 명령), enabledMcpjsonServers
~/.claude/mcp.json                   # mcpServers (MCP 서버 설정)
~/.claude/CLAUDE.md                  # 전역 지시사항
~/.claude/plugins/installed_plugins.json  # 설치된 플러그인 목록 (version, scope, lastUpdated)
~/.claude/keybindings.json           # (선택적)
.claude/settings.json                # 프로젝트별 설정
.claude/CLAUDE.md                    # 프로젝트별 지시사항
.mcp.json                            # 프로젝트별 MCP 설정

Claude Code 버전:
$ claude --version
```

---

## 12. CLI 인터페이스 (MVP 범위)

```bash
agentscore [OPTIONS] [COMMAND]

# MVP 명령어
agentscore                       # 즉시 범용 스캔
agentscore check <github-url>    # 설치 전 영향 분석
agentscore history               # 점수 추이 조회
agentscore diff [date]           # 특정 시점 대비 비교
agentscore setup                 # 프로필 설정

# MVP 옵션
--profile TEXT     역할 직접 지정
--measure          정밀 모드 (실제 Claude 실행해서 토큰 측정)
--json             JSON 출력
--no-color         색상 없이 출력
--version

# v2 예정
# agentscore watch
# agentscore compare <url...>
```

---

## 13. 히스토리 저장소

### 저장 경로

```
~/.agentscore/
├── config.json          # agentscore setup으로 저장한 프로필
└── history/
    ├── 20260514_143022.json
    ├── 20260513_091500.json
    └── ...              # 30일 초과분 자동 삭제
```

### 히스토리 파일 포맷

```json
{
  "timestamp": "2026-05-14T14:30:22Z",
  "profile": {"role": "fullstack", "tier": 1},
  "total_score": 72.5,
  "grade": "B",
  "scores": {
    "context_efficiency": 18.0,
    "coverage": 16.0,
    "conflict": 16.0,
    "config_quality": 12.5,
    "security": 7.0,
    "freshness": 3.0
  },
  "tool_count": 6,
  "issues_count": 3
}
```

### config.json 포맷

```json
{
  "profile": {"role": "fullstack", "tier": 1},
  "created_at": "2026-05-14T14:30:22Z"
}
```

### `agentscore diff` 동작

```python
# 가장 최근 히스토리와 현재 결과를 비교
# agentscore diff 2026-05-13 → 해당 날짜 파일과 비교
# 출력: 차원별 점수 변화 (+/-), 추가/삭제된 도구
```

---

## 14. MVP 구현 순서

```
Phase 1 — 스캔 + 기본 출력
├── config_reader.py: settings.json, settings.local.json, mcp.json, CLAUDE.md, installed_plugins.json 파싱
├── plugin_scanner.py: 도구 목록 + config_priority 분류
├── tool_registry.json: 초기 30개 도구 등록 (실제 Claude Code 생태계 기준)
└── terminal.py: rich 기반 기본 출력

Phase 2 — 평가 엔진
├── 6개 evaluator 구현 (완전 정의된 공식 사용)
├── Context ROI 계산
├── Tier 0 범용 + Tier 1 역할 5개 프로필
└── 자동 감지 (파일 패턴 기반)

Phase 3 — agentscore check
├── GitHub API 연동 (httpx)
├── 구조 기반 도구 분류
└── 점수 시뮬레이션

Phase 4 — 히스토리 + 완성도
├── 히스토리 저장/조회/diff
├── --measure 정밀 모드
├── self-check 기능
└── README + 데모 준비
```
