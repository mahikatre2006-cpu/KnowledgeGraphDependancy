import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./theme.css";
import GeminiApp from "./GeminiApp.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <GeminiApp />
  </StrictMode>,
);
