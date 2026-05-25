import { useEffect, useMemo, useState } from "react";
import {
  uploadDocument,
  listDocuments,
  deleteDocument,
  askQuestion,
} from "./api";
import "./App.css";

function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedSource, setSelectedSource] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(3);
  const [retrievalMode, setRetrievalMode] = useState("hybrid");

  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState([]);
  const [retrievedChunks, setRetrievedChunks] = useState([]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadDocuments() {
    try {
      const data = await listDocuments();
      const docs = data.documents || [];
      setDocuments(docs);

      if (!selectedSource && docs.length > 0) {
        setSelectedSource(docs[0].filename);
      }
    } catch (error) {
      setMessage(error.message || "Failed to fetch documents.");
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function handleUpload() {
    if (!selectedFile) {
      setMessage("Please select a document first.");
      return;
    }

    try {
      setLoading(true);
      setMessage("Uploading and indexing document...");

      const data = await uploadDocument(selectedFile);

      setMessage(
        `Uploaded successfully: ${data.filename} • Indexed ${data.chunks_indexed} chunks`
      );

      setSelectedFile(null);
      await loadDocuments();
      setSelectedSource(data.filename);
    } catch (error) {
      setMessage(error.message || "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(filename) {
    try {
      setLoading(true);
      setMessage(`Deleting ${filename}...`);

      await deleteDocument(filename);

      setMessage(`Deleted: ${filename}`);

      if (selectedSource === filename) {
        setSelectedSource("");
      }

      await loadDocuments();
    } catch (error) {
      setMessage(error.message || "Delete failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleAsk() {
    if (!question.trim()) {
      setMessage("Please enter a question.");
      return;
    }

    try {
      setLoading(true);
      setMessage("Retrieving evidence and generating answer...");

      const data = await askQuestion({
        question,
        source: selectedSource || null,
        topK: Number(topK),
        retrievalMode,
      });

      setAnswer(data.answer || "");
      setCitations(data.citations || []);
      setRetrievedChunks(data.retrieved_chunks || []);
      setMessage("Query completed successfully.");
    } catch (error) {
      setMessage(error.message || "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  const statusTone = useMemo(() => {
    if (!message) return "";
    const lower = message.toLowerCase();

    if (
      lower.includes("failed") ||
      lower.includes("error") ||
      lower.includes("fetch")
    ) {
      return "error";
    }

    if (lower.includes("delete")) return "warning";

    return "info";
  }, [message]);

  return (
    <div className="page-shell">
      <div className="animated-bg" aria-hidden="true">
        <span className="orb orb-one" />
        <span className="orb orb-two" />
        <span className="orb orb-three" />

        <span className="flower flower-a" />
        <span className="flower flower-b" />
        <span className="flower flower-c" />
        <span className="flower flower-d" />

        <span className="mesh-grid" />
        <span className="noise-layer" />
      </div>

      <header className="topbar">
        <div className="topbar-left">
          <div className="brand-mark">DG</div>
          <span className="system-chip">Production RAG</span>
        </div>

        <div className="brand-title-wrap">
          <p className="brand-kicker">Evidence-first knowledge system</p>
          <h1 className="brand-title">DocuGuard RAG</h1>
        </div>

        <div className="topbar-pills">
          <span>FastAPI</span>
          <span>ChromaDB</span>
          <span>Hybrid</span>
          <span>Rerank</span>
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Knowledge Retrieval Workspace</p>
          <h2>
            Question your documents with evidence, citations, and measurable
            retrieval quality.
          </h2>
          <p className="hero-text">
            A production-style RAG dashboard for PDFs, Markdown, LaTeX, and
            OCR-backed notes. Upload, retrieve, inspect citations, and debug
            evidence chunks with scores.
          </p>

          <div className="hero-actions">
            <button onClick={handleAsk} disabled={loading}>
              {loading ? "Processing..." : "Run Query"}
            </button>
            <button
              className="secondary-btn"
              onClick={loadDocuments}
              disabled={loading}
            >
              Refresh Sources
            </button>
          </div>
        </div>

        <div className="hero-stats">
          <div className="stat-card">
            <span>Indexed Docs</span>
            <strong>{documents.length}</strong>
          </div>
          <div className="stat-card">
            <span>Citations</span>
            <strong>{citations.length}</strong>
          </div>
          <div className="stat-card">
            <span>Evidence</span>
            <strong>{retrievedChunks.length}</strong>
          </div>
          <div className="stat-card">
            <span>Mode</span>
            <strong>{retrievalMode}</strong>
          </div>
        </div>
      </section>

      {message && (
        <div className={`status-banner ${statusTone}`}>
          <span className="status-dot" />
          <span>{message}</span>
        </div>
      )}

      <section className="workspace-grid">
        <aside className="control-column">
          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-kicker">Ingestion</p>
                <h3>Upload Document</h3>
              </div>
              <span className="panel-badge">PDF / MD / TEX</span>
            </div>

            <div className="stack">
              <label className="field-label">Choose file</label>
              <input
                type="file"
                accept=".pdf,.md,.markdown,.tex"
                onChange={(event) => setSelectedFile(event.target.files[0])}
              />

              <button onClick={handleUpload} disabled={loading}>
                Upload & Index
              </button>
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-kicker">Document Scope</p>
                <h3>Source Library</h3>
              </div>
              <span className="panel-badge">{documents.length} loaded</span>
            </div>

            <div className="stack">
              <label className="field-label">Search scope</label>
              <select
                value={selectedSource}
                onChange={(event) => setSelectedSource(event.target.value)}
              >
                <option value="">Search all indexed documents</option>
                {documents.map((doc) => (
                  <option key={doc.filename} value={doc.filename}>
                    {doc.filename}
                  </option>
                ))}
              </select>
            </div>

            <div className="doc-list">
              {documents.length === 0 ? (
                <div className="empty-mini">No indexed documents found yet.</div>
              ) : (
                documents.map((doc) => (
                  <div className="doc-item" key={doc.filename}>
                    <div className="doc-meta">
                      <p className="doc-name">{doc.filename}</p>
                      <p className="doc-subtext">
                        {selectedSource === doc.filename
                          ? "Currently selected"
                          : "Available source"}
                      </p>
                    </div>

                    <div className="doc-actions">
                      <button
                        className="mini-btn"
                        onClick={() => setSelectedSource(doc.filename)}
                        disabled={loading}
                      >
                        Use
                      </button>
                      <button
                        className="mini-btn danger-btn"
                        onClick={() => handleDelete(doc.filename)}
                        disabled={loading}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="panel">
            <div className="panel-head">
              <div>
                <p className="panel-kicker">Retrieval</p>
                <h3>Settings</h3>
              </div>
            </div>

            <div className="stack">
              <label className="field-label">Top K</label>
              <input
                type="number"
                min="1"
                max="10"
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
              />

              <label className="field-label">Retrieval mode</label>
              <select
                value={retrievalMode}
                onChange={(event) => setRetrievalMode(event.target.value)}
              >
                <option value="hybrid">Hybrid</option>
                <option value="vector">Vector</option>
              </select>
            </div>
          </div>
        </aside>

        <section className="main-column">
          <div className="panel ask-panel">
            <div className="panel-head">
              <div>
                <p className="panel-kicker">Question Interface</p>
                <h3>Ask the System</h3>
              </div>
              <span className="panel-badge">
                {selectedSource || "All documents"}
              </span>
            </div>

            <div className="stack">
              <label className="field-label">Question</label>
              <textarea
                rows="5"
                value={question}
                placeholder="Example: What is OCFAB in CFAT?"
                onChange={(event) => setQuestion(event.target.value)}
              />

              <div className="action-row">
                <button onClick={handleAsk} disabled={loading}>
                  {loading ? "Processing..." : "Ask Question"}
                </button>
                <button
                  className="secondary-btn"
                  onClick={() => {
                    setQuestion("");
                    setAnswer("");
                    setCitations([]);
                    setRetrievedChunks([]);
                    setMessage("Workspace cleared.");
                  }}
                  disabled={loading}
                >
                  Clear Output
                </button>
              </div>
            </div>
          </div>

          <div className="result-grid">
            <div className="panel answer-panel">
              <div className="panel-head">
                <div>
                  <p className="panel-kicker">LLM Output</p>
                  <h3>Answer</h3>
                </div>
              </div>

              {answer ? (
                <div className="answer-box">{answer}</div>
              ) : (
                <div className="empty-state">
                  <h4>No answer yet</h4>
                  <p>
                    Ask a question to see a grounded response with citations and
                    inspectable evidence.
                  </p>
                </div>
              )}
            </div>

            <div className="panel citation-panel">
              <div className="panel-head">
                <div>
                  <p className="panel-kicker">Grounding</p>
                  <h3>Citations</h3>
                </div>
                <span className="panel-badge">{citations.length}</span>
              </div>

              {citations.length > 0 ? (
                <div className="citation-list">
                  {citations.map((citation, index) => (
                    <div
                      className="citation-card"
                      key={`${citation.chunk_id}-${index}`}
                    >
                      <p className="citation-source">{citation.source}</p>
                      <div className="meta-row">
                        <span>Page: {citation.page ?? "-"}</span>
                        <span>Chunk: {citation.chunk_id}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state compact">
                  <p>No citations yet.</p>
                </div>
              )}
            </div>
          </div>

          <div className="panel evidence-panel">
            <div className="panel-head">
              <div>
                <p className="panel-kicker">Retrieval Evidence</p>
                <h3>Retrieved Chunks</h3>
              </div>
              <span className="panel-badge">
                {retrievedChunks.length} chunks
              </span>
            </div>

            {retrievedChunks.length > 0 ? (
              <div className="chunk-list">
                {retrievedChunks.map((chunk, index) => (
                  <details
                    className="chunk-card"
                    key={chunk.chunk_id}
                    open={index === 0}
                  >
                    <summary>
                      <div className="chunk-summary">
                        <div>
                          <p className="chunk-title">{chunk.source}</p>
                          <p className="chunk-subtitle">
                            Page {chunk.page ?? "-"} • Section{" "}
                            {chunk.section || "-"} • Chunk #{chunk.chunk_index}
                          </p>
                        </div>

                        <div className="score-pills">
                          <span>
                            Rerank:{" "}
                            {typeof chunk.rerank_score === "number"
                              ? chunk.rerank_score.toFixed(2)
                              : "NA"}
                          </span>
                          <span>
                            Hybrid:{" "}
                            {typeof chunk.hybrid_score === "number"
                              ? chunk.hybrid_score.toFixed(2)
                              : "NA"}
                          </span>
                        </div>
                      </div>
                    </summary>

                    <div className="chunk-meta-row">
                      <span>Distance: {chunk.distance ?? "NA"}</span>
                      <span>Extraction: {chunk.extraction_method || "NA"}</span>
                      <span>ID: {chunk.chunk_id}</span>
                    </div>

                    <div className="chunk-body">{chunk.text}</div>
                  </details>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                <h4>No evidence retrieved yet</h4>
                <p>
                  Retrieved chunks will appear here with scores, source
                  metadata, and extraction method.
                </p>
              </div>
            )}
          </div>
        </section>
      </section>
    </div>
  );
}

export default App;