from __future__ import annotations

import json
import mimetypes
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
DOCUMENT_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".docx",
    ".pptx",
    ".pdf",
    ".xlsx",
    ".csv",
    ".json",
}


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def normalize_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_video_path(path: str | Path) -> bool:
    return normalize_path(path).suffix.lower() in VIDEO_EXTENSIONS


def is_audio_path(path: str | Path) -> bool:
    return normalize_path(path).suffix.lower() in AUDIO_EXTENSIONS


def is_document_path(path: str | Path) -> bool:
    return normalize_path(path).suffix.lower() in DOCUMENT_EXTENSIONS


def slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    normalized = normalized.strip("-")
    return normalized or "artifact"


def utc_now_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    ensure_directory(target.parent)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def write_text(path: str | Path, content: str) -> Path:
    target = Path(path)
    ensure_directory(target.parent)
    target.write_text(content, encoding="utf-8")
    return target


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def command_exists(name: str) -> bool:
    try:
        subprocess.run([name, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except FileNotFoundError:
        return False


def run_command(command: list[str], cwd: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def ffprobe_json(path: str | Path) -> dict[str, Any]:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-print_format",
            "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def collect_texts(values: Iterable[str]) -> str:
    return "\n\n".join(value.strip() for value in values if value and value.strip())


def guess_mime_type(path: str | Path) -> str:
    return mimetypes.guess_type(str(path))[0] or "application/octet-stream"

