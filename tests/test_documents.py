from pathlib import Path

from minuteflow.services.documents import DocumentService


def test_parse_text_document(tmp_path: Path) -> None:
    source = tmp_path / "agenda.md"
    source.write_text("# Agenda\n\n- Item 1\n- Item 2\n", encoding="utf-8")

    service = DocumentService()
    result = service.parse_document(str(source))

    assert result["backend"] == "plain-text"
    assert result["title"] == "agenda"
    assert "Item 1" in result["text"]

