# Implementation Plan: Remote Ollama Config & Root-Based App Serving

## Stage 1: Analyze Current server.py Behavior
### Purpose
Understand existing constants, request handling, and startup logging in `server.py` to identify exact edit points.

### Targets
- `server.py`

### Steps
1. Open `server.py`.
2. Locate the current Ollama URL constant (e.g., `OLLAMA_URL = "http://localhost:11434"`).
3. Locate the handler class (likely `CORSRequestHandler`) that subclasses `http.server.SimpleHTTPRequestHandler`.
4. Identify the existing `do_POST` implementation that proxies `/api/*` requests to Ollama.
5. Identify any existing `do_GET` implementation (if present); if not present, confirm that GET is currently inherited from `SimpleHTTPRequestHandler`.
6. Locate the `__main__` block that:
   - Creates the HTTP server
   - Prints the startup banner / quickstart instructions

### Success Criteria
- Exact locations for Ollama URL definition, POST proxy logic, and startup banner are known.
- Decision made on whether `do_GET` is currently overridden or will need to be added.


## Stage 2: Add Env-Var-Based OLLAMA_BASE_URL Configuration
### Purpose
Allow configuring the Ollama backend base URL via `OLLAMA_BASE_URL`, with a safe default and minimal validation.

### Targets
- `server.py`

### Steps
1. At the module level near the existing Ollama-related constants, add logic to read `OLLAMA_BASE_URL` from `os.environ` with a default of `"http://localhost:11434"`.
2. Include a simple safety check so that an empty string from the environment falls back to the default and optionally logs or comments a warning.
3. Replace any remaining hard-coded `"http://localhost:11434"` assignments for the Ollama base with the new computed configuration variable.
4. In the `do_POST` proxy logic, confirm that the target URL continues to be constructed as the base URL plus `self.path` (e.g., `f"{OLLAMA_URL}{self.path}"`), using the newly configured value.
5. Verify that no other parts of `server.py` rely on a hard-coded Ollama URL.

### Success Criteria
- When `OLLAMA_BASE_URL` is unset, behavior is identical to current: requests proxy to `http://localhost:11434/api/...`.
- When `OLLAMA_BASE_URL` is set to a custom URL, all proxied `/api/*` requests use that base instead.
- The change is confined to `server.py` and does not introduce new dependencies.


## Stage 3: Adjust GET Handling for Root-Based App Serving
### Purpose
Serve `santa-tracker.html` for `/` and `/index.html` while preserving `/santa-tracker.html` and existing static file behavior.

### Targets
- `server.py` (CORSRequestHandler or equivalent HTTP handler class)

### Steps
1. In the handler class that currently extends `SimpleHTTPRequestHandler`, add or modify a `do_GET` method.
2. At the start of `do_GET`, inspect `self.path`:
   - If `self.path == '/'`, change it to `'/santa-tracker.html'`.
   - Else if `self.path == '/index.html'`, change it to `'/santa-tracker.html'`.
3. For all cases (including unchanged paths), delegate to the parent GET handling by calling `super().do_GET()`.
4. Confirm that `/santa-tracker.html` continues to be served unchanged via the standard static file mechanism.
5. Confirm that other static assets (JS, CSS, images) are still served using the default behavior of `SimpleHTTPRequestHandler`.

### Success Criteria
- `http://localhost:PORT/` loads the Santa Tracker SPA via `santa-tracker.html`.
- `http://localhost:PORT/index.html` loads the same SPA.
- `http://localhost:PORT/santa-tracker.html` still works exactly as before.
- Requests to other static paths (e.g., JS/CSS bundles) are unaffected.


## Stage 4: Update Startup Logging
### Purpose
Expose both the effective Ollama backend URL and the new root SPA entrypoint in the startup banner.

### Targets
- `server.py` (`__main__` block where the server is started and instructions are printed)

### Steps
1. In the startup banner or print statements in `server.py`, update the displayed app URL to point primarily to `http://localhost:{PORT}/`.
2. Optionally keep a secondary mention of `http://localhost:{PORT}/santa-tracker.html` for backwards familiarity.
3. Add a line that prints the effective Ollama backend URL, using the resolved configuration variable from Stage 2 (e.g., `Ollama backend: {OLLAMA_URL}`).
4. Ensure the startup message remains concise and clear for new users.

### Success Criteria
- When starting the server without env vars, console output shows:
  - Root app URL at `/`.
  - Default Ollama backend URL `http://localhost:11434`.
- When `OLLAMA_BASE_URL` is set, console output reflects the configured remote URL.


## Stage 5: Sanity Check and Manual Verification
### Purpose
Confirm that changes are coherent and match the specification, without adding tests or docs in this step.

### Targets
- `server.py`

### Steps
1. Review `server.py` to ensure the new configuration and routing logic is localized and easy to understand.
2. Verify there are no remaining references to a hard-coded Ollama URL.
3. Confirm that CORS behavior and POST proxy error handling are unchanged except for the configurable base URL.
4. Manually reason through requests to `/`, `/index.html`, `/santa-tracker.html`, and `/api/generate` with and without `OLLAMA_BASE_URL` set, ensuring they all follow the expected paths.

### Success Criteria
- The implementation steps align with the `specification.md` requirements.
- The file remains a single, simple script, consistent with project goals.
