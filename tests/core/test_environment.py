from pathlib import Path

from litagent.core.environment import check_configs, check_papers


def test_project_configs_are_valid_yaml() -> None:
    root = Path(__file__).resolve().parents[2]
    results = check_configs(root)

    assert results
    assert all(result.status == "PASS" for result in results)


def test_papers_directory_is_resolved_from_config() -> None:
    root = Path(__file__).resolve().parents[2]
    result = check_papers(root)

    assert result.status == "PASS"
    assert "pdf_count=10" in result.detail
