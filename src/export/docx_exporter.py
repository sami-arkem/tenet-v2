from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

PACKAGE_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Tenet</Application>
</Properties>
"""


def _core_xml() -> str:
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Tenet Export</dc:title>
  <dc:creator>Tenet</dc:creator>
  <cp:lastModifiedBy>Tenet</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>
"""


def _paragraph_xml(text: str) -> str:
    safe_text = escape(text)
    return (
        "<w:p>"
        "<w:r>"
        f"<w:t xml:space=\"preserve\">{safe_text}</w:t>"
        "</w:r>"
        "</w:p>"
    )


def _heading_xml(text: str, level: int) -> str:
    safe_text = escape(text)
    style = f"Heading{level}"
    return (
        "<w:p>"
        "<w:pPr>"
        f"<w:pStyle w:val=\"{style}\"/>"
        "</w:pPr>"
        "<w:r>"
        f"<w:t xml:space=\"preserve\">{safe_text}</w:t>"
        "</w:r>"
        "</w:p>"
    )


def _bullet_xml(text: str) -> str:
    return _paragraph_xml(f"• {text}")


def _document_xml(markdown_text: str) -> str:
    paragraphs = []
    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            paragraphs.append(_paragraph_xml(""))
            continue
        if stripped.startswith("# "):
            paragraphs.append(_heading_xml(stripped[2:].strip(), level=1))
        elif stripped.startswith("## "):
            paragraphs.append(_heading_xml(stripped[3:].strip(), level=2))
        elif stripped.startswith("### "):
            paragraphs.append(_heading_xml(stripped[4:].strip(), level=3))
        elif stripped.startswith("- "):
            paragraphs.append(_bullet_xml(stripped[2:].strip()))
        else:
            paragraphs.append(_paragraph_xml(stripped))

    body = "".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:w10="urn:schemas-microsoft-com:office:word"
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
 xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 mc:Ignorable="w14 wp14">
  <w:body>
    {body}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>
"""

def _write_markdown_to_docx(markdown_text: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", CONTENT_TYPES_XML)
        archive.writestr("_rels/.rels", PACKAGE_RELS_XML)
        archive.writestr("docProps/app.xml", APP_XML)
        archive.writestr("docProps/core.xml", _core_xml())
        archive.writestr("word/document.xml", _document_xml(markdown_text))
    return out_path


def export_docx_set(board_markdown: str, regulator_markdown: str, client_markdown: str, out_dir: Path, audit_id: str = "audit") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "board_docx": _write_markdown_to_docx(board_markdown, out_dir / f"{audit_id}_board_memo.docx"),
        "regulator_docx": _write_markdown_to_docx(regulator_markdown, out_dir / f"{audit_id}_regulator_memo.docx"),
        "client_docx": _write_markdown_to_docx(client_markdown, out_dir / f"{audit_id}_client_report.docx"),
    }
