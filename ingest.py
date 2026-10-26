"""Document ingestion and clause-aware chunking for ClauseLens AI.

Supports PDF (via pypdf), TXT, and Markdown files.
Splits on numbered clauses, headings, and Q&A blocks before paragraphs.
Explicitly rejects scanned PDFs (no OCR) with clear user feedback.
"""

from dataclasses import dataclass, asdict
import os
import re
from typing import Any, Dict, List, Optional
import pypdf
import config


@dataclass
class Chunk:
    chunk_id: str
    doc_name: str
    page: Optional[int]
    clause_label: str
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def embedding_text(self) -> str:
        """Prefixed text used for embedding representation."""
        label_part = f" [{self.clause_label}]" if self.clause_label else ""
        return f"{self.doc_name}{label_part}: {self.text}"


def extract_text_from_file(file_path: str, filename: Optional[str] = None) -> List[Dict[str, Any]]:
    """Extracts raw text pages from a file.
    
    Returns a list of dicts: [{"page": int or None, "text": str}]
    """
    fname = filename or os.path.basename(file_path)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > config.MAX_FILE_MB:
        raise ValueError(f"File '{fname}' ({file_size_mb:.1f} MB) exceeds maximum allowed size of {config.MAX_FILE_MB} MB")

    ext = os.path.splitext(fname)[1].lower()
    pages_data: List[Dict[str, Any]] = []

    if ext == ".pdf":
        try:
            reader = pypdf.PdfReader(file_path)
        except Exception as e:
            raise ValueError(f"Failed to parse PDF '{fname}': {e}")

        total_pages = len(reader.pages)
        if total_pages > config.MAX_PAGES:
            raise ValueError(f"PDF '{fname}' has {total_pages} pages, exceeding maximum limit of {config.MAX_PAGES}")

        total_text_chars = 0
        for p_idx, page in enumerate(reader.pages):
            p_text = page.extract_text() or ""
            total_text_chars += len(p_text.strip())
            pages_data.append({"page": p_idx + 1, "text": p_text})

        if total_text_chars == 0:
            raise ValueError(
                f"PDF '{fname}' contains no extractable text. Scanned documents or images "
                "without OCR are unsupported in this prototype."
            )

    elif ext in (".txt", ".md"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read file '{fname}': {e}")
        pages_data.append({"page": None, "text": content})

    else:
        raise ValueError(f"Unsupported file type '{ext}'. Supported types: .pdf, .txt, .md")

    return pages_data


def chunk_document(doc_name: str, pages_data: List[Dict[str, Any]]) -> List[Chunk]:
    """Splits document text into clause-aware chunks."""
    clean_name = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(doc_name)[0])
    chunks: List[Chunk] = []

    # Patterns matching headings and clauses
    clause_regex = re.compile(
        r"^(?:(#{1,4}\s+[^\n]+)|(?:(Section\s+[0-9]+(?:\.[0-9]+)*[^\n]*))|(?:([0-9]+\.[0-9]+(?:\.[0-9]+)*[^\n]*))|(?:(Q:\s+[^\n]+)))",
        re.MULTILINE
    )

    chunk_counter = 1

    for p_info in pages_data:
        page_num = p_info["page"]
        text = p_info["text"]
        if not text.strip():
            continue

        # Split text into candidate clause sections
        splits = list(clause_regex.finditer(text))
        if not splits:
            # Fall back to paragraph splitting
            sections = [("General", text)]
        else:
            sections = []
            prev_end = 0
            current_label = "Preamble"

            for match in splits:
                start, end = match.span()
                # Text before this match belongs to previous label
                pre_text = text[prev_end:start].strip()
                if pre_text:
                    sections.append((current_label, pre_text))
                
                # The match text itself forms the new label
                matched_str = match.group(0).strip()
                # Clean markdown heading hashes for display
                cleaned_label = re.sub(r"^#+\s*", "", matched_str)
                current_label = cleaned_label[:80]
                prev_end = start

            # Trailing text
            trailing = text[prev_end:].strip()
            if trailing:
                sections.append((current_label, trailing))

        # Sub-chunk sections exceeding CHUNK_MAX_CHARS
        for label, sec_text in sections:
            sec_text = sec_text.strip()
            if not sec_text:
                continue

            if len(sec_text) <= config.CHUNK_MAX_CHARS:
                c = Chunk(
                    chunk_id=f"{clean_name}_c{chunk_counter}",
                    doc_name=doc_name,
                    page=page_num,
                    clause_label=label,
                    text=sec_text
                )
                chunks.append(c)
                chunk_counter += 1
            else:
                # Split on paragraphs
                paragraphs = [p.strip() for p in sec_text.split("\n\n") if p.strip()]
                current_buf: List[str] = []
                current_len = 0

                for para in paragraphs:
                    if current_len + len(para) + 2 > config.CHUNK_MAX_CHARS and current_buf:
                        buf_text = "\n\n".join(current_buf)
                        c = Chunk(
                            chunk_id=f"{clean_name}_c{chunk_counter}",
                            doc_name=doc_name,
                            page=page_num,
                            clause_label=label,
                            text=buf_text
                        )
                        chunks.append(c)
                        chunk_counter += 1
                        current_buf = []
                        current_len = 0

                    if len(para) > config.CHUNK_MAX_CHARS:
                        # Split by sentence
                        sentences = re.split(r"(?<=[.!?])\s+", para)
                        for sent in sentences:
                            if not sent.strip():
                                continue
                            if current_len + len(sent) + 1 > config.CHUNK_MAX_CHARS and current_buf:
                                buf_text = " ".join(current_buf)
                                c = Chunk(
                                    chunk_id=f"{clean_name}_c{chunk_counter}",
                                    doc_name=doc_name,
                                    page=page_num,
                                    clause_label=label,
                                    text=buf_text
                                )
                                chunks.append(c)
                                chunk_counter += 1
                                current_buf = []
                                current_len = 0
                            current_buf.append(sent)
                            current_len += len(sent) + 1
                    else:
                        current_buf.append(para)
                        current_len += len(para) + 2

                if current_buf:
                    buf_text = "\n\n".join(current_buf)
                    c = Chunk(
                        chunk_id=f"{clean_name}_c{chunk_counter}",
                        doc_name=doc_name,
                        page=page_num,
                        clause_label=label,
                        text=buf_text
                    )
                    chunks.append(c)
                    chunk_counter += 1

    return chunks
