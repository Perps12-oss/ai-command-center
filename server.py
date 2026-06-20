"""Simple web server to display AI Command Center project info in Replit."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

README = open("README.md").read()
ARCH = open("docs/ARCHITECTURE.md").read()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Command Center</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0d1117;
    color: #e6edf3;
    min-height: 100vh;
  }
  header {
    background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
    border-bottom: 1px solid #30363d;
    padding: 24px 40px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .logo {
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #58a6ff, #a371f7);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 24px;
  }
  header h1 { font-size: 22px; font-weight: 700; color: #e6edf3; }
  header p { font-size: 13px; color: #8b949e; margin-top: 2px; }
  .badge {
    margin-left: auto;
    background: #1f2d1f;
    color: #3fb950;
    border: 1px solid #238636;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
  }
  .container { max-width: 1100px; margin: 0 auto; padding: 40px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px; }
  .card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
  }
  .card h2 { font-size: 15px; font-weight: 600; color: #58a6ff; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .card p, .card li { font-size: 14px; color: #8b949e; line-height: 1.7; }
  .card ul { padding-left: 20px; }
  .notice {
    background: #1a1a0a;
    border: 1px solid #9e6a03;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 32px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }
  .notice-icon { font-size: 20px; flex-shrink: 0; }
  .notice h3 { font-size: 14px; font-weight: 600; color: #e3b341; margin-bottom: 4px; }
  .notice p { font-size: 13px; color: #8b949e; line-height: 1.6; }
  .arch-flow {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 32px;
  }
  .arch-flow h2 { font-size: 15px; font-weight: 600; color: #58a6ff; margin-bottom: 20px; }
  .flow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .flow-node {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
  }
  .flow-arrow { color: #58a6ff; font-size: 18px; }
  .modules {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
  }
  .modules h2 { font-size: 15px; font-weight: 600; color: #58a6ff; margin-bottom: 16px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px 12px; color: #8b949e; border-bottom: 1px solid #30363d; font-weight: 600; }
  td { padding: 10px 12px; border-bottom: 1px solid #21262d; color: #e6edf3; }
  td:last-child { color: #8b949e; }
  code {
    background: #21262d;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
    font-family: 'Consolas', monospace;
    color: #a371f7;
  }
</style>
</head>
<body>
<header>
  <div class="logo">⌘</div>
  <div>
    <h1>AI Command Center</h1>
    <p>Local AI command surface for Windows ARM64</p>
  </div>
  <span class="badge">Phase 2 — UI</span>
</header>
<div class="container">
  <div class="notice">
    <div class="notice-icon">⚠️</div>
    <div>
      <h3>Desktop Application — Windows ARM64 Only</h3>
      <p>This project is a native desktop app built for Windows on Snapdragon X ARM64 hardware with Ollama running locally. It uses <code>customtkinter</code> for the UI and <code>pywin32</code> for system tray integration. It cannot run directly in a Linux/Replit environment. Use this view to browse the project structure and documentation.</p>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h2>🎯 What It Does</h2>
      <ul>
        <li>Global <strong>Alt+Space</strong> command palette</li>
        <li>Chat with local LLMs via <strong>Ollama</strong></li>
        <li>Obsidian notes integration</li>
        <li>Shell command execution</li>
        <li>System tray with phase-colored status</li>
        <li>SQLite persistence with FTS5 search</li>
      </ul>
    </div>
    <div class="card">
      <h2>🖥️ Target Hardware</h2>
      <ul>
        <li>Lenovo 83N3, Snapdragon X Elite</li>
        <li>16 GB RAM, Windows ARM64</li>
        <li>Native ARM64 Python required</li>
        <li>Ollama installed locally</li>
        <li>DB at <code>%APPDATA%\\AICommandCenter</code></li>
      </ul>
    </div>
    <div class="card">
      <h2>📦 Key Dependencies</h2>
      <ul>
        <li><code>customtkinter</code> — modern Tk UI</li>
        <li><code>aiohttp</code> — async HTTP (Ollama)</li>
        <li><code>pystray</code> — system tray icon</li>
        <li><code>keyboard</code> — global hotkeys</li>
        <li><code>pywin32</code> — Windows APIs</li>
        <li><code>watchdog</code> — file watching</li>
      </ul>
    </div>
    <div class="card">
      <h2>📐 Governance (UCGS v5)</h2>
      <ul>
        <li>Architecture enforcement via YAML config</li>
        <li>Pre-commit hooks + CI gate scripts</li>
        <li>Phase-gated development (0 → 5)</li>
        <li>Wheel audit for ARM64 compatibility</li>
        <li>Currently in <strong>Phase 2</strong> (Command Palette UI)</li>
      </ul>
    </div>
  </div>

  <div class="arch-flow">
    <h2>🔄 Data Flow Architecture</h2>
    <div class="flow">
      <div class="flow-node">UI</div>
      <div class="flow-arrow">→</div>
      <div class="flow-node">EventBus</div>
      <div class="flow-arrow">→</div>
      <div class="flow-node">Services</div>
      <div class="flow-arrow">→</div>
      <div class="flow-node">EventBus</div>
      <div class="flow-arrow">→</div>
      <div class="flow-node">AppState</div>
      <div class="flow-arrow">→</div>
      <div class="flow-node">UI</div>
    </div>
  </div>

  <div class="modules">
    <h2>📁 Core Modules</h2>
    <table>
      <tr><th>Module</th><th>Role</th></tr>
      <tr><td><code>core/event_bus.py</code></td><td>Thread-safe pub/sub system</td></tr>
      <tr><td><code>core/app_state.py</code></td><td>Immutable snapshots + reducers</td></tr>
      <tr><td><code>core/service_manager.py</code></td><td>load() / hibernate() / unload()</td></tr>
      <tr><td><code>core/context_manager.py</code></td><td>Context window management</td></tr>
      <tr><td><code>services/chat_handler_service.py</code></td><td>LLM chat orchestration</td></tr>
      <tr><td><code>services/ollama_service.py</code></td><td>Local Ollama LLM interface</td></tr>
      <tr><td><code>services/obsidian_service.py</code></td><td>Obsidian notes integration</td></tr>
      <tr><td><code>services/shell_tool_service.py</code></td><td>Shell command execution</td></tr>
      <tr><td><code>services/memory_graph_service.py</code></td><td>Knowledge graph memory</td></tr>
      <tr><td><code>ui/app.py</code></td><td>CommandPaletteApp (customtkinter)</td></tr>
      <tr><td><code>ui/tray.py</code></td><td>System tray controller</td></tr>
      <tr><td><code>db/schema.sql</code></td><td>SQLite + FTS5 + V2 hooks</td></tr>
      <tr><td><code>application.py</code></td><td>Bootstrap without UI</td></tr>
    </table>
  </div>
</div>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Serving on http://0.0.0.0:{port}")
    server.serve_forever()
