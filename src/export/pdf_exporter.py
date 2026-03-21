from __future__ import annotations

from pathlib import Path
from typing import List


PAGE_WIDTH = 595
PAGE_HEIGHT = 842
MARGIN_X = 50
TOP_Y = 792
BOTTOM_Y = 60


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_line(text: str, max_chars: int) -> List[str]:
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [text[:max_chars]]

    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _markdown_to_pages(markdown_text: str) -> List[List[tuple[str, int, int]]]:
    pages: List[List[tuple[str, int, int]]] = [[]]
    y = TOP_Y

    def add_page() -> None:
        nonlocal y
        pages.append([])
        y = TOP_Y

    for raw_line in markdown_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            y -= 14
            if y < BOTTOM_Y:
                add_page()
            continue

        if stripped.startswith("# "):
            font_size = 16
            leading = 24
            text = stripped[2:].strip()
            max_chars = 65
        elif stripped.startswith("## "):
            font_size = 13
            leading = 20
            text = stripped[3:].strip()
            max_chars = 80
        elif stripped.startswith("### "):
            font_size = 11
            leading = 18
            text = stripped[4:].strip()
            max_chars = 90
        elif stripped.startswith("- "):
            font_size = 10
            leading = 14
            text = f"• {stripped[2:].strip()}"
            max_chars = 95
        else:
            font_size = 10
            leading = 14
            text = stripped
            max_chars = 95

        for chunk in _wrap_line(text, max_chars):
            if y < BOTTOM_Y:
                add_page()
            pages[-1].append((chunk, font_size, y))
            y -= leading

    return [page for page in pages if page] or [[]]


def _pdf_stream_for_page(page: List[tuple[str, int, int]]) -> bytes:
    commands = ["BT"]
    for text, font_size, y in page:
        font_name = "/F2" if font_size >= 11 else "/F1"
        commands.append(f"{font_name} {font_size} Tf")
        commands.append(f"1 0 0 1 {MARGIN_X} {y} Tm")
        commands.append(f"({_escape_pdf_text(text)}) Tj")
    commands.append("ET")
    body = "\n".join(commands).encode("latin-1", errors="replace")
    return body


def _write_markdown_to_pdf(markdown_text: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pages = _markdown_to_pages(markdown_text)

    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")

    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Count {len(pages)} /Kids [{kids}] >>".encode("ascii"))

    font_regular_id = 3 + len(pages) * 2
    font_bold_id = font_regular_id + 1

    for index, page in enumerate(pages):
        page_object_id = 3 + index * 2
        stream_object_id = page_object_id + 1
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_regular_id} 0 R /F2 {font_bold_id} 0 R >> >> "
            f"/Contents {stream_object_id} 0 R >>"
        )
        objects.append(page_dict.encode("ascii"))
        stream = _pdf_stream_for_page(page)
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_id} 0 obj\n".encode("ascii"))
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("ascii")
    )
    out_path.write_bytes(bytes(pdf))
    return out_path


def export_pdf_set(board_markdown: str, regulator_markdown: str, client_markdown: str, out_dir: Path, audit_id: str = "audit") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "board_pdf": _write_markdown_to_pdf(board_markdown, out_dir / f"{audit_id}_board_memo.pdf"),
        "regulator_pdf": _write_markdown_to_pdf(regulator_markdown, out_dir / f"{audit_id}_regulator_memo.pdf"),
        "client_pdf": _write_markdown_to_pdf(client_markdown, out_dir / f"{audit_id}_client_report.pdf"),
    }
