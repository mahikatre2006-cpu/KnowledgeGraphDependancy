import React, { useState } from "react";

export default function AnalyticsPanel({
  recommendations,
  missingPrereqs,
  bottlenecks,
  nodes,
  targetConceptId,
  onSelectTarget,
  onToggleMastery,
}) {
  const [activeTab, setActiveTab] = useState("recommendations"); // 'recommendations' | 'missing' | 'bottlenecks'

  return (
    <div className="bg-white border-[3px] border-bauhaus-black p-5 shadow-bauhaus relative mt-4">
      <div className="absolute -top-3 -left-3 bg-bauhaus-black text-white text-[10px] font-black px-1.5 py-0.5 font-mono">03</div>
      {/* Navigation Tabs */}
      <div className="flex items-center justify-between border-b-[3px] border-bauhaus-black pb-3 mb-4">
        <div className="flex items-center bg-bauhaus-cream border-2 border-bauhaus-black text-xs font-mono font-bold">
          <button
            onClick={() => setActiveTab("recommendations")}
            className={`px-3 py-1.5  font-medium transition-colors cursor-pointer ${
              activeTab === "recommendations"
                ? "bg-white text-neutral-900 "
                : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Recommended Path
          </button>
          <button
            onClick={() => setActiveTab("missing")}
            className={`px-3 py-1.5  font-medium transition-colors cursor-pointer ${
              activeTab === "missing"
                ? "bg-white text-neutral-900 "
                : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Missing Prerequisites
          </button>
          <button
            onClick={() => setActiveTab("bottlenecks")}
            className={`px-3 py-1.5  font-medium transition-colors cursor-pointer ${
              activeTab === "bottlenecks"
                ? "bg-white text-neutral-900 "
                : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Curriculum Bottlenecks
          </button>
        </div>

        {recommendations && (
          <div className="hidden sm:flex items-center gap-2 text-xs text-bauhaus-black font-bold uppercase font-bauhaus tracking-wider">
            <span>Curriculum Mastery:</span>
            <span className="font-mono font-black text-bauhaus-red bg-bauhaus-cream px-1 border border-bauhaus-black">
              {recommendations.student_mastery_percentage}%
            </span>
          </div>
        )}
      </div>

      {/* Tab 1: Recommendations */}
      {activeTab === "recommendations" && (
        <div className="space-y-3">
          <p className="text-xs text-bauhaus-black font-bold font-mono mb-2">
            Dynamic study recommendations prioritized by prerequisite readiness and unlock impact.
          </p>

          {recommendations?.recommended_path?.length > 0 ? (
            <div className="space-y-2">
              {recommendations.recommended_path.map((item) => (
                <div
                  key={item.concept.id}
                  className="p-3.5 border-[3px] border-bauhaus-black bg-white hover:bg-bauhaus-yellow transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-bauhaus"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-mono uppercase tracking-wider font-black px-2 py-0.5 bg-bauhaus-black text-white">
                        {item.status}
                      </span>
                      <h4 className="text-xs font-black uppercase font-bauhaus text-bauhaus-black tracking-wider">
                        {item.concept.name}
                      </h4>
                      <span className="text-[10px] text-neutral-400 font-mono">
                        ({item.concept.unit || "Unit 1"})
                      </span>
                    </div>
                    <p className="text-[11px] text-neutral-600">
                      {item.recommendation_reason}
                    </p>
                  </div>

                  <button
                    onClick={() => onToggleMastery(item.concept.id)}
                    className="self-start sm:self-auto text-xs font-medium px-3 py-1.5  bg-white border border-neutral-300 hover:border-neutral-900 text-neutral-900 transition-colors  cursor-pointer"
                  >
                    Mark Mastered
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-neutral-400 bg-neutral-50  border border-dashed border-neutral-200">
              All topics in current view are mastered or blocked. Select a target goal or upload a syllabus.
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Missing Prerequisites */}
      {activeTab === "missing" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-neutral-50 p-3  border border-neutral-200">
            <label className="text-xs font-bold text-bauhaus-black">
              Select Target Topic:
            </label>
            <select
              value={targetConceptId || ""}
              onChange={(e) => onSelectTarget(e.target.value)}
              className="text-xs font-medium p-1.5  border border-neutral-300 bg-white text-neutral-900 focus:outline-none"
            >
              <option value="">-- Choose Target Concept --</option>
              {nodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} ({n.unit || "General"})
                </option>
              ))}
            </select>
          </div>

          {missingPrereqs ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="text-neutral-600">Target Readiness Progress:</span>
                <span className="font-mono font-black text-bauhaus-red bg-bauhaus-cream px-1 border border-bauhaus-black">
                  {missingPrereqs.progress_percentage}%
                </span>
              </div>
              <div className="w-full bg-neutral-100 h-2  overflow-hidden">
                <div
                  className="bg-neutral-900 h-full transition-all duration-300"
                  style={{ width: `${missingPrereqs.progress_percentage}%` }}
                />
              </div>

              {missingPrereqs.missing_concepts.length > 0 ? (
                <div>
                  <h4 className="text-xs font-semibold text-neutral-800 mb-2">
                    Prerequisites To Study Before '{missingPrereqs.target_concept_name}':
                  </h4>
                  <div className="space-y-1.5">
                    {missingPrereqs.missing_concepts.map((m) => (
                      <div
                        key={m.id}
                        className="p-2.5  border border-neutral-200 bg-white flex items-center justify-between text-xs"
                      >
                        <span className="font-medium text-neutral-900">{m.name}</span>
                        <button
                          onClick={() => onToggleMastery(m.id)}
                          className="text-[11px] font-medium text-neutral-700 hover:text-neutral-900 underline cursor-pointer"
                        >
                          Mark Learned
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-bauhaus-black font-bold uppercase font-bauhaus tracking-wider p-3 bg-neutral-50  border border-neutral-200">
                  You have satisfied all prerequisites required for '{missingPrereqs.target_concept_name}'!
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-neutral-400 text-center py-6">
              Select a target concept above to analyze missing prerequisite dependencies.
            </p>
          )}
        </div>
      )}

      {/* Tab 3: Bottlenecks */}
      {activeTab === "bottlenecks" && (
        <div className="space-y-3">
          <p className="text-xs text-bauhaus-black font-bold font-mono mb-2">
            Curriculum bottleneck concepts that unlock the largest downstream portion of the course.
          </p>

          {bottlenecks?.bottlenecks?.length > 0 ? (
            <div className="space-y-2">
              {bottlenecks.bottlenecks.map((item, idx) => (
                <div
                  key={item.concept.id}
                  className="p-3  border border-neutral-200 bg-neutral-50 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-bold text-neutral-400 w-5">
                      #{idx + 1}
                    </span>
                    <div>
                      <h4 className="font-semibold text-neutral-900">
                        {item.concept.name}
                      </h4>
                      <p className="text-[11px] text-neutral-500">
                        {item.description}
                      </p>
                    </div>
                  </div>

                  <div className="text-right font-mono">
                    <span className="text-xs font-bold text-neutral-900">
                      {item.downstream_count}
                    </span>
                    <span className="text-[10px] text-neutral-400 block">unlocked</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-neutral-400 text-center py-6">
              No bottleneck analysis available. Load a syllabus graph first.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
