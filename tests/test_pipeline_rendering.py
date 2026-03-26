from minuteflow.config import RuntimeConfig, ModelEndpointConfig
from minuteflow.services.pipeline import MeetingPipelineService


def build_service() -> MeetingPipelineService:
    config = RuntimeConfig(
        llm=ModelEndpointConfig(),
        multimodal=ModelEndpointConfig(),
        huggingface_token="",
    )
    return MeetingPipelineService(config=config)


def test_render_transcript_markdown_contains_speaker() -> None:
    service = build_service()
    markdown = service._render_transcript_markdown(
        {
            "source_path": "/tmp/demo.wav",
            "backend": "faster-whisper",
            "language": "zh",
            "segments": [
                {"start": 0.0, "end": 1.5, "speaker": "SPEAKER_01", "text": "大家好"},
            ],
        }
    )

    assert "SPEAKER_01" in markdown
    assert "大家好" in markdown

