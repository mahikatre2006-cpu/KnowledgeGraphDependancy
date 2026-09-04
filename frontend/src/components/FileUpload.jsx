import React, { useState } from "react";
import { Upload, FileText, ArrowRight } from "lucide-react";
import { uploadAndBuildGraph, parseSyllabusText, buildGraphFromSyllabus } from "../services/api";

export default function FileUpload({ onPipelineComplete, onError }) {
  const [mode, setMode] = useState("pdf"); // 'pdf' | 'text'
  const [loading, setLoading] = useState(false);
  const [rawText, setRawText] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const handleFileUpload = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      onError("Please select a valid PDF document (.pdf)");
      return;
    }
    setLoading(true);
    try {
      const data = await uploadAndBuildGraph(file);
      onPipelineComplete(data);
    } catch (err) {
      onError(err.message || "Failed to process PDF file.");
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
    setLoading(true);
    try {
      const parsedSyllabus = await parseSyllabusText(rawText);
      await buildGraphFromSyllabus(parsedSyllabus);
      onPipelineComplete({ parsed_syllabus: parsedSyllabus });
    } catch (err) {
      onError(err.message || "Failed to parse text.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-neutral-100 pb-3 mb-4">
        <h2 className="text-sm font-semibold text-neutral-900">
          Curriculum Input
        </h2>
        <div className="flex items-center gap-1 bg-neutral-100 p-0.5 rounded text-xs">
          <button
            onClick={() => setMode("pdf")}
            className={`px-3 py-1 rounded font-medium transition-colors ${
              mode === "pdf" ? "bg-white text-neutral-900 shadow-xs" : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            PDF Upload
          </button>
          <button
            onClick={() => setMode("text")}
            className={`px-3 py-1 rounded font-medium transition-colors ${
              mode === "text" ? "bg-white text-neutral-900 shadow-xs" : "text-neutral-500 hover:text-neutral-900"
            }`}
          >
            Raw Text
          </button>
        </div>
      </div>

      {mode === "pdf" ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragOver ? "border-neutral-900 bg-neutral-100" : "border-neutral-200 bg-neutral-50 hover:bg-neutral-100/50"
          }`}
        >
          <Upload className="w-6 h-6 text-neutral-400 mx-auto mb-2" />
          <p className="text-xs font-medium text-neutral-800">
            Drag and drop your syllabus PDF here
          </p>
          <p className="text-[11px] text-neutral-400 mt-1">
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
            <span className="cursor-pointer inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900 bg-white border border-neutral-300 hover:border-neutral-400 px-3.5 py-1.5 rounded shadow-2xs transition-colors">
              {loading ? "Processing Syllabus..." : "Select PDF Document"}
            </span>
          </label>
        </div>
      ) : (
        <form onSubmit={handleTextSubmit} className="space-y-3">
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste syllabus units and topics here... (e.g. Unit 1: Foundations \n - Linear Algebra \n - Calculus)"
            rows={5}
            className="w-full text-xs p-3 font-mono border border-neutral-200 rounded focus:outline-none focus:border-neutral-900 bg-neutral-50 text-neutral-800 placeholder-neutral-400"
          />
          <button
            type="submit"
            disabled={loading || !rawText.trim()}
            className="flex items-center justify-center gap-1.5 w-full text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 disabled:opacity-50 py-2 rounded transition-colors"
          >
            <span>{loading ? "Parsing Topics..." : "Build Knowledge Graph"}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>
      )}
    </div>
  );
}
