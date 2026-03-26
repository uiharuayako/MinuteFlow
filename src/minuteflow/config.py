from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(slots=True)
class ModelEndpointConfig:
    base_url: str = ""
    model: str = ""
    api_key: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.model)


@dataclass(slots=True)
class RuntimeConfig:
    llm: ModelEndpointConfig
    multimodal: ModelEndpointConfig
    huggingface_token: str = ""
    transcription_backend: str = "auto"
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    transcription_language: str = ""
    max_visual_frames: int = 8
    frame_interval_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            llm=ModelEndpointConfig(
                base_url=_env("MINUTEFLOW_LLM_BASE_URL"),
                model=_env("MINUTEFLOW_LLM_MODEL"),
                api_key=_env("MINUTEFLOW_LLM_API_KEY"),
            ),
            multimodal=ModelEndpointConfig(
                base_url=_env("MINUTEFLOW_MM_BASE_URL"),
                model=_env("MINUTEFLOW_MM_MODEL"),
                api_key=_env("MINUTEFLOW_MM_API_KEY"),
            ),
            huggingface_token=_env("MINUTEFLOW_HF_TOKEN"),
            transcription_backend=_env("MINUTEFLOW_TRANSCRIPTION_BACKEND", "auto"),
            whisper_model=_env("MINUTEFLOW_WHISPER_MODEL", "small"),
            whisper_device=_env("MINUTEFLOW_WHISPER_DEVICE", "auto"),
            whisper_compute_type=_env("MINUTEFLOW_WHISPER_COMPUTE_TYPE", "auto"),
            transcription_language=_env("MINUTEFLOW_TRANSCRIPTION_LANGUAGE"),
            max_visual_frames=int(_env("MINUTEFLOW_MAX_VISUAL_FRAMES", "8")),
            frame_interval_seconds=float(_env("MINUTEFLOW_FRAME_INTERVAL_SECONDS", "20")),
        )

