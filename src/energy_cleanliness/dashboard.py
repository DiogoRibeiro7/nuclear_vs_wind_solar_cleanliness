"""Build a self-contained static HTML dashboard from a structured report.

The dashboard consumes ``reports/multimetric_report.json`` (the versioned report
produced by :mod:`energy_cleanliness.reporting`) and renders a single portable HTML
file with scenario tabs, ranking tables, embedded figures and a standard model-risk
section. It has no runtime dependency beyond a browser: figures are base64-embedded
and styling/interactivity are inlined, so the output can be opened or hosted as-is.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path

from energy_cleanliness.model_risk import GENERAL_RISKS, MULTIMETRIC_RISKS

SCENARIO_BLURBS = {
    "balanced": "Equal weight on every metric.",
    "low_emissions_first": "Heavily weights lifecycle carbon and air-pollution deaths.",
    "low_cost_first": "Heavily weights levelized cost and financing risk.",
    "high_reliability_first": "Heavily weights capacity factor and grid integration.",
}

_CSS = """
:root { --bg:#0f1115; --card:#181b22; --ink:#e8eaed; --muted:#9aa0aa;
  --accent:#4c72b0; --good:#55a868; --warn:#dd8452; --line:#2a2e37; }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:15px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; }
.wrap { max-width:1040px; margin:0 auto; padding:32px 20px 64px; }
h1 { font-size:26px; margin:0 0 6px; }
h2 { font-size:20px; margin:32px 0 12px; border-bottom:1px solid var(--line); padding-bottom:6px; }
h3 { font-size:16px; margin:18px 0 8px; }
.muted { color:var(--muted); }
.meta { color:var(--muted); font-size:13px; margin-bottom:8px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:16px 18px; margin:14px 0; }
.tabs { display:flex; flex-wrap:wrap; gap:8px; margin:16px 0 4px; }
.tab { background:var(--card); border:1px solid var(--line); color:var(--ink);
  padding:8px 14px; border-radius:999px; cursor:pointer; font-size:14px; }
.tab.active { background:var(--accent); border-color:var(--accent); color:#fff; }
.panel { display:none; }
.panel.active { display:block; }
.lead { background:rgba(76,114,176,.14); border-left:3px solid var(--accent);
  padding:10px 14px; border-radius:6px; margin:10px 0; }
table { width:100%; border-collapse:collapse; margin:10px 0; font-size:14px; }
th, td { text-align:left; padding:7px 10px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.figs { display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-top:12px; }
.figs img { width:100%; border-radius:8px; background:#fff; }
@media (max-width:780px){ .figs{ grid-template-columns:1fr; } }
.pill { display:inline-block; background:var(--line); color:var(--ink);
  padding:2px 9px; border-radius:999px; font-size:12px; margin:2px 4px 2px 0; }
.risk li { margin:4px 0; }
footer { color:var(--muted); font-size:13px; margin-top:36px; }
a { color:#7aa2d6; }
"""

_JS = """
function showScenario(id, btn){
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.getElementById('panel-'+id).classList.add('active');
  btn.classList.add('active');
}
"""

# Shared, single-source-of-truth caveats (see energy_cleanliness.model_risk).
MODEL_RISKS = GENERAL_RISKS + MULTIMETRIC_RISKS


def _encode_png(path: str | Path) -> str:
    raw = Path(path).read_bytes()
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def _fmt(value: float, places: int = 3) -> str:
    return f"{float(value):.{places}f}"


def _scenario_table(score_summary: list[dict], rank_stability: list[dict]) -> str:
    stability = {row["technology"]: row for row in rank_stability}
    ordered = sorted(score_summary, key=lambda r: r["mean_score"], reverse=True)
    rows = []
    for row in ordered:
        tech = row["technology"]
        st = stability.get(tech, {})
        rows.append(
            "<tr>"
            f"<td>{html.escape(tech)}</td>"
            f"<td class='num'>{_fmt(row['mean_score'])}</td>"
            f"<td class='num'>[{_fmt(row['ci_low'])}, {_fmt(row['ci_high'])}]</td>"
            f"<td class='num'>{_fmt(st.get('p_top1', 0), 2)}</td>"
            f"<td class='num'>{_fmt(st.get('p_top3', 0), 2)}</td>"
            "</tr>"
        )
    head = (
        "<table><thead><tr>"
        "<th>Technology</th><th class='num'>Mean score</th><th class='num'>95% CI</th>"
        "<th class='num'>P(rank 1)</th><th class='num'>P(top 3)</th>"
        "</tr></thead><tbody>"
    )
    return head + "".join(rows) + "</tbody></table>"


def build_dashboard_html(report: dict, figures: dict[str, dict[str, str]]) -> str:
    """Render the dashboard HTML string.

    ``figures`` maps scenario name to ``{"scores": <png path>, "rank": <png path>}``.
    """
    method = report["method"]
    scenarios = report["scenarios"]
    names = list(scenarios)

    tab_parts = []
    for i, name in enumerate(names):
        active = " active" if i == 0 else ""
        safe = html.escape(name)
        tab_parts.append(
            f"<button class='tab{active}' onclick=\"showScenario('{name}', this)\">"
            f"{safe}</button>"
        )
    tabs = "".join(tab_parts)

    panels = []
    for i, name in enumerate(names):
        active = " active" if i == 0 else ""
        scenario = scenarios[name]
        ordered = sorted(scenario["score_summary"], key=lambda r: r["mean_score"], reverse=True)
        leader = ordered[0]["technology"]
        stability = {r["technology"]: r for r in scenario["rank_stability"]}
        p1 = stability.get(leader, {}).get("p_top1", 0.0)
        blurb = SCENARIO_BLURBS.get(name, "")
        fig = figures.get(name, {})
        fig_block = ""
        if fig.get("scores") and fig.get("rank"):
            fig_block = (
                "<div class='figs'>"
                f"<img alt='scores' src='{_encode_png(fig['scores'])}'>"
                f"<img alt='rank stability' src='{_encode_png(fig['rank'])}'>"
                "</div>"
            )
        table = _scenario_table(scenario["score_summary"], scenario["rank_stability"])
        panels.append(
            f"<div class='panel{active}' id='panel-{name}'>"
            f"<p class='muted'>{html.escape(blurb)}</p>"
            f"<div class='lead'>Leader: <strong>{html.escape(leader)}</strong> "
            f"&mdash; rank 1 in {float(p1) * 100:.0f}% of Monte Carlo draws.</div>"
            f"{table}"
            f"{fig_block}"
            "</div>"
        )

    best = report["best_by_metric"]
    best_rows = "".join(
        f"<tr><td>{html.escape(metric)}</td><td>{html.escape(tech)}</td></tr>"
        for metric, tech in sorted(best.items())
    )
    pareto_pills = "".join(
        f"<span class='pill'>{html.escape(t)}</span>" for t in report["pareto_frontier"]
    )
    risk_items = "".join(f"<li>{html.escape(r)}</li>" for r in MODEL_RISKS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Energy cleanliness dashboard</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>Energy cleanliness dashboard</h1>
  <p class="meta">Multi-metric comparison of nuclear, wind and solar &mdash;
    no universal winner.</p>
  <p class="meta">
    Report schema {html.escape(str(report["report_schema_version"]))} &middot;
    dataset schema {html.escape(str(report["dataset_schema_version"]))} &middot;
    {method["uncertainty"]} &middot;
    {int(method["samples"])} draws &middot; seed {int(method["seed"])}
  </p>

  <h2>By policy scenario</h2>
  <p class="muted">Each scenario weights the twelve metrics differently. Switch tabs to
  see how the cleanest technology changes with the policy intent.</p>
  <div class="tabs">{tabs}</div>
  {''.join(panels)}

  <h2>Pareto frontier</h2>
  <div class="card">
    <p class="muted">Technologies never beaten on all metrics at once:</p>
    {pareto_pills}
  </div>

  <h2>Best technology per metric</h2>
  <div class="card">
    <table><thead><tr><th>Metric</th><th>Best</th></tr></thead>
    <tbody>{best_rows}</tbody></table>
  </div>

  <h2>Model risk &amp; limitations</h2>
  <div class="card risk"><ul>{risk_items}</ul></div>

  <footer>
    Generated from <code>reports/multimetric_report.json</code>.
    See <a href="../docs/methods_note.md">methods note</a>,
    <a href="../data/data_sources.md">data sources</a> and
    <a href="../docs/claim_to_evidence.md">claim-to-evidence map</a>.
  </footer>
</div>
<script>{_JS}</script>
</body>
</html>
"""


def write_dashboard(
    report: dict, figures: dict[str, dict[str, str]], output_path: str | Path
) -> Path:
    """Write the dashboard HTML to ``output_path`` and return the path."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_dashboard_html(report, figures), encoding="utf-8")
    return destination
