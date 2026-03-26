from __future__ import annotations

from pathlib import Path

from minuteflow.config import RuntimeConfig
from minuteflow.models import MeetingPacket
from minuteflow.providers.openai_compatible import OpenAICompatibleClient
from minuteflow.services.documents import DocumentService
from minuteflow.services.media import MediaService
from minuteflow.services.transcription import TranscriptionService
from minuteflow.services.video import VideoService
from minuteflow.utils import collect_texts, ensure_directory, is_video_path, slugify, utc_now_compact, write_json, write_text


class MeetingPipelineService:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config
        self._media = MediaService()
        self._documents = DocumentService()
        self._transcription = TranscriptionService(config=config, media_service=self._media)
        self._video = VideoService(config=config, media_service=self._media)

    def run(
        self,
        media_path: str,
        document_paths: list[str] | None,
        output_dir: str,
        user_request: str = "",
        include_visual_analysis: bool = True,
        include_llm_summary: bool = True,
    ) -> dict:
        run_dir = ensure_directory(Path(output_dir) / f"run_{utc_now_compact()}_{slugify(Path(media_path).stem)}")
        transcript_dir = ensure_directory(run_dir / "transcription")
        documents_dir = ensure_directory(run_dir / "documents")
        visual_dir = ensure_directory(run_dir / "video")
        outputs_dir = ensure_directory(run_dir / "outputs")

        transcript = self._transcription.transcribe_media(
            path=media_path,
            output_audio_path=str(transcript_dir / "audio.wav"),
        )
        transcript_json_path = write_json(transcript_dir / "transcript.json", transcript)
        transcript_markdown_path = write_text(
            transcript_dir / "transcript.md",
            self._render_transcript_markdown(transcript),
        )

        parsed_documents: list[dict] = []
        document_markdown_paths: list[str] = []
        for document_path in document_paths or []:
            parsed = self._documents.parse_document(document_path)
            parsed_documents.append(parsed)
            markdown_path = write_text(
                documents_dir / f"{slugify(Path(document_path).stem)}.md",
                self._render_document_markdown(parsed),
            )
            document_markdown_paths.append(str(markdown_path))
        documents_manifest_path = write_json(documents_dir / "documents.json", parsed_documents)

        transcript_text = collect_texts(segment["text"] for segment in transcript["segments"])
        document_text = collect_texts(item["text"] for item in parsed_documents)

        visual_analysis_path: str | None = None
        visual_summary = ""
        warnings = list(transcript.get("warnings", []))
        if include_visual_analysis and is_video_path(media_path):
            visual_result = self._video.analyze_video(
                video_path=media_path,
                frames_dir=str(visual_dir / "frames"),
                transcript_text=transcript_text,
                document_text=document_text,
            )
            visual_analysis_path = str(write_json(visual_dir / "visual_analysis.json", visual_result))
            if visual_result.get("summary_markdown"):
                write_text(visual_dir / "visual_summary.md", visual_result["summary_markdown"])
                visual_summary = visual_result["summary_markdown"]
            warnings.extend(visual_result.get("warnings", []))

        summary_path: str | None = None
        answer_path: str | None = None
        if include_llm_summary and self._config.llm.is_configured:
            llm_client = OpenAICompatibleClient(self._config.llm)
            meeting_summary = llm_client.text_completion(
                system_prompt=(
                    "You are a meeting analyst. Produce a precise, structured meeting summary using transcript, materials, and "
                    "visual findings if present. Explicitly list action items, owners if inferable, open questions, and risks."
                ),
                user_prompt=self._build_summary_prompt(
                    transcript_text=transcript_text,
                    document_text=document_text,
                    visual_summary=visual_summary,
                ),
            )
            summary_path = str(write_text(outputs_dir / "meeting_summary.md", meeting_summary["content"]))
            write_json(outputs_dir / "meeting_summary.raw.json", meeting_summary["raw"])

            if user_request.strip():
                answer = llm_client.text_completion(
                    system_prompt="Answer the user's meeting question based only on the supplied meeting evidence.",
                    user_prompt=self._build_answer_prompt(
                        question=user_request,
                        transcript_text=transcript_text,
                        document_text=document_text,
                        visual_summary=visual_summary,
                    ),
                )
                answer_path = str(write_text(outputs_dir / "answer.md", answer["content"]))
                write_json(outputs_dir / "answer.raw.json", answer["raw"])
        else:
            warnings.append("No text LLM endpoint configured; packet created without model-generated summary")

        packet = MeetingPacket(
            run_dir=str(run_dir),
            media_path=str(Path(media_path).resolve()),
            transcript_path=str(transcript_json_path),
            transcript_markdown_path=str(transcript_markdown_path),
            document_paths=[str(Path(path).resolve()) for path in document_paths or []],
            document_markdown_paths=document_markdown_paths,
            visual_analysis_path=visual_analysis_path,
            summary_path=summary_path,
            answer_path=answer_path,
            warnings=warnings,
            suggested_next_steps=[
                f"Read transcript at {transcript_markdown_path}",
                f"Read parsed documents manifest at {documents_manifest_path}",
                "Use the packet JSON as the stable input for follow-up QA or agent workflows",
            ],
        )
        packet_path = write_json(outputs_dir / "meeting_packet.json", packet.model_dump())
        response = packet.model_dump()
        response["packet_path"] = str(packet_path)
        response["documents_manifest_path"] = str(documents_manifest_path)
        return response

    def answer_question(self, packet_path: str, question: str) -> dict:
        if not self._config.llm.is_configured:
            raise RuntimeError("No LLM endpoint configured. Set MINUTEFLOW_LLM_* environment variables first.")
        packet = Path(packet_path).resolve()
        payload = packet.read_text(encoding="utf-8")
        client = OpenAICompatibleClient(self._config.llm)
        answer = client.text_completion(
            system_prompt="Answer questions from a meeting packet. Cite concrete evidence from the packet when possible.",
            user_prompt=f"Meeting packet JSON:\n{payload}\n\nQuestion:\n{question}",
        )
        answer_path = packet.parent / "followup_answer.md"
        write_text(answer_path, answer["content"])
        write_json(packet.parent / "followup_answer.raw.json", answer["raw"])
        return {
            "packet_path": str(packet),
            "question": question,
            "answer_path": str(answer_path),
            "answer": answer["content"],
        }

    def _render_transcript_markdown(self, transcript: dict) -> str:
        lines = [
            f"# Transcript",
            "",
            f"- Source: `{transcript['source_path']}`",
            f"- Backend: `{transcript['backend']}`",
            f"- Language: `{transcript.get('language') or 'unknown'}`",
            "",
        ]
        for segment in transcript["segments"]:
            speaker = segment.get("speaker") or "UNKNOWN"
            lines.append(
                f"- [{segment['start']:.2f}s - {segment['end']:.2f}s] `{speaker}` {segment['text']}"
            )
        return "\n".join(lines)

    def _render_document_markdown(self, parsed: dict) -> str:
        return "\n".join(
            [
                f"# {parsed['title']}",
                "",
                f"- Source: `{parsed['source_path']}`",
                f"- Backend: `{parsed['backend']}`",
                "",
                parsed["text"],
            ]
        )

    def _build_summary_prompt(self, transcript_text: str, document_text: str, visual_summary: str) -> str:
        return collect_texts(
            [
                "Summarize the meeting. Distinguish facts from inference.",
                f"Transcript:\n{transcript_text[:18000]}",
                f"Meeting materials:\n{document_text[:12000]}" if document_text else "",
                f"Visual summary:\n{visual_summary[:6000]}" if visual_summary else "",
                "Return sections: Executive Summary, Timeline, Decisions, Action Items, Risks, Open Questions, Source Gaps.",
            ]
        )

    def _build_answer_prompt(self, question: str, transcript_text: str, document_text: str, visual_summary: str) -> str:
        return collect_texts(
            [
                f"Question:\n{question}",
                f"Transcript:\n{transcript_text[:18000]}",
                f"Meeting materials:\n{document_text[:12000]}" if document_text else "",
                f"Visual summary:\n{visual_summary[:6000]}" if visual_summary else "",
                "Answer in Chinese unless the question requests another language. Be explicit about uncertainty.",
            ]
        )

