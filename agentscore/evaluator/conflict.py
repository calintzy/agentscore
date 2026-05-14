from __future__ import annotations

from agentscore.models import Conflict, EnvSnapshot, Profile, Tool


def evaluate_conflict(env: EnvSnapshot, profile: Profile) -> float:
    score = 20.0
    conflicts = detect_conflicts(env.installed_tools)
    score -= len(conflicts) * 2.0
    return max(0.0, score)


def detect_conflicts(installed_tools: list[Tool]) -> list[Conflict]:
    # multi-tool은 넓은 기능을 포괄하는 게 설계 의도 — 전문 도구 간 충돌만 체크
    specialized = [t for t in installed_tools if t.category != "multi-tool"]

    capability_map: dict[str, list[Tool]] = {}
    for tool in specialized:
        for cap in tool.provides:
            capability_map.setdefault(cap, []).append(tool)

    conflicts: list[Conflict] = []
    for cap, tools in capability_map.items():
        if len(tools) >= 2:
            conflicts.append(Conflict(
                category=cap,
                tools=tools,
                message=f"{cap} 기능을 제공하는 도구가 {len(tools)}개 설치됨",
            ))
    return conflicts
