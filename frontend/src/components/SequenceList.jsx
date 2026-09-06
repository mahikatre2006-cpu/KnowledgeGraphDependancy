import React from "react";

export default function SequenceList({ sequence }) {
  if (!sequence || sequence.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm mt-6">
      <h2 className="text-sm font-semibold text-neutral-900 mb-3">
        Recommended Study Sequence
      </h2>
      <ol className="list-decimal list-inside space-y-2 text-xs text-neutral-700">
        {sequence.map((node, index) => (
          <li key={node.id} className="p-2 border border-neutral-100 rounded bg-neutral-50">
            {node.name} <span className="text-neutral-400">({node.unit})</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
