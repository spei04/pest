# Deployment Guide — Render

## Prerequisites

- Code pushed to https://github.com/spei04/pest.git
- Anthropic API key
- Source documents on your local machine at `sources/`

---

## 1. Create the Web Service

1. Log in to [render.com](https://render.com) and click **New → Web Service**
2. Connect your GitHub account and select **spei04/pest**
3. Fill in the fields:

   | Field | Value |
   |---|---|
   | Name | `pest` (or anything you like) |
   | Region | Pick the one closest to you |
   | Branch | `main` |
   | Runtime | **Docker** |
   | Instance Type | **Starter** ($7/month) |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app:app --host 0.0.0.0 --port $PORT` |

4. Do **not** click Deploy yet — add the disk and env vars first.

---

## 2. Add a Persistent Disk

The vector database must survive deploys and restarts.

1. Scroll down to **Storage** and click **Add Disk**
2. Fill in:

   | Field | Value |
   |---|---|
   | Name | `chroma-data` |
   | Mount Path | `/data` |
   | Size | 1 GB |

---

## 3. Set Environment Variables

Under **Environment**, add these four variables:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `CHROMA_DIR` | `/data/chroma_db` |
| `SOURCES_DIR` | `/data/sources` |
| `UPLOAD_TOKEN` | any strong random string (e.g. `openssl rand -hex 32`) |

---

## 4. Deploy

Click **Create Web Service**. Render will:

1. Pull the repo
2. Build the Docker image (installs dependencies + downloads the embedding model — takes ~5 minutes on first build)
3. Start the server

Watch the build logs. The deploy is ready when you see:
```
Application startup complete.
```

---

## 5. Upload Source Documents

Render's SSH is interactive-only and does not support SCP. Instead, upload via the `/upload` endpoint built into the app.

First, generate a strong token and add it as the `UPLOAD_TOKEN` environment variable in Render:

```bash
openssl rand -hex 32
```

Then from your Mac terminal:

```bash
UPLOAD_TOKEN=your-token ./upload_sources.sh
```

This uploads every file in `sources/` directly to `/data/sources` on the server.

---

## 6. Run Ingest

Once the upload is complete, open the **Shell** tab in Render and run:

```bash
python ingest.py
```

This processes all documents and populates the vector database. Expect a few minutes depending on the number of files. You will see output like:

```
Found 48 files.
Loading embedding model 'all-MiniLM-L6-v2'...
Processing: PMi Company Protocols/Bed Bug Conventional Treatment Protocol 12172024.docx
  Ingested 12 chunks.
...
Done. 847 total chunks stored in '/data/chroma_db'.
```

---

## 7. Verify

Open your service URL (shown at the top of the Render dashboard). The chat interface should load and respond to questions.

---

## Re-deploying After Code Changes

Push to `main` — Render auto-deploys on every push.

The disk persists across deploys. You do not need to re-run `ingest.py` unless your source documents have changed.

## Re-ingesting After Document Changes

1. Run `UPLOAD_TOKEN=your-token ./upload_sources.sh` to upload new or updated files
2. Open the Render Shell and run `python ingest.py`

Re-running is safe — existing documents are updated, not duplicated.

## Disabling the Upload Endpoint

Once your documents are ingested, remove the `UPLOAD_TOKEN` environment variable from Render to disable the `/upload` endpoint.
