# PestPro Field Assistant

An internal AI knowledge system for Pest Management Systems, Inc. Ask questions in plain English and get accurate answers drawn directly from company documents — SOPs, protocols, regulatory guidance, and more.

---

## Requirements

- Python 3.10 or higher
- [Homebrew](https://brew.sh) (macOS) — for installing ffmpeg
- An Anthropic API key

---

## Setup

### 1. Install ffmpeg

Required for processing MP4 files (meeting recordings). Skip if you have no MP4 source files.

```bash
brew install ffmpeg
```

### 2. Install Python dependencies

```bash
pip3 install -r requirements.txt
```

This installs all required packages including the local embedding model (`sentence-transformers`), ChromaDB, FastAPI, and the Anthropic SDK.

### 3. Configure your API key

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_key_here
```

No OpenAI key is needed — embeddings run locally.

### 4. Add your documents

Place your source documents inside the `sources/` folder. Subdirectories are supported at any depth. Supported formats:

| Format | Notes |
|--------|-------|
| `.docx` | Microsoft Word |
| `.pdf`  | PDF documents |
| `.pptx` | PowerPoint presentations |
| `.mp4`  | Video/audio — transcribed automatically via Whisper |

### 5. Ingest documents

This processes all files in `sources/`, generates embeddings, and stores them in a local vector database.

```bash
python3 ingest.py
```

Run time depends on the number and size of files. MP4 transcription is the slowest step. Re-running is safe — existing documents are updated, not duplicated.

### 6. Start the server

```bash
python3 -m uvicorn app:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

---

## Usage

Type any question into the chat interface and press Enter. The system retrieves the most relevant passages from your documents and generates an answer based solely on that content.

Each answer includes source citations. Click any source chip to view the exact passage from the document that was used.

To test the ingestion pipeline on a single file before running a full ingest:

```bash
python3 test_ingest.py
python3 test_ingest.py "sources/path/to/your/file.docx"
```

---

## Project Structure

```
pest/
├── sources/          # Your source documents (add files here)
├── static/
│   └── index.html    # Chat UI
├── chroma_db/        # Vector store — created on first ingest (do not commit)
├── app.py            # FastAPI server
├── ingest.py         # Document parsing and ingestion pipeline
├── query.py          # Retrieval and answer generation
├── test_ingest.py    # Single-file pipeline test
├── requirements.txt
├── .env              # Your API keys (do not commit)
└── .env.example      # Key template
```

---

## Re-ingesting After Changes

If you add or update documents, re-run `ingest.py`. It will update existing chunks and add new ones without duplicating.

If you need a completely clean slate (e.g. after changing embedding settings):

```bash
rm -rf chroma_db/
python3 ingest.py
```
