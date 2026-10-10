import React from "react";
import { Sparkles, RefreshCw } from "lucide-react";

export default function Header({ onInferRelationships, inferring, nodeCount, edgeCount, courseTitle }) {
  return (
    <header className="w-full bg-white border-b-[3px] border-bauhaus-black px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-black tracking-tight text-bauhaus-black uppercase font-bauhaus">
            Knowledge Dependency Graph
          </h1>
          {courseTitle && (
            <span className="text-[10px] font-black px-2 py-0.5 bg-bauhaus-yellow text-bauhaus-black border-2 border-bauhaus-black uppercase font-mono">
              {courseTitle}
            </span>
          )}
        </div>
        <p className="text-xs font-bold text-bauhaus-blue mt-0.5 uppercase font-bauhaus">
          Curriculum dependency analysis, bottleneck detection, and prerequisite engine
        </p>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3 text-xs font-mono font-bold text-bauhaus-black bg-bauhaus-cream px-3 py-1.5 border-2 border-bauhaus-black ">
          <div>
            <span className="text-bauhaus-black">Nodes:</span>{" "}
            <span className="font-black text-bauhaus-red">{nodeCount}</span>
          </div>
          <span className="text-bauhaus-black font-black">|</span>
          <div>
            <span className="text-bauhaus-black">Edges:</span>{" "}
            <span className="font-black text-bauhaus-red">{edgeCount}</span>
          </div>
        </div>

        <button
          onClick={onInferRelationships}
          disabled={inferring || nodeCount === 0}
          className="flex items-center gap-2 text-[11px] font-black uppercase tracking-wider font-bauhaus text-white bg-bauhaus-blue hover:bg-bauhaus-blue/90 disabled:opacity-50 disabled:cursor-not-allowed px-3.5 py-2 border-2 border-bauhaus-black transition-colors "
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
