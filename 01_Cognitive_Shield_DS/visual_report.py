import html
from pathlib import Path
from typing import Any, Dict, List

from scenario_runner import run_all_scenarios


REPORT_PATH = Path(__file__).resolve().parent / "visual_report.html"


def render_status_chip(label: str, value: str, tone: str) -> str:
    return (
        f'<span class="chip {tone}">'
        f'<span>{html.escape(label)}</span>'
        f'<strong>{html.escape(value)}</strong>'
        "</span>"
    )


def render_lineage(lineage: List[str]) -> str:
    if not lineage:
        return '<p class="muted">No Context Graph lineage recorded.</p>'

    nodes = []
    for index, node_id in enumerate(lineage):
        nodes.append(f'<span class="lineage-node">{html.escape(node_id)}</span>')
        if index < len(lineage) - 1:
            nodes.append('<span class="lineage-arrow">-></span>')
    return f'<div class="lineage">{"".join(nodes)}</div>'


def render_failed_tools(failed_tools: List[Dict[str, Any]]) -> str:
    if not failed_tools:
        return '<p class="muted">No failed tools.</p>'

    rows = []
    for item in failed_tools:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('tool', 'unknown_tool')))}</td>"
            f"<td>{html.escape(str(item.get('error', 'unknown_error')))}</td>"
            "</tr>"
        )
    return (
        '<table><thead><tr><th>Tool</th><th>Error</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_action_list(actions: List[str]) -> str:
    if not actions:
        return '<p class="muted">No attempted actions.</p>'
    return "<ul>" + "".join(f"<li>{html.escape(action)}</li>" for action in actions) + "</ul>"


def render_scenario_card(result: Dict[str, Any]) -> str:
    assessment = result["assessment"]
    freshness = assessment["freshness"]
    failure_budget = assessment["failure_budget"]
    artifact_fold = assessment["artifact_ledger_fold"]
    replay_summary = assessment["replay_summary"]

    is_fresh = freshness["is_fresh"]
    breached = failure_budget["budget_breached"]
    mode = failure_budget["autonomy_mode"]

    card_tone = "risk" if breached or not is_fresh else "healthy"
    fresh_tone = "ok" if is_fresh else "warn"
    budget_tone = "warn" if breached else "ok"
    mode_tone = "warn" if mode != "active" else "ok"

    chips = [
        render_status_chip("Fresh", str(is_fresh), fresh_tone),
        render_status_chip("Budget", "breached" if breached else "inside", budget_tone),
        render_status_chip("Mode", mode, mode_tone),
        render_status_chip("Next", failure_budget["next_safe_action"], mode_tone),
    ]

    failure_reasons = replay_summary["failure_reasons"]
    reason_html = (
        "<ul>" + "".join(f"<li>{html.escape(reason)}</li>" for reason in failure_reasons) + "</ul>"
        if failure_reasons
        else '<p class="muted">No blocking failure reasons.</p>'
    )

    return f"""
    <section class="scenario-card {card_tone}">
      <header>
        <div>
          <p class="eyebrow">{html.escape(result["scenario_id"])}</p>
          <h2>{html.escape(result["title"])}</h2>
          <p>{html.escape(result["description"])}</p>
        </div>
        <div class="chips">{''.join(chips)}</div>
      </header>
      <div class="grid">
        <div>
          <h3>Replay Summary</h3>
          <p class="replay-copy">{html.escape(replay_summary["summary"])}</p>
        </div>
        <div>
          <h3>Context Hashes</h3>
          <dl>
            <dt>Current</dt>
            <dd>{html.escape(freshness["current_context_hash"])}</dd>
            <dt>Evidence Ledger</dt>
            <dd>{html.escape(freshness["ledger_context_hash"])}</dd>
          </dl>
        </div>
        <div>
          <h3>Context Lineage</h3>
          {render_lineage(replay_summary["context_lineage"])}
        </div>
        <div>
          <h3>Attempted Actions</h3>
          {render_action_list(artifact_fold["attempted_actions"])}
        </div>
        <div>
          <h3>Failed Tools</h3>
          {render_failed_tools(artifact_fold["failed_tools"])}
        </div>
        <div>
          <h3>Failure Reasons</h3>
          {reason_html}
        </div>
      </div>
    </section>
    """


def build_report(results: List[Dict[str, Any]]) -> str:
    total = len(results)
    breached = sum(1 for result in results if result["assessment"]["failure_budget"]["budget_breached"])
    stale = sum(1 for result in results if not result["assessment"]["freshness"]["is_fresh"])
    conservative = sum(
        1
        for result in results
        if result["assessment"]["failure_budget"]["autonomy_mode"] != "active"
    )

    cards = "\n".join(render_scenario_card(result) for result in results)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cognitive Shield DS Visual Report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #18202a;
      --muted: #637083;
      --line: #d9e0e8;
      --surface: #ffffff;
      --page: #f4f7fb;
      --ok: #147a55;
      --ok-bg: #e4f5ed;
      --ok-soft: #f3fbf7;
      --warn: #a33c12;
      --warn-bg: #fff0e8;
      --warn-soft: #fff8f4;
      --accent: #2457a6;
      --accent-bg: #e8f0ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    .topbar {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: end;
      margin-bottom: 24px;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ font-size: 32px; margin-bottom: 8px; }}
    h2 {{ font-size: 22px; margin-bottom: 6px; }}
    h3 {{ font-size: 14px; margin-bottom: 10px; text-transform: uppercase; color: var(--muted); }}
    p {{ overflow-wrap: anywhere; }}
    .summary-strip {{
      display: grid;
      grid-template-columns: repeat(4, minmax(120px, 1fr));
      gap: 10px;
      margin-bottom: 18px;
    }}
    .metric, .scenario-card {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 14px;
      border-top: 4px solid var(--accent);
    }}
    .metric:nth-child(2), .metric:nth-child(3), .metric:nth-child(4) {{
      border-top-color: var(--warn);
    }}
    .metric strong {{ display: block; font-size: 28px; line-height: 1; margin-bottom: 6px; }}
    .metric span, .muted, .eyebrow {{ color: var(--muted); }}
    .scenario-card {{
      position: relative;
      overflow: hidden;
      padding: 18px;
      margin-top: 14px;
      border-left: 8px solid var(--ok);
      box-shadow: 0 10px 28px rgba(24, 32, 42, 0.07);
    }}
    .scenario-card.healthy {{ background: linear-gradient(90deg, var(--ok-soft), var(--surface) 22%); }}
    .scenario-card.risk {{
      background: linear-gradient(90deg, var(--warn-soft), var(--surface) 24%);
      border-left-color: var(--warn);
    }}
    .scenario-card header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: start;
      border-bottom: 1px solid var(--line);
      padding-bottom: 14px;
      margin-bottom: 16px;
    }}
    .eyebrow {{
      margin-bottom: 4px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
      font-weight: 700;
    }}
    .chips {{
      display: grid;
      grid-template-columns: repeat(2, minmax(120px, 1fr));
      gap: 8px;
      width: min(430px, 100%);
    }}
    .chip {{
      display: grid;
      gap: 2px;
      padding: 9px 10px;
      border-radius: 8px;
      font-size: 13px;
      border: 1px solid var(--line);
      min-width: 0;
    }}
    .chip span {{
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      color: inherit;
      opacity: 0.78;
    }}
    .chip strong {{
      overflow-wrap: anywhere;
      line-height: 1.2;
    }}
    .chip.ok {{ background: var(--ok-bg); color: var(--ok); border-color: #afd9c4; }}
    .chip.warn {{ background: var(--warn-bg); color: var(--warn); border-color: #f1c6b2; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    .grid > div {{
      min-width: 0;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
    }}
    .grid > div:first-child {{
      grid-column: 1 / -1;
      background: #f8fbff;
      border-color: #c9d8ed;
    }}
    .replay-copy {{
      margin-bottom: 0;
      font-size: 16px;
      font-weight: 650;
    }}
    dl {{ margin: 0; }}
    dt {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    dd {{
      margin: 2px 0 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      overflow-wrap: anywhere;
      font-size: 12px;
    }}
    ul {{ margin: 0; padding-left: 20px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 8px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    .lineage {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }}
    .lineage-node {{
      padding: 7px 9px;
      border: 1px solid #b8c7dc;
      background: var(--accent-bg);
      color: var(--accent);
      border-radius: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    .lineage-arrow {{ color: var(--muted); }}
    @media (max-width: 780px) {{
      main {{ width: min(100% - 20px, 1180px); padding-top: 20px; }}
      .topbar, .scenario-card header, .grid, .summary-strip {{ grid-template-columns: 1fr; }}
      .chips {{ grid-template-columns: 1fr; width: 100%; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="topbar">
      <div>
        <h1>Cognitive Shield DS Visual Report</h1>
        <p class="muted">Fixture-backed view of Context Hash freshness, Failure Budget directives, Context Graph lineage, Artifact Ledger Folds, and Replay Summaries.</p>
      </div>
    </section>
    <section class="summary-strip">
      <div class="metric"><strong>{total}</strong><span>Scenarios</span></div>
      <div class="metric"><strong>{stale}</strong><span>Stale Context</span></div>
      <div class="metric"><strong>{breached}</strong><span>Budget Breaches</span></div>
      <div class="metric"><strong>{conservative}</strong><span>Conservative Mode</span></div>
    </section>
    {cards}
  </main>
</body>
</html>
"""


def write_report(path: Path = REPORT_PATH) -> Path:
    path.write_text(build_report(run_all_scenarios()), encoding="utf-8")
    return path


if __name__ == "__main__":
    output_path = write_report()
    print(output_path)
