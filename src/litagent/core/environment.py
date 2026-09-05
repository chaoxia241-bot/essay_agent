"""Environment checks for the P1 development baseline."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import yaml

Status = Literal["PASS", "WARN", "FAIL"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: Status
    detail: str


REQUIRED_PACKAGES = {
    "pydantic": "pydantic",
    "pydantic-settings": "pydantic_settings",
    "PyYAML": "yaml",
    "loguru": "loguru",
    "typer": "typer",
    "SQLAlchemy": "sqlalchemy",
    "httpx": "httpx",
}

REQUIRED_CONFIGS = (
    "configs/app.yaml",
    "configs/models.yaml",
    "configs/ingestion.yaml",
    "configs/retrieval.yaml",
)


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def check_python() -> CheckResult:
    version = sys.version_info
    supported = (3, 11) <= version[:2] < (3, 13)
    detail = f"{sys.executable} ({version.major}.{version.minor}.{version.micro})"
    if supported:
        return CheckResult("python", "PASS", detail)
    return CheckResult(
        "python",
        "FAIL",
        f"{detail}; supported range is Python >=3.11,<3.13",
    )


def check_packages() -> list[CheckResult]:
    results: list[CheckResult] = []
    for package, module in REQUIRED_PACKAGES.items():
        installed = importlib.util.find_spec(module) is not None
        results.append(
            CheckResult(
                f"package:{package}",
                "PASS" if installed else "FAIL",
                "installed" if installed else "missing",
            )
        )
    return results


def check_configs(project_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for relative_path in REQUIRED_CONFIGS:
        path = project_root / relative_path
        if not path.is_file():
            results.append(CheckResult(f"config:{relative_path}", "FAIL", "missing"))
            continue
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            results.append(CheckResult(f"config:{relative_path}", "FAIL", str(exc)))
            continue
        if not isinstance(payload, dict):
            results.append(
                CheckResult(f"config:{relative_path}", "FAIL", "root must be a mapping")
            )
            continue
        results.append(CheckResult(f"config:{relative_path}", "PASS", "valid YAML"))
    return results


def check_papers(project_root: Path) -> CheckResult:
    app_config = project_root / "configs/app.yaml"
    try:
        payload = yaml.safe_load(app_config.read_text(encoding="utf-8"))
        raw_path = payload["paths"]["raw_pdfs"]
        papers_dir = (project_root / raw_path).resolve()
    except (OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        return CheckResult("papers", "FAIL", f"cannot resolve raw_pdfs: {exc}")

    if not papers_dir.is_dir():
        return CheckResult("papers", "FAIL", f"missing directory: {papers_dir}")
    pdf_count = sum(
        1
        for path in papers_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if pdf_count == 0:
        return CheckResult("papers", "WARN", f"{papers_dir}; no PDFs found")
    return CheckResult("papers", "PASS", f"{papers_dir}; pdf_count={pdf_count}")


def check_tool(name: str, required: bool) -> CheckResult:
    executable = shutil.which(name)
    if executable:
        return CheckResult(f"tool:{name}", "PASS", executable)
    status: Status = "FAIL" if required else "WARN"
    return CheckResult(f"tool:{name}", status, "not found on PATH")


def run_checks(project_root: Path | None = None) -> list[CheckResult]:
    root = (project_root or default_project_root()).resolve()
    return [
        check_python(),
        *check_packages(),
        *check_configs(root),
        check_papers(root),
        check_tool("git", required=True),
        check_tool("docker", required=False),
        check_tool("nvidia-smi", required=False),
    ]


def render_text(results: list[CheckResult]) -> str:
    width = max(len(result.name) for result in results)
    return "\n".join(
        f"{result.status:4}  {result.name:<{width}}  {result.detail}" for result in results
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the LitAgent P1 environment.")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    results = run_checks(args.project_root)
    if args.as_json:
        print(json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2))
    else:
        print(render_text(results))
    raise SystemExit(1 if any(result.status == "FAIL" for result in results) else 0)


if __name__ == "__main__":
    main()
