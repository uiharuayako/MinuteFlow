from __future__ import annotations

from pathlib import Path

from minuteflow.config import RuntimeConfig
from minuteflow.models import VideoFrame, VisualAnalysisResult
from minuteflow.providers.openai_compatible import OpenAICompatibleClient
from minuteflow.services.media import MediaService
from minuteflow.utils import collect_texts


class VideoService:
    def __init__(self, config: RuntimeConfig, media_service: MediaService | None = None) -> None:
        self._config = config
        self._media_service = media_service or MediaService()

    def analyze_video(
        self,
        video_path: str,
        frames_dir: str,
        transcript_text: str = "",
        document_text: str = "",
        interval_seconds: float | None = None,
        max_frames: int | None = None,
    ) -> dict:
        manifest = self._media_service.extract_frames(
            video_path=video_path,
            output_dir=frames_dir,
            interval_seconds=interval_seconds or self._config.frame_interval_seconds,
            max_frames=max_frames or self._config.max_visual_frames,
        )
        frames = [VideoFrame(**frame) for frame in manifest["frames"]]
        warnings: list[str] = []
        summary_markdown = ""
        raw_response = None
        backend = "frames-only"

        if self._config.multimodal.is_configured:
            try:
                client = OpenAICompatibleClient(self._config.multimodal)
                response = client.vision_completion(
                    system_prompt=(
                        "You analyze meeting videos. Focus on slides, UI, whiteboards, visible decisions, action items, "
                        "and major visual changes. Keep the response concise and structured."
                    ),
                    user_prompt=self._build_visual_prompt(frames, transcript_text, document_text),
                    image_paths=[frame.path for frame in frames],
                )
                raw_response = response["raw"]
                summary_markdown = response["content"]
                backend = f"openai-compatible:{self._config.multimodal.model}"
            except Exception as exc:
                warnings.append(f"Multimodal analysis failed, frames retained only: {exc}")
        else:
            warnings.append("No multimodal endpoint configured; only frames were extracted")

        result = VisualAnalysisResult(
            video_path=str(Path(video_path).resolve()),
            frames=frames,
            backend=backend,
            summary_markdown=summary_markdown,
            raw_response=raw_response,
            warnings=warnings,
        )
        return result.model_dump()

    def _build_visual_prompt(self, frames: list[VideoFrame], transcript_text: str, document_text: str) -> str:
        frame_lines = [f"- frame {frame.index} at {frame.timestamp_seconds:.1f}s" for frame in frames]
        return collect_texts(
            [
                "Please inspect these meeting frames and summarize the visual content that matters for meeting notes.",
                "Frames:\n" + "\n".join(frame_lines),
                f"Transcript context:\n{transcript_text[:6000]}" if transcript_text else "",
                f"Document context:\n{document_text[:6000]}" if document_text else "",
                "Return sections: Visual timeline, Key evidence from visuals, Slide/UI findings, Action items or decisions hinted by the visuals.",
            ]
        )

