#!/usr/bin/env python3
"""
Simple HTTP server for Santa Tracker with Ollama proxy
Run this to serve the app and avoid CORS issues with Ollama
"""

import http.server
import socketserver
import os
import json
import urllib.request
import urllib.error

PORT = 8000
OLLAMA_URL = "http://localhost:11434"

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def do_POST(self):
        # Proxy Ollama requests
        if self.path.startswith('/api/'):
            try:
                # Read the request body
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                # Forward to Ollama
                req = urllib.request.Request(
                    f"{OLLAMA_URL}{self.path}",
                    data=post_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req) as response:
                    response_data = response.read()
                    
                    # Send response back with CORS headers
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response_data)
                    
            except urllib.error.URLError as e:
                self.send_response(502)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_msg = json.dumps({"error": f"Ollama not available: {str(e)}"})
                self.wfile.write(error_msg.encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    # Change to the directory containing this script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"""
╔══════════════════════════════════════════════════════════╗
║           🎅 Santa Tracker Server Started! 🎄           ║
╚══════════════════════════════════════════════════════════╝

  ✨ Server running at: http://localhost:{PORT}
  
  📂 Open in your browser: http://localhost:{PORT}/santa-tracker.html
  
  🛑 Press Ctrl+C to stop the server
  
  📝 This server proxies Ollama requests to avoid CORS issues!
     Just make sure Ollama is running (it should be already)

""")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🎅 Ho ho ho! Server stopped. Merry Christmas! 🎄\n")
