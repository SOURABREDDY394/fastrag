import { useEffect, useState } from "react";
import { PDFDocument } from "pdf-lib";
import {
  ArrowDown,
  ArrowUpRight,
  BookOpen,
  BrainCircuit,
  FileSearch,
  FileText,
  Layers3,
  MessageSquareText,
  Search,
  Sparkles,
} from "lucide-react";

import AnswerCard from "./components/AnswerCard";
import Navbar from "./components/Navbar";
import QuestionCard from "./components/QuestionCard";
import SourcesCard from "./components/SourcesCard";
import UploadCard from "./components/UploadCard";
import { askQuestion, getDocumentStatus, uploadPdf } from "./services/api";

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024;
const FAST_INDEX_BYTES = 50 * 1024 * 1024;
const FAST_INDEX_PAGES = 1;

const storyStages = [
  {
    number: "01",
    label: "Document Ingestion",
    title: "Upload PDF",
    text: "Drop in a study PDF and start a focused document workflow.",
    side: "left",
    icon: FileText,
    card: "upload",
  },
  {
    number: "02",
    label: "Document Index",
    title: "Index Document",
    text: "StudyRAG extracts pages, builds chunks, and prepares the PDF for fast retrieval.",
    side: "right",
    icon: Layers3,
    card: "index",
  },
  {
    number: "03",
    label: "Query Input",
    title: "Ask Question",
    text: "Ask exam-style questions directly against the indexed document.",
    side: "left",
    icon: MessageSquareText,
    card: "query",
  },
  {
    number: "04",
    label: "Retrieval Flow",
    title: "Retrieve Chunks",
    text: "The most relevant chunks are ranked with page context and match strength.",
    side: "right",
    icon: Search,
    card: "retrieve",
  },
  {
    number: "05",
    label: "Exam Answer",
    title: "Exam Answer",
    text: "StudyRAG turns matched evidence into a clear answer for revision.",
    side: "left",
    icon: BrainCircuit,
    card: "answer",
  },
  {
    number: "06",
    label: "Source Trace",
    title: "Sources",
    text: "Page references and chunk details stay visible so answers can be checked.",
    side: "right",
    icon: FileSearch,
    card: "sources",
  },
];

function simplifyError(error, fallbackMessage) {
  console.error("StudyRAG request failed:", error);

  if (error?.code === "ERR_NETWORK") {
    return "Could not reach the backend. Check the deployed API URL and CORS settings.";
  }

  if (error?.response?.status >= 500) {
    return fallbackMessage;
  }

  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.toLowerCase().includes("no relevant")) {
    return "No relevant chunks found. Try asking something from the uploaded PDF.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  return fallbackMessage;
}

function simplifyDocumentError(errorMessage) {
  if (!errorMessage) {
    return "Document processing failed.";
  }

  const normalizedMessage = errorMessage.toLowerCase();

  if (
    normalizedMessage.includes("scanned") ||
    normalizedMessage.includes("ocr") ||
    normalizedMessage.includes("tesseract")
  ) {
    return "This PDF appears to be scanned. OCR support is required to read it.";
  }

  if (
    normalizedMessage.includes("no readable text") ||
    normalizedMessage.includes("no extractable text") ||
    normalizedMessage.includes("no searchable chunks")
  ) {
    return "No readable text was found in this PDF.";
  }

  return errorMessage;
}

async function createFastIndexPdf(file) {
  if (file.size <= FAST_INDEX_BYTES) {
    return file;
  }

  const sourcePdf = await PDFDocument.load(await file.arrayBuffer(), {
    ignoreEncryption: true,
  });
  const fastPdf = await PDFDocument.create();
  const pageIndexes = Array.from(
    { length: Math.min(sourcePdf.getPageCount(), FAST_INDEX_PAGES) },
    (_, index) => index,
  );
  const copiedPages = await fastPdf.copyPages(sourcePdf, pageIndexes);

  copiedPages.forEach((page) => fastPdf.addPage(page));

  const fastPdfBytes = await fastPdf.save({ useObjectStreams: true });
  const fastPdfName = file.name.replace(/\.pdf$/i, "") + "-fast-index.pdf";

  return new File([fastPdfBytes], fastPdfName, {
    type: "application/pdf",
    lastModified: Date.now(),
  });
}

