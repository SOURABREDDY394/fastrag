import { FileText } from "lucide-react";

function formatSimilarity(value) {
  if (typeof value !== "number") {
    return "N/A";
  }

  return `${Math.round(value * 100)}% similarity`;
}

function previewText(text) {
  if (!text) {
    return "No chunk preview returned.";
  }

  if (text.length <= 250) {
    return text;
  }

  return `${text.slice(0, 250).trim()}...`;
}

function getChunkForSource(source, retrievedChunks) {
  return retrievedChunks.find(
    (chunk) =>
      chunk.document_id === source.document_id &&
      chunk.page_number === source.page_number &&
      chunk.chunk_index === source.chunk_index,
  );
}

function SourcesCard({ sources, retrievedChunks }) {
  if (sources.length === 0) {
    return (
      <section className="app-card ml-auto max-w-6xl">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center bg-teal-700 text-white">
            <FileText size={20} />
          </div>
          <div>
            <p className="eyebrow">Evidence</p>
            <h2 className="mt-1 text-3xl font-black text-charcoal">Sources Used</h2>
          </div>
        </div>

        <div className="mt-6 border border-dashed border-charcoal/20 bg-[#fbfaf7] px-5 py-10 text-center">
          <p className="text-sm leading-6 text-slate-600">
            Page references will appear after an answer is generated.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="app-card ml-auto max-w-6xl">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center bg-teal-700 text-white">
          <FileText size={20} />
        </div>
        <div>
          <p className="eyebrow">Evidence</p>
          <h2 className="mt-1 text-3xl font-black text-charcoal">Sources Used</h2>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sources.map((source, index) => {
          const chunk = getChunkForSource(source, retrievedChunks);

          return (
            <article
              key={`${source.document_id}-${source.page_number}-${source.chunk_index}-${index}`}
              className="border border-charcoal/10 bg-[#fbfaf7] p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="bg-charcoal px-3 py-1 text-sm font-black text-white">
                  Page {source.page_number ?? "N/A"}
                </span>
                <span className="text-sm font-bold text-slate-600">
                  Chunk {source.chunk_index ?? "N/A"}
                </span>
                <span className="text-sm font-black text-teal-700">
                  {formatSimilarity(source.similarity)}
                </span>
              </div>

              <p className="mt-4 text-sm leading-6 text-slate-700">
                {previewText(chunk?.chunk_text)}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default SourcesCard;
