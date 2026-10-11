import React, { useState } from "react";
import { Upload, ArrowRight, AlertCircle } from "lucide-react";
import { uploadAndParse, buildAndInfer, parseSyllabusText, buildGraphFromSyllabus } from "../services/api";

export default function FileUpload({ onPipelineComplete, onError }) {
  const [mode, setMode] = useState("pdf"); // 'pdf' | 'text'
  const [loading, setLoading] = useState(false);
  const [rawText, setRawText] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [subjects, setSubjects] = useState([]);
  const [documentId, setDocumentId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const clearError = () => setErrorMsg(null);

  const handleSubjectSelect = async (courseCode) => {
    clearError();
    setLoading(true);
    try {
      const data = await buildAndInfer(documentId, courseCode);
      onPipelineComplete(data);
    } catch (err) {
      const msg = err.message || "Failed to build graph.";
      setErrorMsg(msg);
      onError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      const msg = "Please select a valid PDF document (.pdf)";
      setErrorMsg(msg);
      onError(msg);
      return;
    }
    clearError();
    setLoading(true);
    setSubjects([]);
    setDocumentId(null);
    try {
      const data = await uploadAndParse(file);
      const theoryFirst = data.subjects.find((s) => s.kind !== "lab") || data.subjects[0];
      if (data.subjects.length === 1) {
        // Single course — build immediately
        const buildData = await buildAndInfer(data.document_id, theoryFirst.course_code);
        onPipelineComplete(buildData);
      } else {
        // Multiple courses — show <select>
        setDocumentId(data.document_id);
        setSubjects(data.subjects);
      }
    } catch (err) {
      let msg = err.message || "Failed to process PDF file.";
      // Surface the not_a_syllabus error specifically
      if (msg.includes("not_a_syllabus") || msg.includes("422")) {
        msg = "This document does not appear to be a university syllabus (not_a_syllabus). Please upload a valid course syllabus PDF.";
      }
      setErrorMsg(msg);
      onError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!rawText.trim()) return;
    clearError();
    setLoading(true);
    try {
      const parsedSyllabus = await parseSyllabusText(rawText);
      await buildGraphFromSyllabus(parsedSyllabus);
      onPipelineComplete({ parsed_syllabus: parsedSyllabus });
    } catch (err) {
      const msg = err.message || "Failed to parse text.";
      setErrorMsg(msg);
      onError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border-[3px] border-bauhaus-black p-5 shadow-bauhaus relative mt-4">
      <div className="absolute -top-3 -left-3 bg-bauhaus-black text-white text-[10px] font-black px-1.5 py-0.5 font-mono">01</div>
      <div className="flex items-center justify-between border-b-[3px] border-bauhaus-black pb-3 mb-4">
        <h2 className="text-sm font-black uppercase font-bauhaus text-bauhaus-black tracking-wider">
          Curriculum Input
        </h2>
        <div className="flex items-center bg-bauhaus-cream border-2 border-bauhaus-black text-xs font-mono font-bold">
          <button
            onClick={() => setMode("pdf")}
            className={`px-3 py-1 font-bold transition-colors ${mode === "pdf" ? "bg-bauhaus-blue text-white border-r-2 border-bauhaus-black" : "text-bauhaus-black hover:bg-bauhaus-yellow border-r-2 border-bauhaus-black"}`}
          >
            PDF Upload
          </button>
          <button
            onClick={() => setMode("text")}
            className={`px-3 py-1 font-bold transition-colors ${mode === "text" ? "bg-bauhaus-blue text-white" : "text-bauhaus-black hover:bg-bauhaus-yellow"}`}
          >
            Raw Text
          </button>
        </div>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="flex items-start gap-2 bg-red-50 border-2 border-bauhaus-red p-3 mb-4">
          <AlertCircle className="w-4 h-4 text-bauhaus-red mt-0.5 flex-shrink-0" />
          <p className="text-xs font-bold text-bauhaus-red font-mono">{errorMsg}</p>
        </div>
      )}

      {/* Course selector dropdown when multi-subject PDF */}
      {subjects.length > 1 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-black uppercase font-bauhaus text-bauhaus-black tracking-wider">Select Subject</h3>
          <p className="text-xs font-bold text-bauhaus-black font-mono">
            This PDF contains multiple subjects. Please select one to graph.
          </p>
          <select
            disabled={loading}
            defaultValue=""
            onChange={(e) => e.target.value && handleSubjectSelect(e.target.value)}
            className="w-full text-sm font-bold border-[3px] border-bauhaus-black p-2 bg-white text-bauhaus-black focus:outline-none focus:border-bauhaus-blue font-mono"
          >
            <option value="" disabled>— Choose a subject —</option>
            {subjects.map((s) => (
              <option key={s.course_code} value={s.course_code}>
                {s.course_code} — {s.course_title} ({s.topic_count} topics, {s.kind})
              </option>
            ))}
          </select>
          {loading && <p className="text-xs text-neutral-500 italic mt-2">Building graph...</p>}
        </div>
      ) : mode === "pdf" ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-4 border-dashed p-8 text-center transition-colors ${dragOver ? "border-bauhaus-blue bg-bauhaus-cream" : "border-bauhaus-black bg-white hover:bg-bauhaus-cream"}`}
        >
          <Upload className="w-6 h-6 text-bauhaus-black mx-auto mb-2" />
          <p className="text-xs font-bold text-bauhaus-black font-mono">
            Drag and drop your syllabus PDF here
          </p>
          <p className="text-[11px] text-bauhaus-black font-bold mt-1">
            Supports official course outlines, unit syllabi, and lecture schedules
          </p>
          <label className="inline-block mt-4">
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              className="hidden"
              disabled={loading}
            />
            <span className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-black uppercase font-bauhaus tracking-wider text-bauhaus-black bg-bauhaus-yellow border-2 border-bauhaus-black hover:bg-[#e5a61a] px-3.5 py-2 shadow-bauhaus transition-colors">
              {loading ? "Processing Syllabus..." : "Select PDF Document"}
            </span>
          </label>
        </div>
      ) : (
        <form onSubmit={handleTextSubmit} className="space-y-3">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste syllabus units and topics here..."
            rows={5}
            className="w-full text-xs p-3 font-mono border-[3px] border-bauhaus-black focus:outline-none focus:border-bauhaus-blue bg-bauhaus-cream text-bauhaus-black placeholder-neutral-500 font-bold"
          />
          <button
            type="submit"
            disabled={loading || !rawText.trim()}
            className="flex items-center justify-center gap-1.5 w-full text-xs font-black uppercase font-bauhaus tracking-wider text-white bg-bauhaus-red hover:bg-bauhaus-red/90 border-2 border-bauhaus-black shadow-bauhaus disabled:opacity-50 py-2 transition-colors"
          >
            <span>{loading ? "Parsing Topics..." : "Build Knowledge Graph"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>
      )}
    </div>
  );
}
