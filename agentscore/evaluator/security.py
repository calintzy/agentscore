from __future__ import annotations

from agentscore.models import EnvSnapshot, Profile

# 위협 카테고리: (패턴 집합, 감점)
# CRITICAL — 임의 명령 실행
CRITICAL_PATTERNS: set[str] = {
    "Bash(*)",
    "Bash(sudo:*)",
}
# HIGH — 파괴적 명령 / 민감 자격증명 경로 접근
HIGH_PATTERNS: set[str] = {
    "Bash(rm:*)",
    "Write(*)",
    "Read(~/.ssh:*)",
    "Bash(~/.ssh:*)",
    "Read(~/.aws:*)",
    "Bash(~/.aws:*)",
    "Read(~/.gnupg:*)",
}
# MEDIUM — 외부 네트워크 접근
MEDIUM_PATTERNS: set[str] = {
    "Bash(curl:*)",
    "Bash(wget:*)",
    "Bash(ssh:*)",
    "WebFetch(*)",
}

THREAT_TABLE: list[tuple[set[str], float]] = [
    (CRITICAL_PATTERNS, 3.0),
    (HIGH_PATTERNS,     2.0),
    (MEDIUM_PATTERNS,   1.0),
]


def evaluate_security(env: EnvSnapshot, profile: Profile) -> float:
    score = 10.0
    allow_list = env.local_settings.get("permissions", {}).get("allow", [])

    for pattern in allow_list:
        for threat_set, penalty in THREAT_TABLE:
            if pattern in threat_set:
                score -= penalty
                break  # 패턴당 최고 위협 카테고리 하나만 적용

    if env.local_settings.get("enableAllProjectMcpServers", False):
        score -= 1.0

    return max(0.0, score)
