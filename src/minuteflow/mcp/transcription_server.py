from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from minuteflow.config import RuntimeConfig
from minuteflow.services.transcription import TranscriptionService

mcp = FastMCP("minuteflow-transcription")
service = TranscriptionService(config=RuntimeConfig.from_env())


@mcp.tool()
def transcribe_media(
    path: str,
    output_audio_path: str | None = None,
    backend: str = "auto",
    diarize: bool = True,
) -> dict:
    """Transcribe audio/video into timestamped segments with optional speaker diarization."""
    return service.transcribe_media(
        path=path,
        output_audio_path=output_audio_path,
        backend=backend,
        diarize=diarize,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

