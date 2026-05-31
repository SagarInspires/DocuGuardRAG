const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function readErrorMessage(response, fallbackMessage) {
  try {
    const errorData = await response.json();
    return errorData.detail || fallbackMessage;
  } catch {
    try {
      const errorText = await response.text();
      return errorText || fallbackMessage;
    } catch {
      return fallbackMessage;
    }
  }
}

export async function uploadDocument(file, options = {}) {
  const formData = new FormData();

  formData.append("file", file);

  formData.append("document_type", options.documentType || "auto");
  formData.append("extraction_mode", options.extractionMode || "auto");
  formData.append("layout_mode", options.layoutMode || "auto");

  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const message = await readErrorMessage(
      response,
      "Document upload failed"
    );
    throw new Error(message);
  }

  return response.json();
}

export async function listDocuments() {
  const response = await fetch(`${API_BASE_URL}/documents/`);

  if (!response.ok) {
    const message = await readErrorMessage(
      response,
      "Failed to fetch documents"
    );
    throw new Error(message);
  }

  return response.json();
}

export async function deleteDocument(filename) {
  const response = await fetch(
    `${API_BASE_URL}/documents/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const message = await readErrorMessage(
      response,
      "Failed to delete document"
    );
    throw new Error(message);
  }

  return response.json();
}

export async function askQuestion({ question, source, topK, retrievalMode }) {
  const response = await fetch(`${API_BASE_URL}/query/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      question,
      source: source || null,
      top_k: topK,
      retrieval_mode: retrievalMode,
    }),
  });

  if (!response.ok) {
    const message = await readErrorMessage(response, "Query failed");
    throw new Error(message);
  }

  return response.json();
}