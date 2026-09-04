from pathlib import Path


def test_project_repository_url():
    pyproject = Path(__file__).parents[1] / "pyproject.toml"
    metadata = pyproject.read_text()

    assert "[project.urls]" in metadata
    assert 'Repository = "https://github.com/tjavanderwielen/geosplink"' in metadata
