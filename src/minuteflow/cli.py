from __future__ import annotations

import json
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import typer

from minuteflow.config import RuntimeConfig
from minuteflow.mcp import document_server, media_server, pipeline_server, transcription_server
from minuteflow.services.pipeline import MeetingPipelineService

app = typer.Typer(help="Local-first meeting workflow utilities.")
mcp_app = typer.Typer(help="Run MCP servers.")
workflow_app = typer.Typer(help="Run the meeting workflow directly.")
config_app = typer.Typer(help="Print ready-to-paste MCP configuration snippets.")
install_app = typer.Typer(help="Install local skill links.")
doctor_app = typer.Typer(help="Check local runtime readiness.")

app.add_typer(mcp_app, name="mcp")
app.add_typer(workflow_app, name="workflow")
app.add_typer(config_app, name="config")
app.add_typer(install_app, name="install")
app.add_typer(doctor_app, name="doctor")


def _project_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in [current.parent, *current.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("Unable to locate project root from cli.py")


def _genmate_payload(root: Path) -> dict:
    return {
        "mcpServers": {
            "minuteflow-media": {
                "command": "uv",
                "args": ["run", "--directory", str(root), "minuteflow", "mcp", "media"],
            },
            "minuteflow-documents": {
                "command": "uv",
                "args": ["run", "--directory", str(root), "minuteflow", "mcp", "documents"],
            },
            "minuteflow-transcription": {
                "command": "uv",
                "args": ["run", "--directory", str(root), "minuteflow", "mcp", "transcription"],
            },
            "minuteflow-pipeline": {
                "command": "uv",
                "args": ["run", "--directory", str(root), "minuteflow", "mcp", "pipeline"],
            },
        }
    }


def _codex_snippet(root: Path) -> str:
    lines = [
        '[mcp_servers.minuteflow_media]',
        'command = "uv"',
        f'args = ["run", "--directory", "{root}", "minuteflow", "mcp", "media"]',
        f'cwd = "{root}"',
        "",
        '[mcp_servers.minuteflow_documents]',
        'command = "uv"',
        f'args = ["run", "--directory", "{root}", "minuteflow", "mcp", "documents"]',
        f'cwd = "{root}"',
        "",
        '[mcp_servers.minuteflow_transcription]',
        'command = "uv"',
        f'args = ["run", "--directory", "{root}", "minuteflow", "mcp", "transcription"]',
        f'cwd = "{root}"',
        "",
        '[mcp_servers.minuteflow_pipeline]',
        'command = "uv"',
        f'args = ["run", "--directory", "{root}", "minuteflow", "mcp", "pipeline"]',
        f'cwd = "{root}"',
    ]
    return "\n".join(lines)


def _write_if_requested(content: str, output_path: str | None) -> None:
    if not output_path:
        return
    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _upsert_codex_config_block(config_path: Path, snippet: str) -> None:
    begin_marker = "# BEGIN minuteflow MCP"
    end_marker = "# END minuteflow MCP"
    legacy_begin_marker = "# BEGIN ai_meeting MCP"
    legacy_end_marker = "# END ai_meeting MCP"
    block = f"{begin_marker}\n{snippet}\n{end_marker}\n"

    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    for old_begin, old_end in [
        (legacy_begin_marker, legacy_end_marker),
        (begin_marker, end_marker),
    ]:
        if old_begin in existing and old_end in existing:
            start = existing.index(old_begin)
            end = existing.index(old_end) + len(old_end)
            existing = (existing[:start].rstrip() + "\n\n" + existing[end:].lstrip("\n")).strip()
    if begin_marker in existing and end_marker in existing:
        start = existing.index(begin_marker)
        end = existing.index(end_marker) + len(end_marker)
        updated = existing[:start].rstrip() + "\n\n" + block
        if end < len(existing):
            updated += existing[end:].lstrip("\n")
    else:
        updated = existing.rstrip()
        if updated:
            updated += "\n\n"
        updated += block

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(updated, encoding="utf-8")


def _find_genmate_settings_file() -> Path | None:
    candidate_roots = [
        Path.home() / "Library" / "Application Support" / "JetBrains",
        Path.home() / ".config" / "JetBrains",
        Path.home() / "AppData" / "Roaming" / "JetBrains",
    ]
    matches: list[Path] = []
    for root in candidate_roots:
        if not root.exists():
            continue
        matches.extend(root.rglob("GenMatePlugin.xml"))
    if not matches:
        return None
    matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0]


