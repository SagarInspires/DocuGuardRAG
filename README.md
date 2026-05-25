## Frontend Dashboard

DocuGuard RAG includes a React + Vite frontend dashboard for interacting with the backend.

### Frontend Features

- Upload PDF / Markdown / LaTeX documents
- List indexed documents from ChromaDB
- Select document scope
- Ask questions using vector or hybrid retrieval
- Display generated answer
- Show citations
- Inspect retrieved chunks
- Show retrieval scores:
  - vector distance
  - hybrid score
  - rerank score
- Show extraction method:
  - pymupdf
  - ocr
  - pymupdf_ocr_failed
- Animated cyberpunk-style dashboard UI

### Run Frontend

Start backend first:

```bash
uvicorn app.main:app --reload
