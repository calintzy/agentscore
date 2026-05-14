from __future__ import annotations

from pathlib import Path

from agentscore.models import Profile
from agentscore.profile.profiles import make_profile


def detect_profile(directory: Path | None = None) -> Profile:
    cwd = directory or Path.cwd()

    py_files = list(cwd.glob("*.py")) + list(cwd.glob("**/*.py"))
    has_package_json = (cwd / "package.json").exists()
    has_dockerfile = (cwd / "Dockerfile").exists() or (cwd / "dockerfile").exists()
    has_k8s = any(cwd.glob("**/*.yaml")) and has_dockerfile
    has_tailwind = _has_tailwind(cwd)
    has_requirements = (cwd / "requirements.txt").exists() or (cwd / "pyproject.toml").exists()
    has_notebooks = any(cwd.glob("**/*.ipynb"))

    if has_k8s:
        return make_profile("devops", tier=1)

    if has_package_json and has_requirements:
        return make_profile("fullstack", tier=1)

    if has_notebooks or (has_requirements and not has_package_json):
        if has_notebooks:
            return make_profile("ml", tier=1)
        if len(py_files) > 3:
            return make_profile("backend", tier=1)

    if has_package_json:
        if has_tailwind:
            return make_profile("frontend", tier=1)
        return make_profile("frontend", tier=1)

    if has_dockerfile:
        return make_profile("devops", tier=1)

    return make_profile("generic", tier=0)


def _has_tailwind(cwd: Path) -> bool:
    return (cwd / "tailwind.config.js").exists() or (cwd / "tailwind.config.ts").exists()