function MiniCard({ type }) {
  if (type === "upload") {
    return (
      <div className="mini-panel w-64">
        <p className="mini-label">PDF Upload</p>
        <div className="mt-4 border border-dashed border-teal-500/50 bg-teal-50 px-4 py-5 text-center">
          <FileText className="mx-auto text-teal-700" size={30} />
          <p className="mt-3 text-sm font-black text-charcoal">Study notes.pdf</p>
          <p className="text-xs font-bold text-teal-800">Selected - ready to upload</p>
        </div>
      </div>
    );
  }

  if (type === "index") {
    return (
      <div className="mini-panel w-72 bg-charcoal text-white">
        <p className="mini-label text-teal-200">Chunk Map</p>
        <div className="mt-5 space-y-3">
          {[
            ["Page 04", 82],
            ["Page 09", 64],
            ["Page 12", 92],
          ].map(([label, width]) => (
            <div key={label} className="flex items-center gap-3">
              <span className="w-14 text-xs font-black text-white/55">{label}</span>
              <span className="h-2 rounded-full bg-white/20" style={{ width: `${width}%` }} />
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs font-bold text-white/55">18 chunks indexed</p>
      </div>
    );
  }

  if (type === "query") {
    return (
      <div className="mini-panel w-72">
        <p className="mini-label">Question Input</p>
        <p className="mt-4 bg-slate-100 p-4 text-sm font-bold leading-6 text-charcoal">
          Explain deadlock prevention in simple points.
        </p>
        <div className="mt-3 flex gap-2 text-xs font-black text-teal-800">
          <span className="bg-teal-50 px-2 py-1">Exam notes</span>
          <span className="bg-teal-50 px-2 py-1">Fast mode</span>
        </div>
      </div>
    );
  }

  if (type === "retrieve") {
    return (
      <div className="mini-panel w-72 bg-[#f6f2ea]">
        <p className="mini-label">Retrieval Results</p>
        <div className="mt-4 space-y-3">
          {["Page 12 - 91% match", "Page 08 - 87% match", "Page 15 - 82% match"].map((item) => (
            <div key={item} className="flex items-center justify-between border-b border-slate-300 pb-2 text-sm">
              <span className="font-black text-charcoal">{item}</span>
              <span className="h-2 w-12 rounded-full bg-teal-500/70" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (type === "answer") {
    return (
      <div className="mini-panel w-72">
        <p className="mini-label">Answer Preview</p>
        <p className="mt-4 text-2xl font-black leading-tight text-charcoal">
          Deadlock prevention removes one required condition so a deadlock cannot form.
        </p>
        <p className="mt-4 text-xs font-black text-teal-700">Answered in 2.1s</p>
      </div>
    );
  }

  return (
    <div className="mini-panel w-72 bg-charcoal text-white">
      <p className="mini-label text-teal-200">Source Trace</p>
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm font-black">
        <span className="bg-white/10 px-3 py-2">Page 12</span>
        <span className="bg-white/10 px-3 py-2">Chunk 04</span>
        <span className="bg-teal-300 px-3 py-2 text-charcoal">91%</span>
        <span className="bg-white/10 px-3 py-2">Page 15</span>
      </div>
    </div>
  );
}

function HeroSection() {
  return (
    <section id="home" className="relative isolate overflow-hidden px-4 pb-16 pt-16 sm:px-6 lg:px-8">
      <div className="paper-grain" />
      <div className="mx-auto grid max-w-7xl items-end gap-12 lg:grid-cols-[0.92fr_1.08fr]">
        <div className="relative z-10 pb-8">
          <div className="mb-8 flex items-center gap-4">
            <span className="h-px w-16 bg-charcoal" />
            <span className="text-xs font-black uppercase tracking-[0.36em] text-teal-700">
              Study Journey
            </span>
          </div>
          <h1 className="text-7xl font-black leading-[0.84] text-charcoal sm:text-8xl lg:text-9xl">
            Study<span className="text-teal-600">RAG</span>
          </h1>
          <p className="mt-8 max-w-2xl text-3xl font-black leading-tight text-charcoal sm:text-4xl">
            Upload study materials and get accurate, exam-ready answers with page references.
          </p>
          <p className="mt-6 max-w-xl text-base leading-8 text-slate-600">
            StudyRAG indexes your PDFs once, then retrieves the most relevant
            parts for fast, focused study answers.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <a href="#workspace" className="editorial-button bg-charcoal text-white">
              Upload PDF
              <ArrowUpRight size={17} />
            </a>
            <a href="#story" className="editorial-button border border-charcoal/15 bg-white text-charcoal">
              Follow Flow
              <ArrowDown size={17} />
            </a>
          </div>
        </div>

        <div className="relative min-h-[520px]">
          <div className="hero-ink hero-ink-a" />
          <div className="hero-ink hero-ink-b" />
          <div className="absolute left-4 top-12 z-10 max-w-xs border-l-2 border-charcoal pl-5">
            <p className="text-7xl font-black leading-none text-charcoal">01+</p>
            <p className="mt-3 text-xl font-black uppercase tracking-wide text-charcoal">
              Upload to Answer
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Turn dense PDFs into exam-ready answers with page references.
            </p>
          </div>
          <div className="absolute bottom-10 right-0 z-10 w-80 border border-slate-200 bg-white p-6 shadow-2xl">
            <p className="text-xs font-black uppercase tracking-[0.28em] text-teal-700">Study Workspace</p>
            <div className="mt-5 space-y-3">
              {["Upload", "Index", "Ask", "Answer", "Sources"].map((item) => (
                <div key={item} className="flex items-center gap-3">
                  <span className="h-2 w-2 bg-charcoal" />
                  <span className="text-sm font-black text-charcoal">{item}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="absolute bottom-32 left-24 z-10 hidden rotate-[-5deg] bg-teal-700 px-6 py-8 text-white shadow-2xl sm:block">
            <Sparkles size={28} />
            <p className="mt-5 text-3xl font-black">2.1s</p>
            <p className="mt-2 max-w-40 text-xs leading-5 text-teal-50">
              Fast retrieval for focused study answers.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function StorySection({
  id = "story",
  stages = storyStages,
  kicker = "StudyRAG Journey",
  title = "Upload, index, ask, and trace every answer.",
  text = "Turn dense PDFs into exam-ready answers with page references.",
  compact = false,
}) {
  return (
    <section id={id} className={`relative px-4 sm:px-6 lg:px-8 ${compact ? "py-14" : "py-10"}`}>
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 grid gap-8 lg:grid-cols-[0.62fr_1fr] lg:items-end">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.36em] text-teal-700">{kicker}</p>
            <h2 className="mt-5 text-5xl font-black leading-none text-charcoal sm:text-7xl">
              {title}
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-8 text-slate-600">{text}</p>
        </div>

        <div className={`story-canvas ${compact ? "story-canvas-compact" : ""}`}>
          <div className="story-spine" aria-hidden="true">
            {[1, 2, 3, 4, 5, 6].map((piece) => (
              <span key={piece} className={`crack-piece crack-piece-${piece}`} />
            ))}
          </div>
          {stages.map((stage, index) => {
            const Icon = stage.icon;
            const isLeft = stage.side === "left";

            return (
              <article
                key={stage.title}
                className={`story-stage ${isLeft ? "story-left" : "story-right"}`}
                style={{ "--stage-offset": `${index * 10}px` }}
              >
                <div className="story-copy">
                  <div className="flex items-center gap-4">
                    <span className="text-6xl font-black leading-none text-charcoal">{stage.number}</span>
                    <span className="h-px flex-1 bg-charcoal/20" />
                  </div>
                  <p className="mt-4 text-xs font-black uppercase tracking-[0.28em] text-teal-700">
                    {stage.label}
                  </p>
                  <h3 className="mt-3 text-3xl font-black leading-tight text-charcoal">{stage.title}</h3>
                  <p className="mt-4 text-sm leading-7 text-slate-600">{stage.text}</p>
                </div>

                <div className="story-node">
                  <Icon size={24} />
                </div>

                <div className="story-card">
                  <MiniCard type={stage.card} />
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function WorkspaceSection(props) {
  return (
    <section id="workspace" className="relative px-4 py-20 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-10 grid gap-8 lg:grid-cols-[0.7fr_1fr] lg:items-end">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.36em] text-teal-700">Study Workspace</p>
            <h2 className="mt-5 text-5xl font-black leading-none text-charcoal sm:text-7xl">
              Study Workspace
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-8 text-slate-600">
            Upload a PDF, ask a question, and review the answer with source pages.
          </p>
        </div>

        <div className="workspace-paper">
          <div className="workspace-mark">WORKSPACE</div>
          <div className="grid gap-7 xl:grid-cols-[0.9fr_1.1fr]">
            <UploadCard {...props.uploadProps} />
            <QuestionCard {...props.questionProps} />
          </div>
          <div className="mt-7 grid gap-7">
            <AnswerCard {...props.answerProps} />
            <SourcesCard {...props.sourcesProps} />
          </div>
        </div>
      </div>
    </section>
  );
}

function FinalSection() {
  return (
    <section className="px-4 pb-20 sm:px-6 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-8 border-t border-charcoal/15 pt-12 lg:grid-cols-[1fr_0.8fr]">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.36em] text-teal-700">Source-Grounded Study</p>
          <h2 className="mt-5 text-5xl font-black leading-none text-charcoal sm:text-7xl">
            Start studying smarter with StudyRAG
          </h2>
        </div>
        <div className="self-end">
          <p className="text-base leading-8 text-slate-600">
            Upload a study PDF and turn it into a searchable, answer-ready study workspace.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <a href="#workspace" className="editorial-button bg-charcoal text-white">
              Upload a PDF
              <ArrowUpRight size={17} />
            </a>
            <a href="#question-panel" className="editorial-button border border-charcoal/15 bg-white text-charcoal">
              Try a Question
              <BookOpen size={17} />
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [documentStatus, setDocumentStatus] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const [question, setQuestion] = useState("");
  const [fastMode, setFastMode] = useState(false);
  const [answerResult, setAnswerResult] = useState(null);
  const [askError, setAskError] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  const uploadedDocumentId = uploadResult?.document_id || "";
  const isDocumentReady =
    documentStatus?.status === "ready" ||
    (documentStatus?.status === "processing" &&
      documentStatus?.total_pages > 0 &&
      documentStatus?.processed_pages >= documentStatus?.total_pages);

  useEffect(() => {
    if (!uploadedDocumentId) {
      return undefined;
    }

    let isActive = true;
    let intervalId;

    async function fetchStatus() {
      try {
        const status = await getDocumentStatus(uploadedDocumentId);

        if (!isActive) {
          return;
        }

        setDocumentStatus(status);

        if (status.status === "failed") {
          setUploadError(simplifyDocumentError(status.error_message));
        } else {
          setUploadError("");
        }

        if (status.status === "ready" || status.status === "failed") {
          window.clearInterval(intervalId);
        }
      } catch (error) {
        console.warn("Could not fetch document status yet:", error);
      }
    }

    fetchStatus();
    intervalId = window.setInterval(fetchStatus, 2500);

    return () => {
      isActive = false;
      window.clearInterval(intervalId);
    };
  }, [uploadedDocumentId]);

  function handleFileSelect(file) {
    setSelectedFile(file);
    setUploadResult(null);
    setDocumentStatus(null);
    setUploadError("");
    setAskError("");
    setAnswerResult(null);
  }

  function handleClearFile() {
    setSelectedFile(null);
    setUploadResult(null);
    setDocumentStatus(null);
    setUploadError("");
    setAskError("");
    setAnswerResult(null);
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (isUploading) {
      return;
    }

    setUploadError("");
    setAskError("");
    setAnswerResult(null);

    if (!selectedFile) {
      setUploadError("Upload failed. Please try another PDF.");
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setUploadError("Upload failed. Please try another PDF.");
      return;
    }

    if (selectedFile.size > MAX_UPLOAD_BYTES) {
      setUploadError(
        "This PDF is too large for the deployed app. Please upload a file under 500 MB or split it into smaller PDFs.",
      );
      return;
    }

    try {
      setIsUploading(true);
      const uploadFile = await createFastIndexPdf(selectedFile);
      const result = await uploadPdf(uploadFile);
      setUploadResult(result);
      setDocumentStatus({
        document_id: result.document_id,
        filename: result.filename,
        status: result.status || "processing",
        total_pages: 0,
        processed_pages: 0,
        total_chunks: 0,
        error_message: null,
      });
    } catch (error) {
      setUploadResult(null);
      setUploadError(simplifyError(error, "Upload failed. Please try another PDF."));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();

    if (isAsking) {
      return;
    }

    setAskError("");
    setAnswerResult(null);

    if (!uploadedDocumentId) {
      setAskError("Upload a PDF first.");
      return;
    }

    if (!isDocumentReady) {
      setAskError("Your PDF is being indexed. You can ask questions once it is ready.");
      return;
    }

    if (!question.trim()) {
      setAskError("Could not generate an answer. Please try again.");
      return;
    }

    try {
      setIsAsking(true);
      const result = await askQuestion(question.trim(), uploadedDocumentId, fastMode);
      setAnswerResult(result);
    } catch (error) {
      setAskError(simplifyError(error, "Could not generate an answer. Please try again."));
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <div className="min-h-screen overflow-hidden bg-paper text-charcoal">
      <Navbar />
      <main>
        <HeroSection />
        <StorySection
          stages={storyStages.slice(0, 3)}
          title="Upload, index, and ask with one focused flow."
          text="Upload study PDFs and prepare exam-style questions without leaving the page."
          compact
        />
        <WorkspaceSection
          uploadProps={{
            selectedFile,
            uploadResult,
            documentStatus,
            uploadError,
            isUploading,
            onFileSelect: handleFileSelect,
            onClearFile: handleClearFile,
            onSubmit: handleUpload,
          }}
          questionProps={{
            question,
            documentId: uploadedDocumentId,
            documentStatus,
            askError,
            isAsking,
            fastMode,
            onQuestionChange: setQuestion,
            onFastModeChange: setFastMode,
            onSubmit: handleAsk,
          }}
          answerProps={{
            answer: answerResult?.answer,
            latency: answerResult?.latency,
            isLoading: isAsking,
          }}
          sourcesProps={{
            sources: answerResult?.sources || [],
            retrievedChunks: answerResult?.retrieved_chunks || [],
          }}
        />
        <StorySection
          id="source-flow"
          stages={storyStages.slice(3)}
          kicker="Answer Trace"
          title="Retrieve, answer, and verify the source."
          text="StudyRAG keeps retrieval, answer generation, and page references connected."
          compact
        />
        <FinalSection />
      </main>
    </div>
  );
}

export default App;
