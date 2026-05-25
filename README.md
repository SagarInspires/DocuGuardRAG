
````md
# DocuGuard RAG

DocuGuard RAG is a production-style Retrieval-Augmented Generation backend for asking questions over technical documents, research papers, notes, and LaTeX/Markdown files.

The project is built from scratch using FastAPI, ChromaDB, SentenceTransformers, BM25, cross-encoder reranking, citation validation, dynamic acronym expansion, and CI-backed retrieval evaluation.

---

## Key Features

- Multi-format ingestion:
  - PDF
  - Markdown
  - LaTeX `.tex`
- PDF parsing with page-level metadata
- OCR fallback foundation for scanned / OneNote-exported PDFs
- Token-based chunking with overlap
- ChromaDB vector store
- BM25 keyword retrieval
- Hybrid retrieval using vector search + BM25
- Cross-encoder reranking
- Document-specific acronym extraction and query expansion
- Source-filtered querying
- Citation and retrieved chunk return
- Safe no-result guard
- LLM fallback handling for quota/provider errors
- Document listing and deletion
- Retrieval evaluation with golden QA dataset
- CI quality gate using GitHub Actions

---

## Architecture

```text
Document Upload
      ↓
Parser
(PDF / Markdown / LaTeX / OCR fallback)
      ↓
Acronym Extraction
      ↓
Token Chunking
      ↓
Embeddings + ChromaDB
      ↓
BM25 Keyword Index
      ↓
Hybrid Retrieval
(Vector + BM25)
      ↓
Cross-Encoder Reranking
      ↓
Context Builder
      ↓
LLM Answer Generation
      ↓
Citation Validation
      ↓
Answer + Citations + Retrieved Evidence
````

---

## Tech Stack

| Layer          | Technology                  |
| -------------- | --------------------------- |
| Backend        | FastAPI                     |
| PDF parsing    | PyMuPDF                     |
| OCR fallback   | Tesseract OCR + pytesseract |
| Embeddings     | SentenceTransformers        |
| Vector DB      | ChromaDB                    |
| Keyword Search | rank-bm25                   |
| Reranking      | CrossEncoder                |
| LLM            | Gemini API                  |
| Evaluation     | Custom golden QA evaluation |
| CI             | GitHub Actions              |

---

## API Endpoints

### Health Check

```http
GET /
```

Returns backend status.

---

### Upload Document

```http
POST /documents/upload
```

Supported formats:

```text
.pdf
.md
.markdown
.tex
```

Returns:

```json
{
  "message": "File uploaded and indexed successfully",
  "filename": "paper.pdf",
  "document_units_extracted": 10,
  "chunks_created": 39,
  "chunks_indexed": 39,
  "bm25_chunks_indexed": 39,
  "acronyms_extracted": 26
}
```

---

### List Documents

```http
GET /documents/
```

Returns uploaded documents.

---

### Delete Document

```http
DELETE /documents/{filename}
```

Deletes the document and its indexed vector chunks.

---

### Query Documents

```http
POST /query/
```

Example request:

```json
{
  "question": "What is OCFAB in CFAT?",
  "top_k": 3,
  "source": "Ray_CFAT_Unleashing_Triangular_Windows_for_Image_Super-resolution_CVPR_2024_paper (1).pdf",
  "retrieval_mode": "hybrid"
}
```

Example response includes:

```json
{
  "answer": "...",
  "citations": [
    {
      "source": "paper.pdf",
      "page": 2,
      "chunk_id": "paper.pdf_p2_c1"
    }
  ],
  "retrieved_chunks": [
    {
      "chunk_id": "...",
      "text": "...",
      "source": "paper.pdf",
      "page": 2,
      "section": "",
      "extraction_method": "pymupdf",
      "distance": 0.72,
      "hybrid_score": 0.75,
      "rerank_score": 5.04
    }
  ]
}
```

---

## Retrieval Pipeline

DocuGuard RAG uses a hybrid retrieval pipeline:

1. User question is expanded using document-specific acronyms.
2. ChromaDB vector search retrieves semantic candidates.
3. BM25 retrieves exact keyword/acronym matches.
4. Reciprocal-rank-style fusion combines results.
5. Cross-encoder reranker reorders chunks by query relevance.
6. Top chunks are passed to the LLM.
7. Citation validation checks answer grounding.

---

## Evaluation

The project includes a golden QA dataset:

```text
data/eval/golden_qa.csv
```

Evaluation documents are stored separately in:

```text
data/eval_docs/
```

Run evaluation index build:

```bash
python eval/build_eval_index.py
```

Run retrieval evaluation:

```bash
python eval/run_retrieval_eval.py
```

Current quality gate:

```text
Source Accuracy@3 >= 0.90
Location Recall@3 >= 0.80
```

Latest local result:

```text
Source Accuracy@3: 1.00
Location Recall@3: 1.00
Overall: PASSED
```

---

## GitHub Actions CI

This repository includes CI for retrieval quality:

```text
.github/workflows/rag_eval.yml
```

On every push or pull request, GitHub Actions:

1. Installs dependencies
2. Builds the evaluation index
3. Runs retrieval evaluation
4. Fails if retrieval quality drops below threshold

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/SagarInspires/DocuGuardRAG.git
cd DocuGuardRAG
```

### 2. Create virtual environment

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
```

### 5. Run backend

```bash
uvicorn app.main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## OCR Notes

DocuGuard RAG includes OCR fallback for scanned and OneNote-exported PDFs.

For OCR on Windows, install Tesseract OCR. The expected default path is:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

OCR is useful for scanned/OneNote PDFs, but handwritten notes may still be noisy. The system stores `extraction_method` metadata to show whether a chunk came from:

```text
pymupdf
ocr
pymupdf_ocr_failed
```

---

## What Makes This Project Different

Most RAG demos only do:

```text
PDF → chunks → embeddings → answer
```

DocuGuard RAG adds production-style components:

* hybrid retrieval
* reranking
* source filtering
* citation validation
* acronym-aware retrieval
* OCR fallback
* multi-format ingestion
* golden QA evaluation
* CI quality gate

---

## Future Improvements

* React frontend
* Docker setup
* user authentication
* persistent BM25 cache
* stronger OCR provider support
* answer faithfulness evaluation
* larger golden QA benchmark
* streaming responses
* deployment on cloud platform

---


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
