# Specification: Remote Ollama Config & Root-Based App Serving

## TLDR

**Key Points:**
- Allow configuring the Ollama backend URL via environment variable while keeping localhost as the default.
- Serve the Santa Tracker SPA at the root path so users can open `http://localhost:8000/` instead of `.../santa-tracker.html`.

**Major Features:**
- `OLLAMA_BASE_URL` (and optional port) environment-based configuration in `server.py`.
- Updated HTTP server behavior and logs to reflect configurable Ollama target.
- Root-based static serving so `/` (and likely `/index.html`) load `santa-tracker.html`.

## 1. Current Behavior Overview

Santa Local AI runs a single-process Python HTTP server (`server.py`) on port 8000 that:
- Serves static files from the repo root directory using `http.server.SimpleHTTPRequestHandler`.
- Proxies POST requests under `/api/*` (e.g., `/api/generate`) directly to a hard-coded local Ollama instance at `http://localhost:11434`.
- Exposes CORS headers to allow browser-based access without separate CORS config.
- Instructs users to open `http://localhost:8000/santa-tracker.html` explicitly; there is no dedicated root index file or routing.

This spec defines changes only to configuration handling and HTTP serving behavior; the React app in `santa-tracker.jsx` remains functionally the same, still calling `/api/generate` etc.

## 2. Requirements

### 2.1 Remote Ollama Backend Configuration

Functional requirements:
- The server must support configuring the Ollama base URL via environment variables instead of a hard-coded `http://localhost:11434`.
- Default behavior (when no env vars are set) must remain compatible with the current setup:
  - If no relevant environment variable is present, Ollama requests go to `http://localhost:11434`.
- The configuration must allow pointing to remote hosts, including non-local network addresses such as `http://192.168.1.50:11434`, `http://ollama.my-domain.com`, or alternative ports.
- The configuration must apply uniformly to all proxied endpoints under `/api/*`.
- The resolved Ollama URL should be visible in the server startup output for easier debugging.

Non-functional requirements:
- The change must be backwards compatible for existing users who do not set any new environment variables.
- The solution must be simple to configure for non-experts (single env var preferred over complex config files).
- Avoid introducing additional external dependencies; stay within the Python standard library.

### 2.2 Root-Based App Serving

Functional requirements:
- Navigating to `http://localhost:8000/` in a browser must load the Santa Tracker app without users needing to manually add `/santa-tracker.html`.
- The existing `santa-tracker.html` file remains the single HTML entrypoint for the SPA.
- The previous URL `http://localhost:8000/santa-tracker.html` should continue to work for backwards compatibility.
- Requests for `/index.html` should also serve the same SPA content as `santa-tracker.html`.

Non-functional requirements:
- Avoid complex routing or frameworks; keep using the existing `http.server.SimpleHTTPRequestHandler`-based approach.
- Keep the project as a self-contained, single-file server for easy use.

## 3. Proposed Changes

### 3.1 Environment Variables for Ollama Backend

Introduce the following environment variables, read in `server.py` at startup:

- `OLLAMA_BASE_URL` (string, optional)
  - Example: `http://localhost:11434`, `http://192.168.1.23:11434`, `http://ollama.internal:8080`.
  - If set, it fully determines the base URL for all Ollama proxy requests.
  - If not set, the base URL defaults to `http://localhost:11434` (current behavior).

Implementation behavior:
- Replace the constant assignment `OLLAMA_URL = "http://localhost:11434"` with logic that checks for `OLLAMA_BASE_URL` from `os.environ` and falls back to the current default.
- Ensure the value is treated as a full base URL and concatenated with `self.path` when forwarding requests.
- On startup, print the effective Ollama base URL to the console next to the server URL.

Validation/edge cases:
- Minimal validation: if the env var is set but clearly malformed (e.g., empty string), log a warning and default to `http://localhost:11434`.
- For this project, detailed URL parsing or strict validation is not required; we rely on the underlying HTTP client (`urllib.request`) to error out if the URL is invalid.

### 3.2 Server Behavior Adjustments (Root-Based Serving)

Modify `CORSRequestHandler` (which subclasses `SimpleHTTPRequestHandler`) to adjust how it resolves paths for static file GET requests.

Behavior changes:
- When the request path is `/`:
  - Serve `santa-tracker.html` instead of the default `directory listing` behavior or `index.html` expectation.
