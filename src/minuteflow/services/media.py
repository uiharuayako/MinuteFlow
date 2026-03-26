from __future__ import annotations

from pathlib import Path

from minuteflow.models import VideoFrame
from minuteflow.utils import ensure_directory, ffprobe_json, is_audio_path, is_video_path, normalize_path, run_command


class MediaService:
    def inspect(self, path: str) -> dict:
        source = normalize_path(path)
        if not source.exists():
            raise FileNotFoundError(f"Media file not found: {source}")
        probe = ffprobe_json(source)
        media_type = "video" if is_video_path(source) else "audio" if is_audio_path(source) else "unknown"
        return {
            "path": str(source),
            "media_type": media_type,
            "probe": probe,
        }

    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> dict:
        source = normalize_path(input_path)
        target = normalize_path(output_path)
        ensure_directory(target.parent)
        result = run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
                str(target),
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "ffmpeg failed while extracting audio")
        return {
            "input_path": str(source),
            "audio_path": str(target),
            "sample_rate": sample_rate,
            "channels": channels,
        }

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        interval_seconds: float = 20.0,
        max_frames: int = 8,
    ) -> dict:
        source = normalize_path(video_path)
        if not is_video_path(source):
            raise ValueError(f"Not a video file: {source}")
        destination = ensure_directory(output_dir)
        probe = ffprobe_json(source)
        duration = float(probe["format"].get("duration") or 0.0)
        timestamps = self._select_timestamps(duration, interval_seconds, max_frames)
        frames: list[VideoFrame] = []
        for index, timestamp in enumerate(timestamps, start=1):
            frame_path = destination / f"frame_{index:03d}.jpg"
            result = run_command(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{timestamp:.3f}",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(frame_path),
                ]
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"ffmpeg failed while extracting frame {index}")
            frames.append(VideoFrame(index=index, timestamp_seconds=timestamp, path=str(frame_path)))
        return {
            "video_path": str(source),
            "output_dir": str(destination),
            "duration_seconds": duration,
            "frames": [frame.model_dump() for frame in frames],
        }

    def _select_timestamps(self, duration: float, interval_seconds: float, max_frames: int) -> list[float]:
        if duration <= 0:
            return [0.0]
        timestamps = [0.0]
        current = interval_seconds
        while current < duration and len(timestamps) < max_frames:
            timestamps.append(current)
            current += interval_seconds
        if len(timestamps) < max_frames and timestamps[-1] < max(duration - 1.0, 0.0):
            timestamps.append(max(duration - 1.0, 0.0))
        return timestamps[:max_frames]

