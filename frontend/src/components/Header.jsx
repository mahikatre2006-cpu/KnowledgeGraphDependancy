import React from "react";
import { Sparkles, RefreshCw } from "lucide-react";

export default function Header({ onInferRelationships, inferring, nodeCount, edgeCount, courseTitle }) {
  return (
    <header className="w-full bg-white border-b border-neutral-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-bold tracking-tight text-neutral-900">
            Knowledge Dependency Graph
          </h1>
          {courseTitle && (
            <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-neutral-100 text-neutral-700 border border-neutral-200">
              {courseTitle}
            </span>
          )}
        </div>
        <p className="text-xs text-neutral-500 mt-0.5">
          Curriculum dependency analysis, bottleneck detection, and prerequisite engine
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 text-xs font-mono text-neutral-600 bg-neutral-50 px-3 py-1.5 rounded border border-neutral-200">
          <div>
            <span className="text-neutral-400">Nodes:</span>{" "}
            <span className="font-semibold text-neutral-900">{nodeCount}</span>
          </div>
          <span className="text-neutral-300">|</span>
          <div>
            <span className="text-neutral-400">Edges:</span>{" "}
            <span className="font-semibold text-neutral-900">{edgeCount}</span>
          </div>
        </div>

        <button
          onClick={onInferRelationships}
          disabled={inferring || nodeCount === 0}
          className="flex items-center gap-2 text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed px-3.5 py-2 rounded transition-colors shadow-sm"
        >
          {inferring ? (
            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Sparkles className="w-3.5 h-3.5" />
          )}
          <span>Infer Relationships</span>
        </button>
      </div>
    </header>
  );
}
