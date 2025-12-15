# Research Index

## santa-local-ai Architecture Overview
**Question:** How is the santa-local-ai app structured today, specifically how Ollama is configured/used and how the frontend is served (santa-tracker.html vs root/index)?
**Finding:** Single-process Python HTTP server on port 8000 serves static files from repo root and proxies POST /api/* to a fixed local Ollama instance at http://localhost:11434. Frontend is a standalone React app embedded in santa-tracker.html that directly calls the server at /api/generate; there is no separate root index or routing.
**Details:** See `research/santa-local-ai-architecture.md`.
