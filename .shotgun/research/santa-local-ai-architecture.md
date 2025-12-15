# santa-local-ai Architecture Overview

## 1. High-level Architecture

santa-local-ai is a very simple, fully local web application composed of:

- A **Python HTTP server** (`server.py`) running on `localhost:8000`
- A **single-page React UI** embedded directly in `santa-tracker.html`, served as a static file
- A **local Ollama LLM backend** assumed to be running at `http://localhost:11434`

The data flow is:

Browser (React SPA in santa-tracker.html)
→ HTTP POST `/api/generate` on Python server (localhost:8000)
→ Python server proxies to Ollama at `http://localhost:11434/api/generate`
→ Response flows back to browser via the Python server.

There is **no build toolchain** (React and Tailwind are loaded from CDNs in the HTML), and there is **no explicit root index routing**; the primary entrypoint is the HTML file `santa-tracker.html` itself.

## 2. Backend: Python HTTP Server (`server.py`)

### 2.1 Entrypoint and Server Setup

- The main module is `server.py`.
- Entrypoint pattern:
  - At module scope:
    - `PORT = 8000`
    - `OLLAMA_URL = "http://localhost:11434"` (hard-coded)
  - At bottom, under `if __name__ == "__main__":`:
    - `os.chdir(os.path.dirname(os.path.abspath(__file__)))` so the server serves files from the repository root.
    - Constructs `socketserver.TCPServer(("", PORT), CORSRequestHandler)`
    - Calls `httpd.serve_forever()` inside a try/except to handle `KeyboardInterrupt`.
    - Prints an ASCII banner including:
      - URL of the server: `http://localhost:{PORT}`
      - Direct link to open: `http://localhost:{PORT}/santa-tracker.html`

### 2.2 Request Handler: `CORSRequestHandler`

Class `CORSRequestHandler` subclasses `http.server.SimpleHTTPRequestHandler` and customizes:

- **CORS behavior:**
  - Overrides `end_headers` to add:
    - `Access-Control-Allow-Origin: *`
    - `Access-Control-Allow-Methods: GET, POST, OPTIONS`
    - `Access-Control-Allow-Headers: Content-Type`
  - Calls `super().end_headers()` afterward.

- **OPTIONS handling:**
  - `do_OPTIONS` simply responds `200` and ends headers.

- **POST handling / Ollama proxy:**
  - `do_POST` is specialized for paths starting with `/api/`:
    - If `self.path.startswith('/api/')`:
      1. Reads the request body from the client:
         - `content_length = int(self.headers['Content-Length'])`
         - `post_data = self.rfile.read(content_length)`
      2. Constructs an upstream request to Ollama:
         - URL: `f"{OLLAMA_URL}{self.path}"` (e.g., `/api/generate` → `http://localhost:11434/api/generate`)
         - Method: implicit POST via `urllib.request.Request` with `data=post_data`
         - Headers: `{'Content-Type': 'application/json'}`
      3. Sends request using `urllib.request.urlopen(req)` and reads `response_data`.
      4. Returns response to browser:
         - `self.send_response(200)` (always 200 if upstream call succeeds)
         - `Content-Type: application/json`
         - `self.end_headers()` (adds CORS headers too via `end_headers` override)
         - Writes `response_data` directly to `wfile` (transparent proxying).
    - **Error handling:**
      - On `urllib.error.URLError`, the handler sends:
        - HTTP status `502`
        - `Content-Type: application/json`
        - JSON body: `{ "error": "Ollama not available: <error>" }`
  - If the path **does not** start with `/api/` and is POST:
    - Responds with `404` and no body.

- **GET handling / static content:**
  - Inherited from `SimpleHTTPRequestHandler` and not overridden.
  - Because of the `os.chdir` call in `__main__`, the server serves **static files from the repository root**.
  - Important static files:
    - `/santa-tracker.html` (main app UI)
    - Assets like `s1.png`, `s2.png`
  - There is **no explicit route for `/`**; hitting `http://localhost:8000/` will use the default directory/index semantics of `SimpleHTTPRequestHandler` (listing or index.html if present). In this repo, **there is no `index.html`**, so directory listing behavior will be used unless disabled by client or environment.

### 2.3 Ollama Backend Configuration

- Ollama configuration is currently **hard-coded**:
  - Base URL: `OLLAMA_URL = "http://localhost:11434"`
  - The server never reads this from environment variables, config files, or CLI flags.
  - All `/api/*` requests are forwarded to this base URL with the same path.
- The Python server **does not know or care** which model is used; it simply forwards JSON.
- The Ollama server is assumed to be running separately via `ollama serve`.

