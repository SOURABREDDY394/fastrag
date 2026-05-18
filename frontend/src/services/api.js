import axios from "axios";

const RENDER_API_BASE_URL = "https://fastrag-1.onrender.com";
const configuredApiBaseUrl =
  import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
const normalizedApiBaseUrl = configuredApiBaseUrl.trim().replace(/\/+$/, "");
const isLocalApiBaseUrl = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(
  normalizedApiBaseUrl,
);

const API_BASE_URL =
  import.meta.env.PROD && isLocalApiBaseUrl
    ? RENDER_API_BASE_URL
    : normalizedApiBaseUrl || RENDER_API_BASE_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
});

export async function uploadPdf(file, options = {}) {
  const formData = new FormData();
  formData.append("file", file);
  if (Number.isInteger(options.pageOffset)) {
    formData.append("page_offset", String(options.pageOffset));
  }
  if (Number.isInteger(options.totalPages)) {
    formData.append("source_total_pages", String(options.totalPages));
  }

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
