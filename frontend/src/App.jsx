import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import FileUpload from "./components/FileUpload";
import GraphCanvas from "./components/GraphCanvas";
import AnalyticsPanel from "./components/AnalyticsPanel";
import SequenceList from "./components/SequenceList";
import thresholdConfig from "../../app/ml/decision_threshold.json";
import {
  getGraphSummary,
  inferRelationships,
  getMissingPrerequisites,
  getBottlenecks,
  getRecommendations,
  getTopologicalSequence,
} from "./services/api";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [knownConceptIds, setKnownConceptIds] = useState([]);
  const [targetConceptId, setTargetConceptId] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [missingPrereqs, setMissingPrereqs] = useState(null);
  const [bottlenecks, setBottlenecks] = useState(null);
  const [sequence, setSequence] = useState(null);
  const [inferring, setInferring] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  // Load the optimal ML threshold from public folder (safe Vite-compatible approach)
  const [mlThreshold, setMlThreshold] = useState(0.20);

  useEffect(() => {
    fetch("/decision_threshold.json")
      .then((r) => r.json())
      .then((cfg) => setMlThreshold(cfg.optimal_threshold ?? 0.20))
      .catch(() => setMlThreshold(0.20));
  }, []);

  const refreshData = async () => {
    try {
      const summaryData = await getGraphSummary();
      setSummary(summaryData);

      if (summaryData.nodes && summaryData.nodes.length > 0) {
        const [recs, bts, seq] = await Promise.all([
          getRecommendations(knownConceptIds, targetConceptId),
          getBottlenecks(10),
          getTopologicalSequence(),
        ]);
        setRecommendations(recs);
        setBottlenecks(bts);
        setSequence(seq.topological_sequence || []);

        if (targetConceptId) {
          const miss = await getMissingPrerequisites(targetConceptId, knownConceptIds);
          setMissingPrereqs(miss);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    refreshData();
  }, [knownConceptIds, targetConceptId]);

  // BUG FIX: buildAndInfer already returns FullPipelineResponse with graph_summary + topological_sequence.
  // We use it directly to avoid a redundant GET /graph/summary round-trip that races with in-memory state.
  const handlePipelineComplete = (data) => {
    setErrorMessage("");
    if (data && data.graph_summary) {
      setSummary(data.graph_summary);
    }
    if (data && data.topological_sequence) {
      setSequence(data.topological_sequence);
    }
    // Kick off analytics refresh in background (non-blocking)
    refreshData();
  };

  const handleInferRelationships = async () => {
    setInferring(true);
    setErrorMessage("");
    try {
      console.log("Using dynamic threshold:", thresholdConfig.optimal_threshold);
      await inferRelationships(0.0, thresholdConfig.optimal_threshold);
      console.log("Using dynamic ML threshold:", mlThreshold);
      await inferRelationships(0.0, mlThreshold);
      await refreshData();
    } catch (err) {
      setErrorMessage(err.message || "Failed to run AI inference.");
    } finally {
      setInferring(false);
    }
  };

  const handleToggleMastery = (conceptId) => {
    setKnownConceptIds((prev) =>
      prev.includes(conceptId) ? prev.filter((id) => id !== conceptId) : [...prev, conceptId]
    );
  };

  const handleSelectTarget = (conceptId) => {
    setTargetConceptId((prev) => (prev === conceptId ? null : conceptId));
  };

  return (
    <div className="min-h-screen bg-bauhaus-bg text-bauhaus-black font-sans flex flex-col antialiased selection:bg-bauhaus-red selection:text-white">
      <Header
        onInferRelationships={handleInferRelationships}
        inferring={inferring}
        nodeCount={summary?.node_count || 0}
        edgeCount={summary?.edge_count || 0}
        courseTitle={summary?.nodes?.[0]?.metadata?.course_title || ""}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {errorMessage && (
          <div className="p-3.5 border-[3px] border-bauhaus-black bg-bauhaus-black text-white text-xs flex items-center justify-between shadow-bauhaus">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage("")}
              className="text-bauhaus-yellow hover:text-white text-xs font-mono font-bold uppercase"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Top Control Section: File Upload & Instructions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          <div className="lg:col-span-1">
            <FileUpload
              onPipelineComplete={handlePipelineComplete}
              onError={(msg) => setErrorMessage(msg)}
            />
          </div>

          <div className="lg:col-span-2 bg-white border-[3px] border-bauhaus-black p-5 shadow-bauhaus space-y-3 relative">
            <div className="absolute -top-3 -left-3 bg-bauhaus-black text-white text-[10px] font-black px-1.5 py-0.5 font-mono">02</div>
            <h2 className="text-sm font-black uppercase font-bauhaus tracking-wider text-bauhaus-black border-b-[3px] border-bauhaus-black pb-2 mb-2">
              Interactive Concept Graph Navigator
            </h2>
            <p className="text-xs text-bauhaus-black font-bold leading-relaxed font-mono">
              Click <span className="font-black text-bauhaus-blue font-mono bg-bauhaus-cream px-1 border border-bauhaus-black">Mark Mastered</span> on any topic node to record your progress. Click <span className="font-black text-bauhaus-blue font-mono bg-bauhaus-cream px-1 border border-bauhaus-black">Set Target Goal</span> to calculate exact missing prerequisites. Click <span className="font-black text-bauhaus-blue font-mono bg-bauhaus-cream px-1 border border-bauhaus-black">Infer Relationships</span> above to trigger open-source AI prerequisite inference.
            </p>

            <GraphCanvas
              summary={summary}
              knownConceptIds={knownConceptIds}
              targetConceptId={targetConceptId}
              onToggleMastery={handleToggleMastery}
              onSelectTarget={handleSelectTarget}
            />
          </div>
        </div>

        {/* Bottom Section: Analytics & Recommendations Panel */}
        <SequenceList sequence={sequence} />

        <AnalyticsPanel
          recommendations={recommendations}
          missingPrereqs={missingPrereqs}
          bottlenecks={bottlenecks}
          nodes={summary?.nodes || []}
          targetConceptId={targetConceptId}
          onSelectTarget={handleSelectTarget}
          onToggleMastery={handleToggleMastery}
        />
      </main>

      <footer className="w-full border-t-[3px] border-bauhaus-black bg-bauhaus-cream py-4 px-6 text-center text-xs text-bauhaus-black font-mono font-bold uppercase tracking-widest">
        Knowledge Dependency Graph V1 &bull; Powered by FastAPI & React Flow
      </footer>
    </div>
  );
}
