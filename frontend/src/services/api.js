import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "https://fastrag-1.onrender.com";

const api = axios.create({
  baseURL: API_BASE_URL,
});

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload/pdf", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

export async function getDocumentStatus(documentId) {
  const response = await api.get(`/documents/${documentId}/status`);
  return response.data;
}

export async function askQuestion(question, documentId, fastMode = false) {
  const response = await api.post("/ask", {
    question,
    document_id: documentId,
    match_count: 5,
    fast_mode: fastMode,
  });

  return response.data;
}
