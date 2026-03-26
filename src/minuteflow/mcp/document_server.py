from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from minuteflow.services.documents import DocumentService

mcp = FastMCP("minuteflow-documents")
service = DocumentService()


@mcp.tool()
def parse_document(path: str) -> dict:
    """Parse a local meeting material document into normalized text."""
    return service.parse_document(path)


@mcp.tool()
def parse_documents(paths: list[str]) -> dict:
    """Parse multiple local meeting material documents."""
    return service.parse_documents(paths)


def main(transport: str = "stdio", mount_path: str | None = None) -> None:
    mcp.run(transport=transport, mount_path=mount_path)


if __name__ == "__main__":
    main()
