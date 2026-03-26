import json
from pathlib import Path

from typer.testing import CliRunner

from minuteflow.cli import app

runner = CliRunner()


def test_config_genmate_uses_repo_root() -> None:
    result = runner.invoke(app, ["config", "genmate"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    repo_root = Path(__file__).resolve().parents[1]
    args = payload["mcpServers"]["minuteflow-pipeline"]["args"]

    assert str(repo_root) in args


def test_install_codex_writes_config_block(monkeypatch, tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    result = runner.invoke(app, ["install", "codex"])

    assert result.exit_code == 0
    config_text = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert "# BEGIN minuteflow MCP" in config_text
    assert "minuteflow_pipeline" in config_text
    assert (codex_home / "skills" / "meeting-orchestrator").is_symlink()


def test_install_codex_replaces_legacy_config_block(monkeypatch, tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    config_path = codex_home / "config.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        '\n'.join(
            [
                'model = "gpt-5.4"',
                "",
                "# BEGIN ai_meeting MCP",
                "[mcp_servers.ai_meeting_pipeline]",
                'command = "uv"',
                '# END ai_meeting MCP',
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["install", "codex"])

    assert result.exit_code == 0
    config_text = config_path.read_text(encoding="utf-8")
    assert "# BEGIN ai_meeting MCP" not in config_text
    assert "ai_meeting_pipeline" not in config_text
    assert "# BEGIN minuteflow MCP" in config_text
