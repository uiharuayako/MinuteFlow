from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from minuteflow.services.media import MediaService

mcp = FastMCP("minuteflow-media")
service = MediaService()


@mcp.tool()
def inspect_media(path: str) -> dict:
    """Inspect a local audio/video file with ffprobe."""
    return service.inspect(path)


@mcp.tool()
def extract_audio(input_path: str, output_path: str, sample_rate: int = 16000, channels: int = 1) -> dict:
    """Extract a mono WAV track from a local media file."""
    return service.extract_audio(input_path=input_path, output_path=output_path, sample_rate=sample_rate, channels=channels)


@mcp.tool()
def extract_frames(video_path: str, output_dir: str, interval_seconds: float = 20.0, max_frames: int = 8) -> dict:
    """Extract representative video frames for multimodal analysis."""
    return service.extract_frames(
        video_path=video_path,
        output_dir=output_dir,
        interval_seconds=interval_seconds,
        max_frames=max_frames,
    )


def main(transport: str = "stdio", mount_path: str | None = None) -> None:
    mcp.run(transport=transport, mount_path=mount_path)


if __name__ == "__main__":
    main()
