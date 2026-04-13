"""
Test ingestion on a single file, printing each step of the pipeline.

Usage:
    python test_ingest.py                        # uses default test file
    python test_ingest.py path/to/your/file.docx
"""

import sys
from pathlib import Path

# Import the pipeline functions directly from ingest.py
from ingest import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    EMBED_MODEL,
    chunk_text,
    embed_texts,
    parse_docx,
    parse_pdf,
    parse_pptx,
    parse_mp4,
    chunk_id,
)

DEFAULT_FILE = "sources/Safety Policy and Protocols/Ladder and Fall Safety Protocol.docx"

SEPARATOR = "─" * 70


def print_section(title: str):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print('═' * 70)


def test_file(path: Path):
    ext = path.suffix.lower()

    print(f"\nFile : {path}")
    print(f"Type : {ext}")

    # ── Step 1: Parse ────────────────────────────────────────────────────
    print_section("STEP 1 — Parse raw text")

    if ext == ".docx":
        text = parse_docx(path)
        chunks_raw = None
    elif ext == ".pdf":
        text = parse_pdf(path)
        chunks_raw = None
    elif ext == ".pptx":
        chunks_raw = parse_pptx(path)   # pptx returns pre-chunked slides
        text = "\n\n".join(chunks_raw)
    elif ext == ".mp4":
        print("  (transcribing audio — this may take several minutes)")
        text = parse_mp4(path)
        chunks_raw = None
    else:
        print(f"Unsupported file type: {ext}")
        sys.exit(1)

    total_chars = len(text)
    total_lines = text.count("\n") + 1
    print(f"  Characters : {total_chars:,}")
    print(f"  Lines      : {total_lines:,}")
    print(f"\n  ── First 800 characters of extracted text ──")
    print(f"  {SEPARATOR}")
    for line in text[:800].splitlines():
        print(f"  {line}")
    if total_chars > 800:
        print(f"  ... ({total_chars - 800:,} more characters)")

    # ── Step 2: Chunk ────────────────────────────────────────────────────
    print_section("STEP 2 — Chunk text")

    if chunks_raw is not None:
        # pptx: already one chunk per slide
        chunks = chunks_raw
        print(f"  Strategy   : per-slide (pptx)")
    else:
        chunks = chunk_text(text)
        print(f"  Strategy   : paragraph-aware, {CHUNK_SIZE} chars / {CHUNK_OVERLAP} overlap")

    print(f"  Total chunks: {len(chunks)}")
    print(f"  Chunk sizes : min={min(len(c) for c in chunks)}, "
          f"max={max(len(c) for c in chunks)}, "
          f"avg={sum(len(c) for c in chunks)//len(chunks)}")

    print(f"\n  ── All chunks (truncated to 300 chars each) ──")
    for i, chunk in enumerate(chunks):
        preview = chunk[:300].replace("\n", " ")
        if len(chunk) > 300:
            preview += f"... [{len(chunk)} chars total]"
        print(f"\n  Chunk {i+1}/{len(chunks)}  ({len(chunk)} chars)")
        print(f"  {SEPARATOR}")
        print(f"  {preview}")

    # ── Step 3: Embed ────────────────────────────────────────────────────
    print_section("STEP 3 — Generate embeddings")
    print(f"  Model : {EMBED_MODEL}  (local, no API key)")
    print(f"  Loading model...")

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)

    print(f"  Embedding {len(chunks)} chunk(s)...")
    embeddings = embed_texts(chunks, model)

    dims = len(embeddings[0])
    print(f"  Embedding dimensions : {dims}")
    print(f"  Chunks embedded      : {len(embeddings)}")
    print(f"\n  ── First embedding vector (first 8 of {dims} values) ──")
    print(f"  {embeddings[0][:8]}")

    # ── Step 4: IDs & metadata ───────────────────────────────────────────
    print_section("STEP 4 — Chunk IDs and metadata")

    source_rel = str(path.relative_to(Path("sources"))) if "sources" in path.parts else str(path)
    for i, chunk in enumerate(chunks):
        cid = chunk_id(source_rel, i)
        print(f"  [{i}] id={cid}  source={source_rel}  chunk_index={i}")

    # ── Summary ──────────────────────────────────────────────────────────
    print_section("SUMMARY")
    print(f"  File         : {path.name}")
    print(f"  Parsed chars : {total_chars:,}")
    print(f"  Chunks       : {len(chunks)}")
    print(f"  Embed dims   : {dims}")
    print(f"\n  ✓ Pipeline looks correct. Run 'python ingest.py' to ingest all files.\n")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_FILE)

    if not target.exists():
        print(f"ERROR: File not found: {target}")
        sys.exit(1)

    test_file(target)
