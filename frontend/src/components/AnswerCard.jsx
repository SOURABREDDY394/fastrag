import { BookOpen, Loader2, Timer } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import MermaidDiagram from "./MermaidDiagram";

function formatLatency(latency) {
  if (!latency?.total_ms && latency?.total_ms !== 0) {
    return "";
  }

  return `Answered in ${(latency.total_ms / 1000).toFixed(1)}s`;
}

function AnswerCard({ answer, latency, isLoading }) {
  const latencyText = formatLatency(latency);

  return (
    <section className="app-card max-w-5xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center bg-charcoal text-white">
            <BookOpen size={20} />
          </div>
          <div>
            <p className="eyebrow">Answer Panel</p>
            <h2 className="mt-1 text-3xl font-black text-charcoal">Answer</h2>
          </div>
        </div>

        {latencyText ? (
          <div className="flex items-center gap-2 border border-teal-200 bg-teal-50 px-3 py-1.5 text-sm font-black text-teal-900">
            <Timer size={16} />
            {latencyText}
          </div>
        ) : null}
      </div>

      {isLoading ? (
        <div className="mt-6 flex items-center gap-3 border border-charcoal/10 bg-[#fbfaf7] p-5 text-sm font-black text-slate-700">
          <Loader2 className="animate-spin text-teal-700" size={20} />
          Searching document...
        </div>
      ) : answer ? (
        <article className="answer-content mt-6 border border-charcoal/10 bg-[#fbfaf7] p-5 sm:p-7">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              pre({ children }) {
                return children;
              },
              code({ className, children, ...props }) {
                const language = /language-(\w+)/.exec(className || "")?.[1];
                const content = String(children).replace(/\n$/, "");

                if (language === "mermaid") {
                  return <MermaidDiagram chart={content} />;
                }

                if (className) {
                  return (
                    <pre>
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                }

                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {answer}
          </ReactMarkdown>
        </article>
      ) : (
        <div className="mt-6 flex flex-col items-center justify-center border border-dashed border-charcoal/20 bg-[#fbfaf7] px-5 py-10 text-center">
          <div className="flex h-16 w-16 items-center justify-center bg-white text-teal-700 shadow-[6px_6px_0_#111315] ring-1 ring-charcoal/10">
            <BookOpen size={32} strokeWidth={1.8} />
          </div>
          <p className="mt-4 max-w-md text-sm leading-6 text-slate-600">
            Your exam-ready answer will appear here.
          </p>
        </div>
      )}
    </section>
  );
}

export default AnswerCard;
