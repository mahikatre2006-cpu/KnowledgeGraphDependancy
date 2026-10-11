import React, { useMemo } from "react";
import FlowMap from "./FlowMap.jsx";

// Every topic that must be learned before `targetId`, found by walking the arrows backwards.
export function findPrerequisiteIds(targetId, edges) {
  const parents = {};
  edges.forEach((e) => (parents[e.target] ??= []).push(e.source));
  const found = new Set();
  const stack = [targetId];
  while (stack.length) {
    (parents[stack.pop()] ?? []).forEach((p) => {
      if (!found.has(p)) {
        found.add(p);
        stack.push(p);
      }
    });
  }
  return found;
}

function BackgroundCards({ items, empty }) {
  if (items.length === 0) return <p className="lp-body">{empty}</p>;
  return (
    <div className="lp-res-grid">
      {items.map((m) => (
        <div key={m.name} className="lp-res-card">
          <h3>{m.name}</h3>
          <p className="lp-body">{m.reason}</p>
          {m.needed_for.length > 0 && (
            <p className="lp-body lp-res-for"><b>Needed for:</b> {m.needed_for.map((t) => t.name).join(", ")}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function StepList({ steps, goalId, showPrereqs }) {
  return (
    <ol className="lp-res-steps">
      {steps.map((s, i) => (
        <li key={s.id} className={`lp-res-step ${s.id === goalId ? "goal" : ""}`}>
          <span className="lp-res-no">{i + 1}</span>
          <span>
            {s.name}
            <small>
              Unit {s.unit}
              {s.id === goalId ? " · your goal" : ""}
              {showPrereqs && s.prerequisites?.length > 0 ? ` · after: ${s.prerequisites.join(", ")}` : ""}
            </small>
          </span>
        </li>
      ))}
    </ol>
  );
}

/**
 * Everything shown after a syllabus is analysed: map, topic planner,
 * whole-syllabus missing prerequisites and the full study order.
 */
export default function Results({ result, selectedId, onSelect }) {
  const keyIds = useMemo(() => new Set((result.bottlenecks ?? []).map((b) => b.id)), [result]);
  const prereqIds = useMemo(
    () => (selectedId ? findPrerequisiteIds(selectedId, result.edges) : new Set()),
    [result, selectedId],
  );

  const selected = result.nodes.find((n) => n.id === selectedId);
  const toStudy = result.study_flow.filter((s) => prereqIds.has(s.id) || s.id === selectedId);
  const background = result.missing_prerequisites.filter((m) =>
    m.needed_for.some((t) => t.id === selectedId || prereqIds.has(t.id)),
  );

  return (
    <div id="results">
      {/* MAP */}
      <section className="lp-section lp-blush">
        <div className="lp-inner">
          <span className="lp-note">{result.course_title}{result.course_code ? ` · ${result.course_code}` : ""}</span>
          <h2 className="lp-h2">Your concept map</h2>
          <p className="lp-lead lp-res-lead">
            Arrows lead from a topic to the topics built on it. Click any topic to light up what you need before it.
            Yellow cards are key topics that unlock the most of the syllabus.
          </p>
          <FlowMap nodes={result.nodes} edges={result.edges} keyIds={keyIds}
            selectedId={selectedId} prereqIds={prereqIds} onSelect={onSelect} />
        </div>
      </section>

      {/* PLANNER */}
      <section className="lp-section lp-indigo">
        <div className="lp-inner">
          <h2 className="lp-h2">Plan your study</h2>
          <label className="lp-select-label">
            Select the topic you want to learn
            <select className="lp-select" value={selectedId ?? ""} onChange={(e) => onSelect(e.target.value || null)}>
              <option value="">Choose a topic...</option>
              {result.nodes.map((n) => <option key={n.id} value={n.id}>Unit {n.unit}: {n.name}</option>)}
            </select>
          </label>

          {!selected ? (
            <p className="lp-lead">Pick a topic (or click one in the map) to see what you are missing and what to study first.</p>
          ) : (
            <div className="lp-cols">
              <div>
                <h3 className="lp-colhead">Missing prerequisites ({background.length})</h3>
                <p className="lp-body lp-res-lead">Background you need that this syllabus does not teach.</p>
                <BackgroundCards items={background} empty="None. Nothing outside the syllabus is needed for this topic." />
              </div>
              <div>
                <h3 className="lp-colhead">Topics to study ({toStudy.length})</h3>
                <p className="lp-body lp-res-lead">Study these in order to reach <b>{selected.name}</b>.</p>
                <StepList steps={toStudy} goalId={selectedId} />
              </div>
            </div>
          )}
        </div>
      </section>

      {/* WHOLE-SYLLABUS BACKGROUND */}
      <section className="lp-section lp-pink">
        <div className="lp-inner">
          <h2 className="lp-h2">Revise these first</h2>
          <p className="lp-lead lp-res-lead">Background this syllabus assumes you already know, but never teaches.</p>
          <BackgroundCards items={result.missing_prerequisites} empty="No missing prerequisites detected for this syllabus." />
        </div>
      </section>

      {/* FULL ORDER */}
      <section className="lp-section lp-white">
        <div className="lp-inner">
          <h2 className="lp-h2">The full study order</h2>
          <StepList steps={result.study_flow} showPrereqs />
        </div>
      </section>
    </div>
  );
}