def _upsert_genmate_settings(settings_path: Path, mcp_json: str) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        tree = ET.parse(settings_path)
        root = tree.getroot()
    else:
        root = ET.Element("application")
        tree = ET.ElementTree(root)

    component = None
    for element in root.findall("component"):
        if element.get("name") == "com.genmate.plugin.settings.GenMateSettingsState":
            component = element
            break
    if component is None:
        component = ET.SubElement(root, "component", {"name": "com.genmate.plugin.settings.GenMateSettingsState"})

    option = None
    for element in component.findall("option"):
        if element.get("name") == "mcpServersJson":
            option = element
            break
    if option is None:
        option = ET.SubElement(component, "option", {"name": "mcpServersJson"})
    option.set("value", mcp_json)
    tree.write(settings_path, encoding="utf-8", xml_declaration=True)


@mcp_app.command("media")
def mcp_media() -> None:
    media_server.main()


@mcp_app.command("documents")
def mcp_documents() -> None:
    document_server.main()


@mcp_app.command("transcription")
def mcp_transcription() -> None:
    transcription_server.main()


@mcp_app.command("pipeline")
def mcp_pipeline() -> None:
    pipeline_server.main()


@workflow_app.command("run")
def workflow_run(
    media_path: str = typer.Option(..., "--media"),
    document_paths: list[str] = typer.Option([], "--doc"),
    output_dir: str = typer.Option("./artifacts", "--output-dir"),
    user_request: str = typer.Option("", "--question"),
    include_visual_analysis: bool = typer.Option(True, "--visual/--no-visual"),
    include_llm_summary: bool = typer.Option(True, "--summary/--no-summary"),
) -> None:
    service = MeetingPipelineService(config=RuntimeConfig.from_env())
    result = service.run(
        media_path=media_path,
        document_paths=document_paths,
        output_dir=output_dir,
        user_request=user_request,
        include_visual_analysis=include_visual_analysis,
        include_llm_summary=include_llm_summary,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@config_app.command("genmate")
def config_genmate() -> None:
    root = _project_root()
    payload = _genmate_payload(root)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    typer.echo(rendered)


@config_app.command("codex")
def config_codex() -> None:
    root = _project_root()
    typer.echo(_codex_snippet(root))


@install_app.command("codex-skill")
def install_codex_skill() -> None:
    root = _project_root()
    source = root / "skills" / "meeting-orchestrator"
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    target = codex_home / "skills" / "meeting-orchestrator"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(source)
    typer.echo(f"Installed Codex skill link: {target} -> {source}")


@install_app.command("codex")
def install_codex() -> None:
    root = _project_root()
    install_codex_skill()
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex"))
    config_path = codex_home / "config.toml"
    _upsert_codex_config_block(config_path, _codex_snippet(root))
    typer.echo(f"Updated Codex MCP config: {config_path}")


@install_app.command("genmate")
def install_genmate(
    settings_file: str = typer.Option("", "--settings-file", help="Optional absolute path to GenMatePlugin.xml"),
) -> None:
    root = _project_root()
    payload = _genmate_payload(root)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    workspace_json = root / ".genmate" / "mcpServers.json"
    workspace_json.parent.mkdir(parents=True, exist_ok=True)
    workspace_json.write_text(rendered, encoding="utf-8")
    typer.echo(f"Wrote workspace MCP JSON: {workspace_json}")

    resolved_settings = Path(settings_file).expanduser().resolve() if settings_file else _find_genmate_settings_file()
    if resolved_settings is None:
        typer.echo("GenMate settings file not found automatically. Import the JSON above or use --settings-file.")
        raise typer.Exit(code=0)

    _upsert_genmate_settings(resolved_settings, rendered)
    typer.echo(f"Updated GenMate settings: {resolved_settings}")


@doctor_app.command("check")
def doctor_check() -> None:
    config = RuntimeConfig.from_env()
    root = _project_root()
    checks = {
        "project_root": str(root),
        "uv": shutil.which("uv") or "",
        "ffmpeg": shutil.which("ffmpeg") or "",
        "ffprobe": shutil.which("ffprobe") or "",
        "faster_whisper": _module_available("faster_whisper"),
        "whisperx": _module_available("whisperx"),
        "pyannote.audio": _module_available("pyannote.audio"),
        "llm_configured": config.llm.is_configured,
        "multimodal_configured": config.multimodal.is_configured,
        "hf_token_configured": bool(config.huggingface_token),
    }
    typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))


def _module_available(module_name: str) -> bool:
    try:
        __import__(module_name)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    app()
