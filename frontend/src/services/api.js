const API_BASE_URL = "http://127.0.0.1:8000/api/v1";

export async function uploadAndBuildGraph(file, clearExisting = true, addUnitSequentialEdges = true) {
  const formData = new FormData();
  formData.append("file", file);

  const url = `${API_BASE_URL}/pipeline/upload-and-build-graph?clear_existing=${clearExisting}&add_unit_sequential_edges=${addUnitSequentialEdges}`;
  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to process PDF syllabus.");
  }
  return await response.json();
}

export async function parseSyllabusText(text) {
  const response = await fetch(`${API_BASE_URL}/syllabus/parse-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!response.ok) {
    throw new Error("Failed to parse syllabus text.");
  }
  return await response.json();
}

export async function buildGraphFromSyllabus(syllabus) {
  const response = await fetch(`${API_BASE_URL}/pipeline/build-graph-from-syllabus`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(syllabus),
  });

  if (!response.ok) {
    throw new Error("Failed to build graph from syllabus.");
  }
  return await response.json();
}

export async function getGraphSummary() {
  const response = await fetch(`${API_BASE_URL}/graph/summary`);
  if (!response.ok) {
    throw new Error("Failed to fetch graph summary.");
  }
  return await response.json();
}

export async function inferRelationships(similarityThreshold = 0.30, minConfidence = 0.50) {
  const response = await fetch(`${API_BASE_URL}/graph/infer-relationships`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      similarity_threshold: similarityThreshold,
      min_confidence: minConfidence,
      auto_add_to_graph: true,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to run relationship inference.");
  }
  return await response.json();
}

export async function getTopologicalSequence() {
  const response = await fetch(`${API_BASE_URL}/sequence/topological`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail?.message || "Failed to fetch topological sequence.");
  }
  return await response.json();
}

export async function getMissingPrerequisites(targetConceptId, knownConceptIds) {
  const response = await fetch(`${API_BASE_URL}/analytics/missing-prerequisites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_concept_id: targetConceptId,
      known_concept_ids: knownConceptIds,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to calculate missing prerequisites.");
  }
  return await response.json();
}

export async function getBottlenecks(topN = 10) {
  const response = await fetch(`${API_BASE_URL}/analytics/bottlenecks?top_n=${topN}`);
  if (!response.ok) {
    throw new Error("Failed to fetch curriculum bottlenecks.");
  }
  return await response.json();
}

export async function getRecommendations(knownConceptIds, targetConceptId = null) {
  const response = await fetch(`${API_BASE_URL}/recommendations/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      known_concept_ids: knownConceptIds,
      target_concept_id: targetConceptId,
      max_recommendations: 10,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to generate recommendations.");
  }
  return await response.json();
}


export async function uploadAndParse(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/pipeline/upload-and-parse`, {
    method: "POST",
    body: formData,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Failed to parse subjects.");
  }
  return data;
}

export async function buildAndInfer(documentId, courseCode) {
  const response = await fetch(`${API_BASE_URL}/pipeline/build-and-infer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_id: documentId,
      course_code: courseCode,
      clear_existing: true,
      add_unit_sequential_edges: false
    })
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Failed to build graph.");
  }
  return data;
}
