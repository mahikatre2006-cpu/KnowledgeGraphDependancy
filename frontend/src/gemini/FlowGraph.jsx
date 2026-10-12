import React, { useMemo } from "react";
import { ReactFlow, Background, Controls, Handle, Position, MarkerType } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const COL_WIDTH = 270;
const ROW_HEIGHT = 100;

function TopicNode({ data }) {
  const { name, unit, isBottleneck, state } = data; // state: "selected" | "prereq" | "dim" | "none"
  const hidden = { opacity: 0, pointerEvents: "none" };
  const look = state !== "none" ? state : isBottleneck ? "key" : "";
  return (
    <div className={`kp-node ${look}`}>
      <Handle id="t" type="target" position={Position.Top} style={hidden} />
      <Handle id="l" type="target" position={Position.Left} style={hidden} />
      <div className="kp-node-top">
        <span className={`kp-tag u${((unit - 1) % 3) + 1}`}>Unit {unit}</span>
        {state === "selected" && <span className="kp-tag">Your goal</span>}
        {state === "prereq" && <span className="kp-tag">Learn first</span>}
        {state === "none" && isBottleneck && <span className="kp-tag">Key topic</span>}
      </div>
      <div className="kp-node-name">{name}</div>
      <Handle id="b" type="source" position={Position.Bottom} style={hidden} />
      <Handle id="r" type="source" position={Position.Right} style={hidden} />
    </div>
  );
}

const nodeTypes = { topic: TopicNode };

export default function FlowGraph({ nodes, edges, bottleneckIds, selectedId, prereqIds, onSelect }) {
  const { flowNodes, flowEdges } = useMemo(() => {
    const unitById = Object.fromEntries(nodes.map((n) => [n.id, n.unit]));
    const unitOrder = [...new Set(nodes.map((n) => n.unit))].sort((a, b) => a - b);
    const rowInUnit = {};

    const flowNodes = nodes.map((n) => {
      const col = unitOrder.indexOf(n.unit);
      const row = (rowInUnit[n.unit] = (rowInUnit[n.unit] ?? -1) + 1);
      const state = !selectedId ? "none"
        : n.id === selectedId ? "selected"
        : prereqIds.has(n.id) ? "prereq"
        : "dim";
      return {
        id: n.id,
        type: "topic",
        position: { x: col * COL_WIDTH, y: row * ROW_HEIGHT },
        data: { name: n.name, unit: n.unit, isBottleneck: bottleneckIds.has(n.id), state },
      };
    });

    const flowEdges = edges.map((e) => {
      const sameUnit = unitById[e.source] === unitById[e.target];
      const onPath = !selectedId || ((prereqIds.has(e.source) || e.source === selectedId) && (prereqIds.has(e.target) || e.target === selectedId));
      return {
        id: `${e.source}->${e.target}`,
        source: e.source,
        target: e.target,
        sourceHandle: sameUnit ? "b" : "r",
        targetHandle: sameUnit ? "t" : "l",
        type: "smoothstep",
        style: { stroke: onPath && selectedId ? "#ff008c" : "#16112e", strokeWidth: 3, opacity: onPath ? 1 : 0.12 },
        markerEnd: { type: MarkerType.ArrowClosed, color: onPath && selectedId ? "#ff008c" : "#16112e" },
      };
    });

    return { flowNodes, flowEdges };
  }, [nodes, edges, bottleneckIds, selectedId, prereqIds]);

  return (
    <div className="kp-graph">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        nodesConnectable={false}
        nodesDraggable={false}
        onNodeClick={(_, node) => onSelect(node.id === selectedId ? null : node.id)}
        onPaneClick={() => onSelect(null)}
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
      >
        <Background color="#e8e0f5" gap={22} size={2} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
