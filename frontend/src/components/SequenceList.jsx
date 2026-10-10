import React from "react";

export default function SequenceList({ sequence }) {
  if (!sequence || sequence.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border-[3px] border-bauhaus-black p-5 shadow-bauhaus mt-6 relative">
      <div className="absolute -top-3 -left-3 bg-bauhaus-black text-white text-[10px] font-black px-1.5 py-0.5 font-mono">04</div>
      <h2 className="text-sm font-black uppercase font-bauhaus tracking-wider text-bauhaus-black mb-3 border-b-[3px] border-bauhaus-black pb-2">
        Recommended Study Sequence
      </h2>
      <ol className="space-y-3 space-y-2 text-xs text-bauhaus-black font-bold">
        {sequence.map((node, index) => (
          <li key={node.id} className="p-2 flex items-center gap-2 border-2 border-bauhaus-black bg-bauhaus-cream shadow-bauhaus">
            <span className={`w-3 h-3 shrink-0 border-2 border-bauhaus-black flex items-center justify-center font-mono text-[8px] font-black ${
              index % 3 === 0 ? "bg-bauhaus-red text-white" : 
              index % 3 === 1 ? "bg-bauhaus-blue text-white" : 
              "bg-bauhaus-yellow text-bauhaus-black"
            }`}>{index + 1}</span>
            {node.name} <span className="text-bauhaus-blue font-mono">({node.unit})</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
