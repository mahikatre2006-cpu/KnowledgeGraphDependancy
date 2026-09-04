import React, { useMemo } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

function ConceptNodeCard({ data }) {
  const { node, isKnown, isTarget, onToggleMastery, onSelectTarget } = data;

  return (
    <div
      className={`px-4 py-3 rounded-md border text-left min-w-[200px] shadow-2xs transition-all ${
        isTarget
          ? "border-neutral-900 bg-neutral-900 text-white ring-2 ring-neutral-400"
          : isKnown
          ? "border-neutral-300 bg-neutral-100 text-neutral-900"
          : "border-neutral-200 bg-white text-neutral-900 hover:border-neutral-400"
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span
          className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${
            isTarget
              ? "bg-neutral-800 text-neutral-300"
              : "bg-neutral-100 text-neutral-600 border border-neutral-200"
          }`}
        >
          {node.unit || "General"}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleMastery(node.id);
          }}
          className={`text-[10px] font-medium px-2 py-0.5 rounded cursor-pointer transition-colors ${
            isKnown
              ? "bg-neutral-900 text-white hover:bg-neutral-800"
              : isTarget
              ? "bg-white text-neutral-900 hover:bg-neutral-100"
              : "bg-neutral-100 text-neutral-700 border border-neutral-300 hover:bg-neutral-200"
          }`}
        >
          {isKnown ? "Mastered" : "Mark Mastered"}
        </button>
      </div>

      <h3 className="text-xs font-semibold leading-snug">{node.name}</h3>

      <div className="mt-2 pt-2 border-t border-neutral-100/50 flex items-center justify-between text-[10px] text-neutral-500">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectTarget(node.id);
          }}
          className={`hover:underline cursor-pointer ${
            isTarget ? "text-neutral-300" : "text-neutral-700"
          }`}
        >
          {isTarget ? "Selected Target" : "Set Target Goal"}
        </button>
      </div>
    </div>
  );
}

const nodeTypes = { conceptNode: ConceptNodeCard };

export default function GraphCanvas({
  summary,
  knownConceptIds,
  targetConceptId,
  onToggleMastery,
  onSelectTarget,
}) {
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!summary || !summary.nodes) return { initialNodes: [], initialEdges: [] };

    const nodesList = summary.nodes;
    const edgesList = summary.edges || [];

    // Group nodes by unit number for horizontal/vertical grid layout
    const unitGroups = {};
    nodesList.forEach((n) => {
      const u = n.unit || "General";
      if (!unitGroups[u]) unitGroups[u] = [];
      unitGroups[u].push(n);
    });

    const unitKeys = Object.keys(unitGroups);
    const flowNodes = [];

    unitKeys.forEach((unitKey, colIdx) => {
      const groupNodes = unitGroups[unitKey];
      groupNodes.forEach((node, rowIdx) => {
        flowNodes.push({
          id: node.id,
          type: "conceptNode",
          position: { x: colIdx * 260 + 50, y: rowIdx * 120 + 50 },
          data: {
            node,
            isKnown: knownConceptIds.includes(node.id),
            isTarget: targetConceptId === node.id,
            onToggleMastery,
            onSelectTarget,
          },
        });
      });
    });

    const flowEdges = edgesList.map((e) => ({
      id: `e-${e.source_id}-${e.target_id}`,
      source: e.source_id,
      target: e.target_id,
      animated: true,
      style: { stroke: "#525252", strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#525252" },
    }));

    return { initialNodes: flowNodes, initialEdges: flowEdges };
  }, [summary, knownConceptIds, targetConceptId, onToggleMastery, onSelectTarget]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (!summary || summary.nodes.length === 0) {
    return (
      <div className="w-full h-full min-h-[450px] bg-neutral-50 border border-neutral-200 rounded-lg flex items-center justify-center text-center p-6">
        <div>
          <p className="text-xs font-semibold text-neutral-700">
            No Concept Graph Loaded
          </p>
          <p className="text-[11px] text-neutral-400 mt-1">
            Upload a syllabus PDF or input raw text above to instantiate graph nodes.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[520px] bg-neutral-50 border border-neutral-200 rounded-lg overflow-hidden relative shadow-inner">
      <ReactFlow
        nodes={initialNodes}
        edges={initialEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background color="#d4d4d4" gap={16} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