## 3. Frontend: santa-tracker.html vs santa-tracker.jsx

### 3.1 Actual Runtime Entry: `santa-tracker.html`

- `santa-tracker.html` is the **actual file served to the browser** and the primary entrypoint.
- It includes:
  - React 18 UMD bundle via CDN:
    - `https://unpkg.com/react@18/umd/react.production.min.js`
    - `https://unpkg.com/react-dom@18/umd/react-dom.production.min.js`
  - Babel standalone for on-the-fly JSX transpilation in the browser:
    - `https://unpkg.com/@babel/standalone/babel.min.js`
  - Tailwind CSS via CDN: `https://cdn.tailwindcss.com`
- The HTML body contains a single root div: `<div id="root"></div>`.
- A `<script type="text/babel">` block defines and renders the React component `SantaTracker`.

The React app is thus **client-only** and compiled at runtime by Babel; there is no bundler, no NPM-based build, and no static asset pipeline.

### 3.2 Component Logic in `santa-tracker.html`

Key pieces of logic (selected for architecture and flow, not styling):

- State:
  - `userLocation` (lat/lon or null)
  - `locationPermission` ("prompt" | "granted" | "denied")
  - `currentTime` (Date)
  - `santaStats` (status, distance, timeUntil, giftsDelivered, santaLon, santaLat)
  - `santaMessage` (string) and `loadingMessage` (bool)

- Effects:
  - `useEffect` setting up a 1-second timer to update `currentTime`.
  - `useEffect` that recalculates Santa's progress whenever `userLocation` or `currentTime` changes.

- Location acquisition:
  - Uses `navigator.geolocation.getCurrentPosition` when user clicks "Share My Location".
  - On success, updates `userLocation` and sets permission to `granted`.
  - On error, logs error and sets permission to `denied`.

- Santa route and stats calculation:
  - `calculateSantaProgress` computes Santa's status and position based on current time and optional `userLocation`.
  - Uses fixed time window:
    - `christmasEve = Dec 24, 18:00`
    - `christmasDay = Dec 25, 06:00`
  - Derives:
    - `santaLon` in [-180, 180] as Santa moves westward
    - `santaLat` following a wavy sine-based trajectory
    - `status` message (e.g., "Preparing at the North Pole", "Out for delivery!", "Santa has visited your area!", etc.)
    - `giftsDelivered` count up to 2 billion
    - `distance` to user via great-circle distance approximation when `userLocation` set

- **AI message flow (Ollama usage from frontend):**
  - `getSantaMessage` is the key function for backend interaction.
  - On button click:
    1. It constructs `context` based on time and `santaStats`:
       - Before Christmas Eve: prepping at North Pole.
       - During delivery window: mentions current distance and gifts delivered when available.
       - After: Santa resting at North Pole.
    2. Builds an LLM prompt string instructing Santa-like behavior.
    3. Sends a POST request:
       - URL: `"/api/generate"`
       - Method: `POST`
       - Headers: `{ "Content-Type": "application/json" }`
       - Body JSON:
         ```json
         {
           "model": "llama3.2",
           "prompt": "...",
           "stream": false,
           "options": {
             "temperature": 0.8,
             "num_predict": 150
           }
         }
         ```
    4. Expects a JSON response from backend with `data.response` containing the generated text from Ollama.
    5. On success, trims and stores `santaMessage` for display.
    6. On error, logs to console and sets a friendly fallback error message that instructs user to ensure `ollama serve` is running and `llama3.2` is installed.

- **Important:** Note that from the frontend's perspective, the backend base path is **relative** (`/api/generate`), not absolute to `localhost:11434`. This is what allows the Python server to proxy to Ollama transparently.

### 3.3 `santa-tracker.jsx` (Developer Source)

- `santa-tracker.jsx` contains a nearly identical `SantaTracker` React component, but structured as a modern ES module (for use with bundlers or a React toolchain):
  - Imports: `import React, { useState, useEffect } from 'react';`
  - Uses Lucide icons for UI decoration.
  - Exports the component as default.
- Key difference in **Ollama call**:
  - In this JSX source, `getSantaMessage` calls Ollama **directly**:
    ```javascript
    const response = await fetch("http://localhost:11434/api/generate", { ... })
    ```
  - This bypasses the Python proxy and talks straight to Ollama.
- This file is **not referenced** anywhere in `server.py` or `santa-tracker.html` in the current repo structure and, per README, is mainly for developers wanting to integrate or build the app differently.

### 3.4 Frontend Entry vs Root/Index

