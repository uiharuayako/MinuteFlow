from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    start: float
    end: float
    word: str
    speaker: str | None = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[WordTiming] = Field(default_factory=list)


class TranscriptDocument(BaseModel):
    source_path: str
    media_type: str
    language: str | None = None
    backend: str
    audio_path: str
    diarization_enabled: bool = False
    segments: list[TranscriptSegment]
    warnings: list[str] = Field(default_factory=list)


class DocumentParseResult(BaseModel):
    source_path: str
    file_type: str
    title: str
    text: str
    backend: str
    warnings: list[str] = Field(default_factory=list)


class VideoFrame(BaseModel):
    index: int
    timestamp_seconds: float
    path: str


class VisualAnalysisResult(BaseModel):
    video_path: str
    frames: list[VideoFrame]
    backend: str
    summary_markdown: str = ""
    raw_response: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class MeetingPacket(BaseModel):
    run_dir: str
    media_path: str
    transcript_path: str | None = None
    transcript_markdown_path: str | None = None
    document_paths: list[str] = Field(default_factory=list)
    document_markdown_paths: list[str] = Field(default_factory=list)
    visual_analysis_path: str | None = None
    summary_path: str | None = None
    answer_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)

