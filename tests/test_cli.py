import json
import sys
from pathlib import Path

from typer.testing import CliRunner

from minuteflow import cli

app = cli.app
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


def test_mcp_transcription_accepts_remote_transport(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_main(transport: str = "stdio", mount_path: str | None = None) -> None:
        captured["transport"] = transport
        captured["mount_path"] = mount_path

    monkeypatch.setattr(cli.transcription_server, "main", fake_main)

    result = runner.invoke(app, ["mcp", "transcription", "--transport", "streamable-http"])

    assert result.exit_code == 0
    assert captured == {"transport": "streamable-http", "mount_path": None}


def test_mcp_pipeline_accepts_sse_mount_path(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_main(transport: str = "stdio", mount_path: str | None = None) -> None:
        captured["transport"] = transport
        captured["mount_path"] = mount_path

    monkeypatch.setattr(cli.pipeline_server, "main", fake_main)

    result = runner.invoke(app, ["mcp", "pipeline", "--transport", "sse", "--mount-path", "/mcp"])

    assert result.exit_code == 0
    assert captured == {"transport": "sse", "mount_path": "/mcp"}


def test_deps_install_uses_project_requirements(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    project_root = tmp_path / "repo"
    requirements_dir = project_root / "requirements"
    requirements_dir.mkdir(parents=True)
    (requirements_dir / "transcription.txt").write_text("faster-whisper>=1.1.1\n", encoding="utf-8")

    def fake_project_root() -> Path:
        return project_root

    def fake_run(command: list[str], check: bool) -> None:
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr(cli, "_project_root", fake_project_root)
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = runner.invoke(app, ["deps", "install", "transcription"])

    assert result.exit_code == 0
    assert captured["check"] is True
    assert captured["command"] == [
        "uv",
        "pip",
        "install",
        "--python",
        sys.executable,
        "-r",
        str(requirements_dir / "transcription.txt"),
    ]
