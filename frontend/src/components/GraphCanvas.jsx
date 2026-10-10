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
  const { node, isKnown, isTarget, onToggleMastery, onSelectTarget, nodeIndex = 0 } = data;
  
  const colors = ["bg-white", "bg-[#F4EFE6]"];
  const accentColors = ["bg-bauhaus-red", "bg-bauhaus-blue", "bg-bauhaus-yellow"];
  const nodeBg = colors[nodeIndex % colors.length];
  const accentBg = accentColors[nodeIndex % accentColors.length];

  return (
    <div
      className={`px-4 py-3 border-[3px] border-bauhaus-black text-left min-w-[200px] shadow-bauhaus transition-all ${isTarget ? "bg-bauhaus-blue text-white" : isKnown ? "bg-bauhaus-cream text-bauhaus-black opacity-80" : `${nodeBg} text-bauhaus-black hover:bg-bauhaus-yellow`}`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span
          className={`text-[10px] font-mono font-black px-1.5 py-0.5 border border-bauhaus-black ${isTarget ? "bg-bauhaus-black text-white" : `${accentBg} ${accentBg === "bg-bauhaus-yellow" ? "text-bauhaus-black" : "text-white"}`}`}
        >
          {node.unit || "General"}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleMastery(node.id);
          }}
          className={`text-[10px] font-black uppercase font-bauhaus tracking-wider px-2 py-0.5 cursor-pointer transition-colors border-2 border-bauhaus-black ${isKnown ? "bg-bauhaus-black text-white hover:bg-bauhaus-black/90" : isTarget ? "bg-white text-bauhaus-black hover:bg-bauhaus-yellow" : "bg-bauhaus-red text-white hover:bg-bauhaus-red/90"}`}
        >
          {isKnown ? "Mastered" : "Mark Mastered"}
        </button>
      </div>

      <h3 className="text-xs font-black uppercase font-bauhaus leading-snug tracking-wider">{node.name}</h3>

      <div className="mt-2 pt-2 border-t-[3px] border-bauhaus-black flex items-center justify-between text-[10px] font-mono font-bold">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelectTarget(node.id);
          }}
          className={`hover:underline cursor-pointer ${isTarget ? "text-white" : "text-bauhaus-black"}`}
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
              nodeIndex: rowIdx + colIdx, // for coloring
            },
        });
      });
    });

    const flowEdges = edgesList.map((e) => ({
      id: `e-${e.source_id}-${e.target_id}`,
      source: e.source_id,
      target: e.target_id,
      animated: true,
      style: { stroke: "#141518", strokeWidth: 3 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#141518" },
    }));

    return { initialNodes: flowNodes, initialEdges: flowEdges };
  }, [summary, knownConceptIds, targetConceptId, onToggleMastery, onSelectTarget]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  if (!summary || summary.nodes.length === 0) {
    return (
      <div className="w-full h-full min-h-[450px] bg-[#E6E0D3] border-[3px] border-bauhaus-black flex items-center justify-center text-center p-6 shadow-bauhaus">
        <div>
          <p className="text-xs font-black uppercase font-bauhaus tracking-wider text-bauhaus-black">
            No Concept Graph Loaded
          </p>
          <p className="text-[11px] text-bauhaus-black font-mono font-bold mt-1">
            Upload a syllabus PDF or input raw text above to instantiate graph nodes.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-[520px] bg-[#E6E0D3] border-[3px] border-bauhaus-black overflow-hidden relative shadow-bauhaus">
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
