from __future__ import annotations

import locale
import os

_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # CLI descriptions
        "cli_help": "AI development environment quality analyzer.",
        "history_help": "Show score history.",
        "diff_help": "Compare current score against a previous snapshot.",
        "setup_help": "Configure and save your profile.",
        "check_help": "Simulate the impact of installing a new tool.",
        # Options
        "opt_profile": "Role (backend/frontend/fullstack/ml/devops)",
        "opt_json": "Output as JSON",
        "opt_no_color": "Disable color output",
        "opt_limit": "Number of records to show",
        # Setup prompts
        "setup_select_role": "Select your role:",
        "setup_prompt": "Enter number",
        "setup_saved": "Profile saved: {role} (~/.agentscore/config.json)",
        # Diff messages
        "diff_not_enough": "Not enough history to compare. Run agentscore once more and try again.",
        "diff_not_found": "No history found for date {date}.",
        # Check messages
        "check_analyzing": "  Analyzing {url}...",
        "check_error": "Error: Could not fetch GitHub data — {err}",
        # Terminal output
        "terminal_header": "agentscore  AI Environment Analysis",
        "terminal_scan": "Claude {version}   Scanned {ts} UTC",
        "terminal_no_tools": "No installed tools found.",
        "terminal_tool_count": "  {n} tools detected",
        "terminal_improvements": "Improvements",
        # Tools table headers
        "col_tool": "Tool",
        "col_category": "Category",
        "col_cost": "Cost",
        "col_priority": "Priority",
        # Issues
        "issue_security": "Dangerous permissions allowed",
        "issue_security_rec": "Review permissions.allow in settings.local.json",
        "issue_coverage": "Missing required tools for {role} profile",
        "issue_coverage_rec": "Add tools for required categories (git, qa, etc.)",
        "issue_conflict": "Duplicate tools with overlapping capabilities detected",
        "issue_conflict_rec": "Remove one tool from each conflicting pair",
        "issue_config": "Config quality improvement needed",
        "issue_config_rec": "Create ~/.claude/CLAUDE.md and set model explicitly",
        "issue_freshness": "Some tools have outdated updates",
        "issue_freshness_rec": "Update plugins to the latest version",
        # Tips
        "terminal_tips": "Quick Wins",
        "tip_context_efficiency": "High-cost tools with low ROI drag your score. Disable or remove tools you rarely use.",
        "tip_coverage": "Your profile is missing tools for key categories. Add a git, QA, or planning tool.",
        "tip_conflict": "Overlapping tools waste context. Keep one tool per capability and remove duplicates.",
        "tip_config_quality": "Create ~/.claude/CLAUDE.md to describe your project, and set \"model\" explicitly in settings.json.",
        "tip_security": "Review permissions.allow in settings.local.json — restrict to only what you actually need.",
        "tip_freshness": "Update your plugins to the latest versions for better compatibility and features.",
    },
    "ko": {
        "cli_help": "AI 개발 환경 품질 분석 도구.",
        "history_help": "점수 추이를 조회합니다.",
        "diff_help": "특정 시점 대비 현재 점수를 비교합니다.",
        "setup_help": "프로필을 설정하고 저장합니다.",
        "check_help": "새 도구를 설치하기 전 영향을 시뮬레이션합니다.",
        "opt_profile": "역할 지정 (backend/frontend/fullstack/ml/devops)",
        "opt_json": "JSON으로 출력",
        "opt_no_color": "색상 없이 출력",
        "opt_limit": "표시할 항목 수",
        "setup_select_role": "역할을 선택하세요:",
        "setup_prompt": "번호 입력",
        "setup_saved": "프로필 저장 완료: {role} (~/.agentscore/config.json)",
        "diff_not_enough": "비교할 히스토리가 부족합니다. agentscore를 한 번 더 실행한 뒤 시도하세요.",
        "diff_not_found": "날짜 {date}에 해당하는 히스토리를 찾을 수 없습니다.",
        "check_analyzing": "  {url} 분석 중...",
        "check_error": "오류: GitHub 데이터를 가져올 수 없습니다 — {err}",
        "terminal_header": "agentscore  AI 개발 환경 분석",
        "terminal_scan": "Claude {version}   스캔 {ts} UTC",
        "terminal_no_tools": "설치된 도구를 찾을 수 없습니다.",
        "terminal_tool_count": "  총 {n}개 도구 감지됨",
        "terminal_improvements": "개선 사항",
        "col_tool": "도구",
        "col_category": "카테고리",
        "col_cost": "비용",
        "col_priority": "우선순위",
        "issue_security": "위험한 권한이 허용됨",
        "issue_security_rec": "settings.local.json의 permissions.allow를 검토하세요",
        "issue_coverage": "{role} 프로필에 필수 도구가 부족함",
        "issue_coverage_rec": "필수 카테고리(git, qa 등) 도구를 추가하세요",
        "issue_conflict": "기능 중복 도구가 감지됨",
        "issue_conflict_rec": "동일 기능을 제공하는 도구 중 하나를 제거하세요",
        "issue_config": "설정 품질 개선 필요",
        "issue_config_rec": "~/.claude/CLAUDE.md를 작성하고 model을 명시적으로 설정하세요",
        "issue_freshness": "업데이트가 오래된 도구가 있음",
        "issue_freshness_rec": "플러그인을 최신 버전으로 업데이트하세요",
        "terminal_tips": "빠른 개선",
        "tip_context_efficiency": "ROI가 낮은 고비용 도구가 점수를 낮춥니다. 거의 사용하지 않는 도구를 비활성화하거나 제거하세요.",
        "tip_coverage": "필수 카테고리 도구가 부족합니다. git, QA, planning 도구를 추가하세요.",
        "tip_conflict": "기능이 겹치는 도구는 컨텍스트를 낭비합니다. 카테고리별로 하나씩만 유지하세요.",
        "tip_config_quality": "~/.claude/CLAUDE.md에 프로젝트 설명을 작성하고 settings.json에 \"model\"을 명시하세요.",
        "tip_security": "settings.local.json의 permissions.allow를 검토해 꼭 필요한 권한만 허용하세요.",
        "tip_freshness": "플러그인을 최신 버전으로 업데이트하면 호환성과 기능이 향상됩니다.",
    },
    "zh": {
        "cli_help": "AI 开发环境质量分析工具。",
        "history_help": "查看历史评分趋势。",
        "diff_help": "与特定时间点的评分进行对比。",
        "setup_help": "配置并保存配置文件。",
        "check_help": "在安装新工具前模拟影响。",
        "opt_profile": "指定角色 (backend/frontend/fullstack/ml/devops)",
        "opt_json": "以 JSON 格式输出",
        "opt_no_color": "禁用颜色输出",
        "opt_limit": "显示的记录数",
        "setup_select_role": "请选择您的角色：",
        "setup_prompt": "输入编号",
        "setup_saved": "配置文件已保存：{role} (~/.agentscore/config.json)",
        "diff_not_enough": "历史记录不足，无法对比。请再次运行 agentscore 后重试。",
        "diff_not_found": "未找到日期 {date} 的历史记录。",
        "check_analyzing": "  正在分析 {url}...",
        "check_error": "错误：无法获取 GitHub 数据 — {err}",
        "terminal_header": "agentscore  AI 环境分析",
        "terminal_scan": "Claude {version}   扫描时间 {ts} UTC",
        "terminal_no_tools": "未找到已安装的工具。",
        "terminal_tool_count": "  共检测到 {n} 个工具",
        "terminal_improvements": "改进建议",
        "col_tool": "工具",
        "col_category": "类别",
        "col_cost": "成本",
        "col_priority": "优先级",
        "issue_security": "存在危险权限",
        "issue_security_rec": "请检查 settings.local.json 中的 permissions.allow",
        "issue_coverage": "{role} 配置文件缺少必要工具",
        "issue_coverage_rec": "请添加必要类别的工具（git、qa 等）",
        "issue_conflict": "检测到功能重复的工具",
        "issue_conflict_rec": "请移除提供相同功能的其中一个工具",
        "issue_config": "需要提升配置质量",
        "issue_config_rec": "请创建 ~/.claude/CLAUDE.md 并明确设置 model",
        "issue_freshness": "存在长时间未更新的工具",
        "issue_freshness_rec": "请将插件更新至最新版本",
        "terminal_tips": "快速优化",
        "tip_context_efficiency": "ROI 低的高成本工具会拉低评分。请禁用或移除很少使用的工具。",
        "tip_coverage": "配置文件缺少关键类别工具。请添加 git、QA 或规划类工具。",
        "tip_conflict": "功能重叠的工具会浪费上下文。每个类别只保留一个工具。",
        "tip_config_quality": "请创建 ~/.claude/CLAUDE.md 描述项目，并在 settings.json 中明确设置 \"model\"。",
        "tip_security": "请检查 settings.local.json 中的 permissions.allow，仅保留必要权限。",
        "tip_freshness": "将插件更新至最新版本可提升兼容性和功能。",
    },
}


def detect_lang() -> str:
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val and val != "C":
            code = val.split("_")[0].split(".")[0].lower()
            if code in _MESSAGES:
                return code
    try:
        loc, _ = locale.getlocale()
        if loc:
            code = loc.split("_")[0].lower()
            if code in _MESSAGES:
                return code
    except Exception:
        pass
    return "en"


_lang: str = detect_lang()
_msgs: dict[str, str] = _MESSAGES[_lang]


def t(key: str, **kwargs: object) -> str:
    text = _msgs.get(key) or _MESSAGES["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
