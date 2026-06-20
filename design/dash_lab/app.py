"""
Dash visual lab — Live Command Center reference (Phase A).
Run: python design/dash_lab/app.py
"""

from __future__ import annotations

import json
from pathlib import Path

from dash import Dash, Input, Output, dcc, html

_ROOT = Path(__file__).resolve().parents[1]
_STYLE = json.loads((_ROOT / "STYLE_LOCK.json").read_text(encoding="utf-8"))
_PAL = _STYLE["palette"]
_LAY = _STYLE["layout"]

app = Dash(__name__)
app.title = "AI Command Center — Visual Lab"

app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="/assets/styles.css">
    </head>
    <body>
        {%app_entry%}
        <footer>{%config%}{%scripts%}{%renderer%}</footer>
    </body>
</html>"""

app.layout = html.Div(
    className="shell",
    style={"backgroundColor": _PAL["bg_deep"]},
    children=[
        html.Div(
            className="header",
            children=[
                html.Div("◇ AI Command Center", className="logo"),
                html.Div(
                    [
                        html.Div("llama3.2:3b", className="model"),
                        html.Div("Local Ollama", className="provider"),
                    ],
                    className="center",
                ),
                html.Div(
                    [
                        html.Span("● Connected", className="pill ready"),
                        html.Span("Alt+Space", className="hint"),
                    ],
                    className="actions",
                ),
            ],
        ),
        html.Div(
            className="body-row",
            children=[
                html.Div(
                    className="sidebar",
                    children=[
                        html.Div("AI Assistant", className="sidebar-title"),
                        *[html.Div(label, className="nav-item" + (" active" if i == 0 else ""))
                          for i, label in enumerate(
                              ["Home", "Chat", "Notes", "System", "Plugins", "Settings"]
                          )],
                        html.Div("Local User", className="user-chip"),
                    ],
                ),
                html.Div(
                    className="main",
                    children=[
                        html.Div(
                            id="hero",
                            className="hero-panel",
                            children=[
                                html.Div(
                                    className="battery",
                                    children=[
                                        html.Div(className="segment"),
                                        html.Div(className="segment"),
                                        html.Div(className="segment"),
                                    ],
                                ),
                                html.Div(
                                    "ARTIFICIAL INTELLIGENCE",
                                    className="hero-title",
                                ),
                            ],
                        ),
                        html.Div("Home", className="page-title"),
                        html.Div(
                            "System overview and recent activity",
                            className="page-subtitle",
                        ),
                        html.Div(
                            className="grid-2x2",
                            children=[
                                html.Div(f"Card {n}", className="metric-card")
                                for n in ("System Status", "Usage", "Knowledge", "Plugins")
                            ],
                        ),
                        dcc.Interval(id="tick", interval=1200, n_intervals=0),
                        html.Div(id="stream", className="stream"),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    Output("hero", "className"),
    Output("stream", "children"),
    Input("tick", "n_intervals"),
)
def animate(n: int):
    glow = "hero-panel glow" if n % 2 == 0 else "hero-panel"
    events = [f"› telemetry.tick #{n}", f"› system.snapshot cpu={20 + n % 40}%"]
    return glow, [html.Div(e, className="stream-line") for e in events]


if __name__ == "__main__":
    app.run(debug=True, port=8050)
