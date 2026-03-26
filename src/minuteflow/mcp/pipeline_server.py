from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from minuteflow.config import RuntimeConfig
from minuteflow.services.pipeline import MeetingPipelineService

mcp = FastMCP("minuteflow-pipeline")
service = MeetingPipelineService(config=RuntimeConfig.from_env())


@mcp.tool()
def run_meeting_workflow(
    media_path: str,
    output_dir: str,
    document_paths: list[str] | None = None,
    user_request: str = "",
    include_visual_analysis: bool = True,
    include_llm_summary: bool = True,
) -> dict:
    """Run the end-to-end meeting workflow and emit a reusable meeting packet."""
    return service.run(
        media_path=media_path,
        document_paths=document_paths or [],
        output_dir=output_dir,
        user_request=user_request,
        include_visual_analysis=include_visual_analysis,
        include_llm_summary=include_llm_summary,
    )


@mcp.tool()
def answer_meeting_question(packet_path: str, question: str) -> dict:
    """Answer a follow-up question from a previously generated meeting packet."""
    return service.answer_question(packet_path=packet_path, question=question)


def main(transport: str = "stdio", mount_path: str | None = None) -> None:
    mcp.run(transport=transport, mount_path=mount_path)


if __name__ == "__main__":
    main()