- When the request path is `/index.html`:
  - Serve `santa-tracker.html` content to provide a conventional index URL.
- All other paths should be handled by the underlying `SimpleHTTPRequestHandler` behavior as they are today (including `/santa-tracker.html`, JS, CSS, and image assets).

This can be achieved by overriding `do_GET` to rewrite the path before delegating back to the parent handler.

### 3.3 Startup Logging Updates

Update the startup banner in `server.py` to reflect the new behavior:

- In addition to printing the server URL (`http://localhost:{PORT}`), also print:
  - The SPA entrypoint URL: `http://localhost:{PORT}/`
  - The Ollama backend URL being used, derived from the resolved `OLLAMA_BASE_URL` (or default).

This keeps the quickstart experience clear and shows users how to adjust configuration.

## 4. Detailed Change List

### 4.1 `server.py` Configuration Changes

Scope: single-file update.

1. **Add environment-based configuration for Ollama URL**
   - Import `os` is already present; reuse it.
   - Replace the current constant:
     - Before: `OLLAMA_URL = "http://localhost:11434"`
     - After: compute `OLLAMA_URL` using `os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")`, with a small safety check for empty values.
   - Ensure the proxy logic still builds the target URL as `f"{OLLAMA_URL}{self.path}"`.

2. **Optional: Provide a small helper function/constant at the top of the file**
   - Since this project favors simplicity, we keep everything inline and avoid adding new modules; a small in-file configuration block at the module level is sufficient.

### 4.2 `server.py` HTTP Handling Changes

Extend `CORSRequestHandler` with custom GET behavior for root and index:

1. Override `do_GET` in the handler:
   - If `self.path` is `'/'`: set `self.path = '/santa-tracker.html'` and then call `super().do_GET()`.
   - If `self.path` is `'/index.html'`: also rewrite to `'/santa-tracker.html'` and call `super().do_GET()`.
   - Otherwise, delegate to `super().do_GET()` directly.

2. Leave POST handling unchanged aside from using the new `OLLAMA_URL` configuration.

3. Keep CORS headers behavior unchanged.

### 4.3 Startup Banner Text

Modify the `print(f""" ... """)` banner in the `__main__` block to:
- Reference `http://localhost:{PORT}/` as the primary link.
- Optionally still mention `http://localhost:{PORT}/santa-tracker.html` as an alternative.
- Add a line indicating the effective Ollama URL, for example:
  - `Ollama backend: {OLLAMA_URL}`.

## 5. Acceptance Criteria

### 5.1 Remote Ollama Configuration

- **Default behavior:**
  - With no `OLLAMA_BASE_URL` set, starting the server and performing a request from the frontend results in traffic to `http://localhost:11434/api/...` as before.
  - The startup log includes a line indicating `Ollama backend: http://localhost:11434`.

- **Remote host behavior:**
  - With `OLLAMA_BASE_URL` set to `http://192.168.1.50:11434`, the server logs `Ollama backend: http://192.168.1.50:11434`.
  - Requests from the frontend (e.g., generating a letter) cause POSTs from `server.py` to `http://192.168.1.50:11434/api/...`.
  - If the remote host is unreachable, the client receives a `502` with a JSON error containing `"Ollama not available"` (unchanged behavior, just a different host).

### 5.2 Root-Based App Serving

- Navigating to `http://localhost:8000/` loads the Santa Tracker app exactly as when opening `/santa-tracker.html` directly.
- Navigating to `http://localhost:8000/index.html` loads the same app content.
- Navigating to `http://localhost:8000/santa-tracker.html` continues to work.
- Static assets referenced by `santa-tracker.html` (JS bundles, CSS, images) continue to load without path changes.

### 5.3 Documentation & Developer Experience

- `README.md` or `QUICKSTART.md` is updated (by a future implementation step) to mention:
  - The new `OLLAMA_BASE_URL` environment variable with one or two concrete usage examples.
  - That the primary app URL is now `http://localhost:8000/`.

## 6. Notes for Implementers

- Keep `server.py` as a single, simple script; do not introduce extra modules or external dependencies.
- Users on typical setups (local Ollama + local santa-local-ai) should not notice any change except that opening the root URL now works.
- When testing remote Ollama, ensure network/firewall settings on the Ollama host allow incoming connections from the machine running `server.py`.
