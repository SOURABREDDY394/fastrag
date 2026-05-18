import { HelpCircle, Info, MessageCircle, Zap } from "lucide-react";

const MAX_QUESTION_LENGTH = 1000;
const suggestions = [
  "What is this document about?",
  "Explain key points",
  "Summarize this PDF",
  "Give exam notes",
];

function QuestionCard({
  question,
  documentId,
  documentStatus,
  askError,
  isAsking,
  fastMode,
  onQuestionChange,
  onFastModeChange,
  onSubmit,
}) {
  const isReady = documentStatus?.status === "ready";
  const hasIndexedChunks = (documentStatus?.total_chunks || 0) > 0;
  const isFailed = documentStatus?.status === "failed";
  const isAskDisabled = !documentId || (!isReady && !hasIndexedChunks) || !question.trim() || isAsking;

  function handleQuestionChange(value) {
    onQuestionChange(value.slice(0, MAX_QUESTION_LENGTH));
  }

  return (
    <form id="question-panel" onSubmit={onSubmit} className="app-card xl:translate-y-12">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Question Panel</p>
          <h2 className="mt-3 text-3xl font-black text-charcoal">Ask a Question</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-slate-600">
            Ask anything from the uploaded document.
          </p>
        </div>
        <div className="flex h-12 w-12 shrink-0 items-center justify-center bg-teal-700 text-white">
          <HelpCircle size={22} />
        </div>
      </div>

      <label className="mt-6 block">
        <span className="sr-only">Question</span>
        <textarea
          value={question}
          onChange={(event) => handleQuestionChange(event.target.value)}
          rows={10}
          maxLength={MAX_QUESTION_LENGTH}
          placeholder={`Examples:\n- Explain deadlock prevention in simple points\n- Summarize paging in operating systems`}
          className="block min-h-64 w-full resize-y border border-charcoal/15 bg-[#fbfaf7] px-4 py-4 text-sm leading-7 text-charcoal shadow-inner outline-none transition placeholder:text-slate-400 focus:border-teal-700 focus:ring-4 focus:ring-teal-600/15"
        />
      </label>

      <div className="mt-2 flex justify-end text-xs font-semibold text-slate-500">
        {question.length} / {MAX_QUESTION_LENGTH}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => handleQuestionChange(suggestion)}
            className="border border-charcoal/15 bg-white px-3 py-1.5 text-xs font-black text-charcoal transition hover:border-teal-700 hover:bg-teal-50 hover:text-teal-900"
          >
            {suggestion}
          </button>
        ))}
      </div>

      <div className="mt-4 flex gap-3 border border-sky-100 bg-sky-50 px-4 py-3">
        <Info className="mt-0.5 shrink-0 text-teal-800" size={18} />
        <p className="text-sm leading-6 text-slate-700">
          {!documentId
            ? "Upload a PDF first to start asking questions."
            : isReady
              ? "Ready to answer questions from your uploaded PDF."
              : hasIndexedChunks
                ? "Document is still indexing. Answers may improve after full indexing completes."
              : isFailed
                ? "PDF processing failed. Upload another PDF to ask questions."
                : "Your PDF is being indexed. You can ask questions once it is ready."}
        </p>
      </div>

      <label className="mt-4 flex cursor-pointer items-center justify-between gap-4 border border-charcoal bg-charcoal px-4 py-3 text-white">
        <div>
          <p className="flex items-center gap-2 text-sm font-black">
            <Zap size={16} className="text-teal-200" />
            Fast Mode
          </p>
          <p className="mt-0.5 text-xs leading-5 text-white/60">
            Search fewer chunks for faster answers.
          </p>
        </div>
        <input
          type="checkbox"
          checked={fastMode}
          onChange={(event) => onFastModeChange(event.target.checked)}
          className="h-5 w-5 rounded-none border-white/40 bg-white/10 text-teal-300 focus:ring-teal-300"
        />
      </label>

      {askError && (
        <div className="mt-4 break-words border border-red-200 bg-red-50 px-4 py-3 text-sm leading-6 text-red-700">
          {askError}
        </div>
      )}

      <button
        type="submit"
        disabled={isAskDisabled}
        className="mt-5 flex w-full items-center justify-center gap-2 bg-teal-700 px-4 py-3 text-sm font-black text-white transition hover:bg-charcoal disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        <MessageCircle size={18} />
        {isAsking ? "Searching document..." : "Ask Question"}
      </button>
    </form>
  );
}

export default QuestionCard;
