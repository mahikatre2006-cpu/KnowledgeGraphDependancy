import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import FileUpload from "./components/FileUpload";
import GraphCanvas from "./components/GraphCanvas";
import AnalyticsPanel from "./components/AnalyticsPanel";
import {
  getGraphSummary,
  inferRelationships,
  getMissingPrerequisites,
  getBottlenecks,
  getRecommendations,
} from "./services/api";

export default function App() {
  const [summary, setSummary] = useState(null);
  const [knownConceptIds, setKnownConceptIds] = useState([]);
  const [targetConceptId, setTargetConceptId] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [missingPrereqs, setMissingPrereqs] = useState(null);
  const [bottlenecks, setBottlenecks] = useState(null);
  const [inferring, setInferring] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const refreshData = async () => {
    try {
      const summaryData = await getGraphSummary();
      setSummary(summaryData);

      if (summaryData.nodes && summaryData.nodes.length > 0) {
        const [recs, bts] = await Promise.all([
          getRecommendations(knownConceptIds, targetConceptId),
          getBottlenecks(10),
        ]);
        setRecommendations(recs);
        setBottlenecks(bts);

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

  const handlePipelineComplete = (data) => {
    setErrorMessage("");
    refreshData();
  };

  const handleInferRelationships = async () => {
    setInferring(true);
    setErrorMessage("");
    try {
      await inferRelationships(0.25, 0.45);
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
    <div className="min-h-screen bg-neutral-100 text-neutral-900 font-sans flex flex-col antialiased selection:bg-neutral-900 selection:text-white">
      <Header
        onInferRelationships={handleInferRelationships}
        inferring={inferring}
        nodeCount={summary?.node_count || 0}
        edgeCount={summary?.edge_count || 0}
        courseTitle={summary?.nodes?.[0]?.metadata?.course_title || ""}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {errorMessage && (
          <div className="p-3.5 rounded-lg border border-neutral-300 bg-neutral-900 text-white text-xs flex items-center justify-between shadow-xs">
            <span>{errorMessage}</span>
            <button
              onClick={() => setErrorMessage("")}
              className="text-neutral-400 hover:text-white text-xs font-mono"
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

          <div className="lg:col-span-2 bg-white border border-neutral-200 rounded-lg p-5 shadow-sm space-y-3">
            <h2 className="text-sm font-semibold text-neutral-900">
              Interactive Concept Graph Navigator
            </h2>
            <p className="text-xs text-neutral-500 leading-relaxed">
              Click <span className="font-semibold text-neutral-900 font-mono">Mark Mastered</span> on any topic node to record your progress. Click <span className="font-semibold text-neutral-900 font-mono">Set Target Goal</span> to calculate exact missing prerequisites. Click <span className="font-semibold text-neutral-900 font-mono">Infer Relationships</span> above to trigger open-source AI prerequisite inference.
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

      <footer className="w-full border-t border-neutral-200 bg-white py-4 px-6 text-center text-xs text-neutral-400 font-mono">
        Knowledge Dependency Graph V1 &bull; Powered by FastAPI & React Flow
      </footer>
    </div>
  );
}
