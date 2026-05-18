import { CheckCircle2, Clipboard, CloudUpload, FileText, Upload, X } from "lucide-react";
import { useState } from "react";

function formatFileSize(size) {
  if (!size) {
    return "";
  }

  const megabytes = size / (1024 * 1024);
  return `${megabytes.toFixed(2)} MB`;
}

function UploadCard({
  selectedFile,
  uploadResult,
  documentStatus,
  uploadError,
  isUploading,
  onFileSelect,
  onClearFile,
  onSubmit,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [copied, setCopied] = useState(false);
  const status = documentStatus?.status || uploadResult?.status;
  const isProcessing = status === "uploaded" || status === "processing";
  const isReady = status === "ready";
  const isFailed = status === "failed";
  const processedPages = documentStatus?.processed_pages || 0;
  const totalPages = documentStatus?.total_pages || 0;
  const progressPercent =
    totalPages > 0 ? Math.round((processedPages / totalPages) * 100) : 0;

  function handleDrop(event) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files?.[0];
    if (file) {
      onFileSelect(file);
    }
  }

  async function copyDocumentId() {
    if (!uploadResult?.document_id) {
      return;
    }

    try {
      await navigator.clipboard.writeText(uploadResult.document_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error("Could not copy document ID:", error);
    }
  }

  return (
    <form onSubmit={onSubmit} className="app-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Upload Panel</p>
          <h2 className="mt-3 text-3xl font-black text-charcoal">Upload PDF</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
            Add one study PDF and prepare it for grounded questions.
          </p>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-charcoal text-white">
          <Upload size={22} />
        </div>
      </div>

      <label
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`mt-6 flex cursor-pointer flex-col items-center justify-center border border-dashed px-5 py-10 text-center transition ${
          isDragging
            ? "border-teal-700 bg-teal-50"
            : "border-charcoal/25 bg-[#fbfaf7] hover:border-teal-700 hover:bg-teal-50"
        }`}
      >
        <input
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => onFileSelect(event.target.files?.[0] || null)}
          className="sr-only"
        />
        <CloudUpload className="text-teal-700" size={44} strokeWidth={1.8} />
        <span className="mt-4 text-sm font-black text-charcoal">
          Drop your PDF here or click to browse
        </span>
        <span className="mt-1 text-xs font-semibold text-slate-500">PDF files only</span>
      </label>

      {selectedFile && (
        <div className="mt-4 flex items-center gap-3 border border-charcoal/10 bg-white px-4 py-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center bg-red-50 text-red-700">
            <FileText size={22} />
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-black text-charcoal">{selectedFile.name}</p>
            {selectedFile.size ? (
              <p className="mt-0.5 text-xs text-slate-500">{formatFileSize(selectedFile.size)}</p>
            ) : null}
          </div>
          <button
            type="button"
            aria-label="Remove selected file"
            onClick={onClearFile}
            disabled={isUploading}
            className="flex h-9 w-9 shrink-0 items-center justify-center text-slate-500 transition hover:bg-slate-100 hover:text-charcoal disabled:cursor-not-allowed disabled:opacity-50"
          >
            <X size={18} />
          </button>
        </div>
      )}

      {uploadError && (
        <div className="mt-4 break-words border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
          {uploadError}
        </div>
      )}

      {isReady && (
        <section className="mt-4 border border-emerald-200 bg-emerald-50 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={22} />
            <div>
              <h3 className="text-sm font-black text-emerald-950">Document Ready</h3>
              <p className="mt-1 text-sm leading-6 text-emerald-800">
                Your document has been processed and is ready for questions.
              </p>
            </div>
          </div>

          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="bg-white p-3 ring-1 ring-emerald-100">
              <dt className="eyebrow text-slate-500">File Name</dt>
              <dd className="mt-1 break-words text-sm font-bold text-charcoal">{uploadResult.filename}</dd>
            </div>
            <div className="bg-white p-3 ring-1 ring-emerald-100">
              <div className="flex items-center justify-between gap-2">
                <dt className="eyebrow text-slate-500">Document ID</dt>
                <button
                  type="button"
                  onClick={copyDocumentId}
                  className="p-1 text-slate-500 transition hover:bg-slate-100 hover:text-teal-700"
                  aria-label="Copy document ID"
                >
                  <Clipboard size={15} />
                </button>
              </div>
              <dd className="mt-1 break-all font-mono text-xs font-bold text-charcoal">
                {copied ? "Copied" : uploadResult.document_id}
              </dd>
            </div>
            <div className="bg-white p-3 ring-1 ring-emerald-100">
              <dt className="eyebrow text-slate-500">Total Pages</dt>
              <dd className="mt-1 text-lg font-black text-charcoal">{documentStatus?.total_pages || 0}</dd>
            </div>
            <div className="bg-white p-3 ring-1 ring-emerald-100">
              <dt className="eyebrow text-slate-500">Total Chunks</dt>
              <dd className="mt-1 text-lg font-black text-charcoal">{documentStatus?.total_chunks || 0}</dd>
            </div>
          </dl>
        </section>
      )}

      {uploadResult && isProcessing && (
        <section className="mt-4 border border-sky-200 bg-sky-50 p-4">
          <h3 className="text-sm font-black text-sky-950">Document uploaded. Indexing started.</h3>
          <p className="mt-1 text-sm leading-6 text-sky-800">
            Your PDF is being indexed. Huge PDFs are uploaded as a tiny fast preview first.
          </p>

          <div className="mt-4">
            <div className="flex justify-between text-xs font-bold text-sky-900">
              <span>
                {totalPages > 0 ? `${processedPages} / ${totalPages} pages` : "Preparing document..."}
              </span>
              <span>{totalPages > 0 ? `${progressPercent}%` : status}</span>
            </div>
            <div className="mt-2 h-2 overflow-hidden bg-white">
              <div
                className="h-full bg-teal-600 transition-all"
                style={{ width: `${totalPages > 0 ? progressPercent : 12}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-sky-800">
              Total chunks indexed: {documentStatus?.total_chunks || 0}
            </p>
          </div>
        </section>
      )}

      {isFailed && (
        <section className="mt-4 border border-red-200 bg-red-50 p-4">
          <h3 className="text-sm font-black text-red-900">Processing failed</h3>
          <p className="mt-1 break-words text-sm leading-6 text-red-700">
            {documentStatus?.error_message || "Document processing failed."}
          </p>
        </section>
      )}

      <button
        type="submit"
        disabled={isUploading || isProcessing || !selectedFile}
        className="mt-5 flex w-full items-center justify-center gap-2 bg-charcoal px-4 py-3 text-sm font-black text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        <Upload size={18} />
        {isUploading ? "Processing PDF..." : "Upload PDF"}
      </button>
      <p className="mt-3 text-center text-xs text-slate-500">
        Huge PDFs are converted to a tiny fast preview before upload.
      </p>
    </form>
  );
}

export default UploadCard;
