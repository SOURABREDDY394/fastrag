import { useEffect, useId, useState } from "react";

let mermaidConfigured = false;

function MermaidDiagram({ chart }) {
  const reactId = useId();
  const [svg, setSvg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let isActive = true;

    async function renderDiagram() {
      try {
        const { default: mermaid } = await import("mermaid");

        if (!mermaidConfigured) {
          mermaid.initialize({
            startOnLoad: false,
            securityLevel: "strict",
            theme: "base",
            themeVariables: {
              primaryColor: "#ccfbf1",
              primaryTextColor: "#111315",
              primaryBorderColor: "#0f766e",
              lineColor: "#334155",
              secondaryColor: "#f8fafc",
              tertiaryColor: "#ffffff",
              fontFamily: "inherit",
            },
          });
          mermaidConfigured = true;
        }

        const diagramId = `fastrag-diagram-${reactId.replace(/:/g, "")}`;
        const result = await mermaid.render(diagramId, chart.trim());

        if (isActive) {
          setSvg(result.svg);
          setError("");
        }
      } catch (renderError) {
        console.error("Could not render answer diagram:", renderError);
        if (isActive) {
          setSvg("");
          setError("The diagram could not be rendered. The text explanation is still available.");
        }
      }
    }

    renderDiagram();

    return () => {
      isActive = false;
    };
  }, [chart, reactId]);

  if (error) {
    return (
      <div className="my-6 border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        {error}
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-6 border border-charcoal/10 bg-white p-5 text-sm font-bold text-slate-500">
        Rendering diagram...
      </div>
    );
  }

  return (
    <figure className="answer-diagram my-7 overflow-x-auto border border-charcoal/10 bg-white p-4">
      <div dangerouslySetInnerHTML={{ __html: svg }} />
    </figure>
  );
}

export default MermaidDiagram;
