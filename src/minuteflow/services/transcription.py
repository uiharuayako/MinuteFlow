from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from minuteflow.config import RuntimeConfig
from minuteflow.models import TranscriptDocument, TranscriptSegment, WordTiming
from minuteflow.services.media import MediaService
from minuteflow.utils import is_audio_path, is_video_path, normalize_path


class TranscriptionService:
    def __init__(self, config: RuntimeConfig, media_service: MediaService | None = None) -> None:
        self._config = config
        self._media_service = media_service or MediaService()

    def transcribe_media(
        self,
        path: str,
        output_audio_path: str | None = None,
        backend: str | None = None,
        diarize: bool = True,
    ) -> dict[str, Any]:
        source = normalize_path(path)
        if not source.exists():
            raise FileNotFoundError(f"Media file not found: {source}")

        media_type = "video" if is_video_path(source) else "audio" if is_audio_path(source) else "unknown"
        if media_type == "unknown":
            raise ValueError(f"Unsupported media input: {source}")

        audio_path = source
        if media_type == "video":
            if not output_audio_path:
                raise ValueError("output_audio_path is required when transcribing a video file")
            extracted = self._media_service.extract_audio(str(source), output_audio_path)
            audio_path = Path(extracted["audio_path"])

        resolved_backend = self._resolve_backend(backend)
        if resolved_backend == "whisperx":
            transcript = self._transcribe_with_whisperx(audio_path, source, media_type, diarize)
        elif resolved_backend == "faster-whisper":
            transcript = self._transcribe_with_faster_whisper(audio_path, source, media_type, diarize)
        else:
            raise ValueError(f"Unsupported transcription backend: {resolved_backend}")

        return transcript.model_dump()

    def _resolve_backend(self, requested: str | None) -> str:
        candidate = (requested or self._config.transcription_backend or "auto").strip().lower()
        if candidate != "auto":
            return candidate
        try:
            import whisperx  # noqa: F401

            return "whisperx"
        except Exception:
            return "faster-whisper"

    def _transcribe_with_faster_whisper(
        self,
        audio_path: Path,
        source_path: Path,
        media_type: str,
        diarize: bool,
    ) -> TranscriptDocument:
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Run `uv run minuteflow deps install transcription`."
            ) from exc

        device = "cpu" if self._config.whisper_device == "auto" else self._config.whisper_device
        compute_type = "int8" if self._config.whisper_compute_type == "auto" else self._config.whisper_compute_type
        model = WhisperModel(self._config.whisper_model, device=device, compute_type=compute_type)
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=self._config.transcription_language or None,
            word_timestamps=True,
            vad_filter=True,
        )

        diarization_segments: list[dict[str, Any]] = []
        warnings: list[str] = []
        if diarize:
            try:
                diarization_segments = self._run_pyannote_diarization(audio_path)
            except Exception as exc:
                warnings.append(str(exc))

        segments: list[TranscriptSegment] = []
        for segment in segments_iter:
            words = [
                WordTiming(
                    start=float(word.start or segment.start),
                    end=float(word.end or segment.end),
                    word=(word.word or "").strip(),
                )
                for word in (segment.words or [])
                if (word.word or "").strip()
            ]
            speaker = self._pick_speaker(segment.start, segment.end, words, diarization_segments) or "SPEAKER_00"
            for word in words:
                word.speaker = speaker
            segments.append(
                TranscriptSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=segment.text.strip(),
                    speaker=speaker,
                    words=words,
                )
            )

        return TranscriptDocument(
            source_path=str(source_path),
            media_type=media_type,
            language=getattr(info, "language", None),
            backend="faster-whisper",
            audio_path=str(audio_path),
            diarization_enabled=bool(diarization_segments),
            segments=segments,
            warnings=warnings,
        )

    def _transcribe_with_whisperx(
        self,
        audio_path: Path,
        source_path: Path,
        media_type: str,
        diarize: bool,
    ) -> TranscriptDocument:
        try:
            import whisperx
        except Exception as exc:
            raise RuntimeError("whisperx is not installed. Run `uv run minuteflow deps install whisperx`.") from exc

        device = "cpu" if self._config.whisper_device == "auto" else self._config.whisper_device
        compute_type = "int8" if self._config.whisper_compute_type == "auto" else self._config.whisper_compute_type
        model = whisperx.load_model(self._config.whisper_model, device, compute_type=compute_type)
        audio = whisperx.load_audio(str(audio_path))
        result = model.transcribe(audio, batch_size=8, language=self._config.transcription_language or None)

        warnings: list[str] = []
        language = result.get("language")
        try:
            align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
            result = whisperx.align(result["segments"], align_model, metadata, audio, device)
        except Exception as exc:
            warnings.append(f"Alignment skipped: {exc}")

        if diarize:
            try:
                if not self._config.huggingface_token:
                    raise RuntimeError("MINUTEFLOW_HF_TOKEN is missing; diarization skipped")
                diarize_model = whisperx.DiarizationPipeline(
                    use_auth_token=self._config.huggingface_token,
                    device=device,
                )
                diarization = diarize_model(str(audio_path))
                result = whisperx.assign_word_speakers(diarization, result)
            except Exception as exc:
                warnings.append(f"Diarization skipped: {exc}")

        segments: list[TranscriptSegment] = []
        for item in result["segments"]:
            words = [
                WordTiming(
                    start=float(word.get("start", item["start"])),
                    end=float(word.get("end", item["end"])),
                    word=(word.get("word") or "").strip(),
                    speaker=word.get("speaker"),
                )
                for word in item.get("words", [])
                if (word.get("word") or "").strip()
            ]
            speaker = item.get("speaker")
            if not speaker:
                speaker = self._pick_majority_speaker(words) or "SPEAKER_00"
            segments.append(
                TranscriptSegment(
                    start=float(item["start"]),
                    end=float(item["end"]),
                    text=item["text"].strip(),
                    speaker=speaker,
                    words=words,
                )
            )

        return TranscriptDocument(
            source_path=str(source_path),
            media_type=media_type,
            language=language,
            backend="whisperx",
            audio_path=str(audio_path),
            diarization_enabled=any(segment.speaker not in {None, "SPEAKER_00"} for segment in segments),
            segments=segments,
            warnings=warnings,
        )

    def _run_pyannote_diarization(self, audio_path: Path) -> list[dict[str, Any]]:
        if not self._config.huggingface_token:
            raise RuntimeError("MINUTEFLOW_HF_TOKEN is missing; diarization skipped")
        try:
            from pyannote.audio import Pipeline
        except Exception as exc:
            raise RuntimeError("pyannote.audio is not installed; diarization skipped") from exc

        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=self._config.huggingface_token,
        )
        diarization = pipeline(str(audio_path))
        segments: list[dict[str, Any]] = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker": speaker,
                }
            )
        return segments

    def _pick_speaker(
        self,
        start: float,
        end: float,
        words: list[WordTiming],
        diarization_segments: list[dict[str, Any]],
    ) -> str | None:
        speaker_votes: list[str] = []
        word_ranges = [(word.start, word.end) for word in words] or [(start, end)]
        for word_start, word_end in word_ranges:
            for diarization in diarization_segments:
                overlap = min(word_end, diarization["end"]) - max(word_start, diarization["start"])
                if overlap > 0:
                    speaker_votes.append(diarization["speaker"])
        if not speaker_votes:
            return None
        return Counter(speaker_votes).most_common(1)[0][0]

    def _pick_majority_speaker(self, words: list[WordTiming]) -> str | None:
        speakers = [word.speaker for word in words if word.speaker]
        if not speakers:
            return None
        return Counter(speakers).most_common(1)[0][0]
