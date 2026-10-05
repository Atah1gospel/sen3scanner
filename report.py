#!/usr/bin/env python3
"""
report.py - Renders a scan_result.json (from scanner.py) into a self-contained,
dark-themed HTML dashboard.

Usage:
    python3 report.py scan_result.json
    python3 report.py scan_result.json --out dashboard.html
"""

import argparse
import json
import math

SEVERITY_COLOR = {
    "critical": "#E5484D",
    "high": "#F2A65A",
    "medium": "#F2C94C",
    "low": "#4FC8E0",
    "info": "#5FD3A0",
}
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


def gauge_svg(score, grade):
    """Draws a semicircular gauge arc representing the score out of 100."""
    radius = 90
    cx, cy = 110, 110
    start_angle = math.pi
    end_angle = math.pi - (score / 100) * math.pi
    x1 = cx + radius * math.cos(start_angle)
    y1 = cy + radius * math.sin(start_angle)
    x2 = cx + radius * math.cos(end_angle)
    y2 = cy + radius * math.sin(end_angle)
    large_arc = 1 if (score / 100) * 180 > 180 else 0
    color = "#5FD3A0" if score >= 75 else "#F2A65A" if score >= 50 else "#E5484D"

    return f"""
    <svg width="220" height="130" viewBox="0 0 220 130">
      <path d="M 20 110 A 90 90 0 0 1 200 110" fill="none" stroke="#232B3D" stroke-width="14" stroke-linecap="round"/>
      <path d="M {x1:.1f} {y1:.1f} A {radius} {radius} 0 {large_arc} 1 {x2:.1f} {y2:.1f}"
            fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round"/>
      <text x="110" y="95" text-anchor="middle" font-size="42" font-weight="700" fill="#E8ECF1" font-family="'JetBrains Mono', monospace">{score}</text>
      <text x="110" y="118" text-anchor="middle" font-size="13" fill="#8993A8" letter-spacing="1">out of 100</text>
    </svg>
    """


def severity_bar(findings):
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    total = max(sum(counts.values()), 1)

    segments = ""
    x = 0
    for s in SEVERITY_ORDER:
        w = (counts[s] / total) * 100
        if w > 0:
            segments += f'<rect x="{x:.2f}%" y="0" width="{w:.2f}%" height="100%" fill="{SEVERITY_COLOR[s]}"/>'
            x += w

    legend = "".join(
        f'<span class="legend-item"><span class="dot" style="background:{SEVERITY_COLOR[s]}"></span>{s.title()} ({counts[s]})</span>'
        for s in SEVERITY_ORDER if counts[s] > 0
    )
    return f"""
    <svg width="100%" height="14" style="border-radius:7px;overflow:hidden;display:block;margin-bottom:14px;">{segments}</svg>
    <div class="legend">{legend}</div>
    """


def findings_html(findings):
    if not findings:
        return '<p class="muted">No findings recorded.</p>'
    rows = ""
    for f in findings:
        color = SEVERITY_COLOR.get(f["severity"], "#8993A8")
        rows += f"""
        <div class="finding" style="border-left-color:{color}">
          <div class="finding-head">
            <span class="sev-tag" style="background:{color}22;color:{color}">{f['severity']}</span>
            <span class="finding-title">{f['title']}</span>
          </div>
          <p class="finding-detail">{f['detail']}</p>
        </div>
        """
    return rows


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SentryScan — {target}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0E1420;
    --panel: #161D2B;
    --border: #232B3D;
    --text: #E8ECF1;
    --muted: #8993A8;
    --amber: #F2A65A;
    --cyan: #4FC8E0;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', -apple-system, sans-serif;
    padding: 40px 20px;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  .top {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 28px;
  }}
  .brand {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--cyan);
    letter-spacing: 2px;
    margin-bottom: 6px;
  }}
  h1 {{
    font-size: 28px;
    margin: 0;
    font-weight: 700;
    word-break: break-all;
  }}
  .meta {{ color: var(--muted); font-size: 13px; margin-top: 6px; font-family: 'JetBrains Mono', monospace; }}
  .grade-badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 46px;
    font-weight: 700;
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 14px;
    background: var(--panel);
    border: 1px solid var(--border);
    color: var(--amber);
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 20px;
  }}
  .gauge-row {{ display: flex; align-items: center; gap: 28px; flex-wrap: wrap; }}
  .gauge-row .stat-label {{ color: var(--muted); font-size: 13px; }}
  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--muted); font-family: 'JetBrains Mono', monospace; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
  .finding {{
    border-left: 3px solid;
    padding: 12px 16px;
    background: #10151F;
    border-radius: 0 8px 8px 0;
    margin-bottom: 10px;
  }}
  .finding-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
  .sev-tag {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    padding: 2px 8px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .finding-title {{ font-weight: 600; font-size: 14px; }}
  .finding-detail {{ margin: 0; color: var(--muted); font-size: 13px; }}
  .section-title {{ font-size: 14px; color: var(--muted); margin: 0 0 14px 0; font-family: 'JetBrains Mono', monospace; letter-spacing: 1px; }}
  .muted {{ color: var(--muted); }}
</style>
</head>
<body>
  <div class="wrap">
    <div class="top">
      <div>
        <div class="brand">SENTRYSCAN</div>
        <h1>{target}</h1>
        <div class="meta">Scanned {scanned_at} · HTTP {http_status}</div>
      </div>
      <div class="grade-badge">{grade}</div>
    </div>

    <div class="card">
      <p class="section-title">POSTURE SCORE</p>
      <div class="gauge-row">
        {gauge}
        <div>
          <div class="stat-label">{finding_count} findings across {sev_count} severity levels</div>
        </div>
      </div>
    </div>

    <div class="card">
      <p class="section-title">SEVERITY BREAKDOWN</p>
      {sev_bar}
    </div>

    <div class="card">
      <p class="section-title">FINDINGS</p>
      {findings}
    </div>
  </div>
</body>
</html>
"""


def build_report(data):
    findings = data.get("findings", [])
    sev_present = len(set(f["severity"] for f in findings))
    return TEMPLATE.format(
        target=data.get("target", "unknown"),
        scanned_at=data.get("scanned_at", ""),
        http_status=data.get("http_status", "—"),
        grade=data.get("grade", "?"),
        gauge=gauge_svg(data.get("score", 0), data.get("grade", "?")),
        finding_count=len(findings),
        sev_count=sev_present,
        sev_bar=severity_bar(findings),
        findings=findings_html(findings),
    )


def main():
    parser = argparse.ArgumentParser(description="Render SentryScan JSON as an HTML dashboard")
    parser.add_argument("json_file", help="Path to scan_result.json")
    parser.add_argument("--out", default="dashboard.html", help="Output HTML path")
    args = parser.parse_args()

    with open(args.json_file) as f:
        data = json.load(f)

    html = build_report(data)
    with open(args.out, "w") as f:
        f.write(html)

    print(f"[+] Dashboard written to {args.out}")


if __name__ == "__main__":
    main()
