# KDG rules (read first, every session)
- Exactly one trained local ML model (XGBoost/LogReg) predicts "is A a prerequisite of B?". All graph logic after that is deterministic code.
- LLMs/APIs (Gemini, OCR) may only help data prep offline (extraction, labeling). Never at prediction time. The prediction path must run with no API key and no network.
- Scope: Mumbai University IT and Computer Engineering (Rev-2019 'C') only. AIML is a separate tag, train-only. No autonomous-college PDFs.
- The agent never fills human_label or gold-set labels. Review samples are flat random, seed 42.
- Every number in a report must come from a command's output. Write UNVERIFIABLE if it wasn't run.
- Never modify full_pipeline.py, existing PDFs, or the frontend (Mahi owns it). Never delete files.
- One phase per chat. Stop at each gate and wait for approval.