import React, { useMemo, useEffect, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow,
  ReactFlowProvider,
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
      className={`px-4 py-3 border-[3px] border-bauhaus-black text-left min-w-[200px] shadow-bauhaus transition-all ${
        isTarget
          ? "bg-bauhaus-blue text-white"
          : isKnown
          ? "bg-bauhaus-cream text-bauhaus-black opacity-80"
          : `${nodeBg} text-bauhaus-black hover:bg-bauhaus-yellow`
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <span
          className={`text-[10px] font-mono font-black px-1.5 py-0.5 border border-bauhaus-black ${
            isTarget
              ? "bg-bauhaus-black text-white"
              : `${accentBg} ${accentBg === "bg-bauhaus-yellow" ? "text-bauhaus-black" : "text-white"}`
          }`}
        >
          {node.unit || "General"}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleMastery(node.id);
          }}
          className={`text-[10px] font-black uppercase font-bauhaus tracking-wider px-2 py-0.5 cursor-pointer transition-colors border-2 border-bauhaus-black ${
            isKnown
              ? "bg-bauhaus-black text-white hover:bg-bauhaus-black/90"
              : isTarget
              ? "bg-white text-bauhaus-black hover:bg-bauhaus-yellow"
              : "bg-bauhaus-red text-white hover:bg-bauhaus-red/90"
          }`}
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

// Inner component that has access to useReactFlow
function GraphCanvasInner({
  summary,
  knownConceptIds,
  targetConceptId,
  onToggleMastery,
  onSelectTarget,
}) {
  const { fitView } = useReactFlow();

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!summary || !summary.nodes) return { initialNodes: [], initialEdges: [] };

    const nodesList = summary.nodes;
    const edgesList = summary.edges || [];

    const flowNodes = nodesList.map((node, idx) => {
      // Use backend position if available, otherwise fall back to unit-grid layout
      let pos;
      if (node.metadata && node.metadata.position) {
        pos = { x: node.metadata.position.x, y: node.metadata.position.y };
      } else {
        // Fallback: group by unit
        const unitMatch = (node.unit || "").match(/\d+/);
        const col = unitMatch ? parseInt(unitMatch[0]) : 0;
        pos = { x: col * 280 + 50, y: (idx % 10) * 90 + 50 };
      }

      return {
        id: String(node.id),       // must be string
        type: "conceptNode",
        position: pos,
        data: {
          node,
          isKnown: knownConceptIds.includes(node.id),
          isTarget: targetConceptId === node.id,
          onToggleMastery,
          onSelectTarget,
          nodeIndex: idx,
        },
      };
    });

    const flowEdges = edgesList.map((e) => ({
      id: `e-${String(e.source_id)}-${String(e.target_id)}`,  // string id
      source: String(e.source_id),                             // string source
      target: String(e.target_id),                             // string target
      animated: true,
      style: { stroke: "#141518", strokeWidth: 3 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#141518" },
    }));

    return { initialNodes: flowNodes, initialEdges: flowEdges };
  }, [summary, knownConceptIds, targetConceptId, onToggleMastery, onSelectTarget]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Sync nodes/edges when summary changes AND call fitView
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
    // fitView after a tick so React Flow has time to mount nodes
    const t = setTimeout(() => fitView({ padding: 0.15, duration: 400 }), 50);
    return () => clearTimeout(t);
  }, [initialNodes, initialEdges, setNodes, setEdges, fitView]);

  if (!summary || summary.nodes.length === 0) {
    return (
      <div className="w-full h-full min-h-[520px] bg-[#E6E0D3] border-[3px] border-bauhaus-black flex items-center justify-center text-center p-6 shadow-bauhaus">
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
    /* Explicit height required by React Flow */
    <div style={{ width: "100%", height: "520px" }} className="bg-[#E6E0D3] border-[3px] border-bauhaus-black overflow-hidden relative shadow-bauhaus">
      <ReactFlow
        nodes={nodes}
        edges={edges}
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

// Wrap with ReactFlowProvider so useReactFlow() works
export default function GraphCanvas(props) {
  return (
    <ReactFlowProvider>
      <GraphCanvasInner {...props} />
    </ReactFlowProvider>
  );
}