- Main entrypoint: `http://localhost:8000/santa-tracker.html`
  - Explicitly mentioned in:
    - `README.md` quick start instructions
    - `QUICKSTART.md`
    - `server.py` banner message
- Root URL: `http://localhost:8000/`
  - No custom handling in code.
  - Depends on `SimpleHTTPRequestHandler` default behavior:
    - If there is no `index.html` (current state), accessing `/` typically shows a directory listing or similar server-generated page.
  - There is **no redirection** from `/` to `/santa-tracker.html` implemented currently.

This means the **canonical way** to access the app is by directly navigating to `/santa-tracker.html`; the root is not treated as an app shell.

## 4. Current Request Flow (End-to-End)

### 4.1 Frontend loading

1. User runs `python3 server.py`.
2. Python server starts on `http://localhost:8000` serving static files from repo root.
3. User opens `http://localhost:8000/santa-tracker.html` in the browser.
4. Browser downloads HTML, React/Tailwind/Babel from CDNs, and executes inline JSX script to mount the `SantaTracker` component into `#root`.

### 4.2 Non-AI interactions (tracking UI)

- All Santa tracking logic (time calculations, user location, distance, route animation) is performed **entirely in the browser**.
- These operations require **no backend calls**:
  - Location is accessed via browser geolocation API.
  - Santa's simulated location is computed in client JS.
  - UI state lives exclusively in React state hooks.

### 4.3 AI interaction (message from Santa)

When user clicks "Get a message from Santa":

1. React `onClick` handler calls `getSantaMessage()` in the frontend.
2. `getSantaMessage`:
   - Gathers time and `santaStats` to construct a prompt.
   - Sends an HTTP POST request to the **relative path** `/api/generate` on the same origin (`localhost:8000`).

3. Incoming request at Python server:
   - `CORSRequestHandler.do_POST` sees path `/api/generate`:
     - Reads JSON body from request.
     - Creates a new HTTP request to `http://localhost:11434/api/generate` with identical JSON body.
     - Sends that to Ollama using `urllib.request.urlopen`.

4. Ollama backend:
   - Receives the request on `localhost:11434/api/generate`.
   - Generates response (`{ "response": "...", ... }` or similar shape).
   - Returns JSON to Python server.

5. Python server:
   - Reads Ollama's response body.
   - Responds to browser with:
     - HTTP 200
     - `Content-Type: application/json`
     - The raw JSON from Ollama.

6. Browser:
   - Receives JSON, reads `data.response`, trims it, sets as `santaMessage` state.
   - Renders message in the UI.

7. In case Ollama cannot be reached (e.g., not running):
   - Python returns 502 with JSON error.
   - Frontend `fetch` will throw; catch block logs the error and shows the "frosty connection" fallback message.

### 4.4 CORS and Same-Origin

- Because the browser makes a request to `/api/generate` on the **same origin** it loaded from (`localhost:8000`), CORS issues are avoided at the browser boundary.
- The Python server adds permissive CORS headers (e.g., `Access-Control-Allow-Origin: *`) mainly to support flexibility or non-browser clients; for the main SPA it is not strictly necessary due to same-origin.
- The CORS **problem** would exist if the browser called `http://localhost:11434/api/generate` directly; the Python proxy solves this by acting as a same-origin backend.

## 5. Summary of Key Points (for Future Changes)

- **Ollama backend configuration:**
  - Currently fixed at `http://localhost:11434` in `server.py`.
  - Frontend assumes `/api/generate` and is agnostic to Ollama's actual host/port.
  - `santa-tracker.jsx` bypasses proxy and directly calls `http://localhost:11434`, but this is not used at runtime.

- **Frontend serving model:**
  - Static file server via `SimpleHTTPRequestHandler`.
  - No bundling or routing; main entry file is `santa-tracker.html`.
  - Root path `/` is not wired to the app; users must open `/santa-tracker.html`.

- **Entrypoints:**
  - Backend entrypoint: `python3 server.py` (starts server on `localhost:8000`).
  - Frontend entrypoint URL: `http://localhost:8000/santa-tracker.html`.

- **Request flow:**
  - Browser → `GET /santa-tracker.html` (static file)
  - Browser → `POST /api/generate` for messages
  - Python server → `POST {OLLAMA_URL}/api/generate` (currently `http://localhost:11434`)
  - Response flows back along the reverse path.

This captures the current architecture and behavior, and sets the stage for future work such as:
- Allowing configurable remote Ollama backends instead of hard-coded localhost.
- Introducing a root `/` index that serves the SPA (or redirects to it).
- Potentially moving from inline Babel to a built frontend using `santa-tracker.jsx`.
