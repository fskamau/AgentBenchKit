"""JSON / Markdown / escaped HTML report generation from real evaluation objects."""

import html
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def report_markdown(report: BaseModel) -> str:
    data = report.model_dump(mode="json")
    if "dimension_scores" in data:
        lines = [f"# Agent trajectory evaluation: {data['task_id']}", "",
                 f"**Observable score:** {data['total_score']}/100", "",
                 "Unobservable dimensions are excluded from the numerical aggregate.", "",
                 "## Dimension scores", ""]
        lines += [f"- **{key}**: {value if value is not None else 'human review required'}"
                  for key, value in data["dimension_scores"].items()]
        lines += ["", "## Evidence-linked findings", ""]
        for finding in data["findings"]:
            lines.append(f"- **{finding['dimension']} / {finding['severity']}** "
                         f"(events: {', '.join(finding['evidence_ids'])}): "
                         f"{finding['message']} [deduction={finding['deduction']}]")
    elif "classification" in data:
        lines = [f"# Patch evaluation: {data['case_id']}", "",
                 f"**Classification:** {data['classification']}", "",
                 f"**Engine:** {data['engine']}", "",
                 f"**Patch SHA-256:** `{data['patch_sha256']}`", "",
                 "## Tests", ""]
        for key in ("baseline", "patched", "oracle"):
            item = data.get(key)
            lines.append(f"- **{key}**: {item['classification'] if item else 'not run'}")
        lines += ["", "## Evidence", ""]
        lines += [f"- {line}" for line in data["evidence"]]
        if data["application_error"]:
            lines += ["", f"**Patch application error:** {data['application_error']}"]
        if data.get("edge_case_results"):
            lines += ["", "## Edge-case checklist", ""]
            lines += [f"- {name}: {status}" for name, status in data["edge_case_results"].items()]
        lines += ["", "## Modified files", ""]
        lines += [f"- `{name}`" for name in data["changed_files"]]
    else:
        lines = ["# Evaluation report", "", "```json", json.dumps(data, indent=2), "```"]
    return "\n".join(lines) + "\n"


def report_html(report: BaseModel) -> str:
    """Render a readable report; escape all evidence originating from logs/diffs."""
    data = report.model_dump(mode="json")
    esc = lambda value: html.escape(str(value), quote=True)
    styles = ("body{font:15px/1.55 system-ui,sans-serif;max-width:1020px;"
              "margin:3rem auto;padding:0 1.4rem;color:#24282c;background:#fff}"
              "header{border-bottom:2px solid #27364c;padding-bottom:1rem;margin-bottom:1.5rem}"
              "h1{font-size:1.8rem}h2{font-size:1.1rem;margin-top:2rem}"
              "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:.65rem;"
              "border-bottom:1px solid #ddd;vertical-align:top}th{background:#f1f3f5}"
              "code,pre{font:12px/1.55 ui-monospace,monospace}pre{white-space:pre-wrap;"
              "overflow-wrap:anywhere;background:#f5f6f8;padding:1rem}"
              "li{margin:.55rem 0}small{color:#565b62}details{margin:.6rem 0}"
              "@media print{body{margin:1rem}details{display:block}}")
    out = ["<!doctype html><html lang='en'><head><meta charset='utf-8'>",
           "<meta name='viewport' content='width=device-width,initial-scale=1'>",
           "<title>AgentBenchKit evaluation report</title><style>", styles,
           "</style></head><body><main>"]
    if "dimension_scores" in data:
        out += [f"<header><h1>Trajectory evaluation: {esc(data['task_id'])}</h1>",
                f"<p><strong>Observable score:</strong> {esc(data['total_score'])}/100</p>",
                "<small>Semantic correctness is excluded when it cannot be observed.</small></header>",
                "<h2>Rubric dimensions</h2><table><thead><tr><th>Dimension</th>"
                "<th>Observable score</th></tr></thead><tbody>"]
        for dimension, value in data["dimension_scores"].items():
            rendered = value if value is not None else "human review required"
            out.append(f"<tr><td>{esc(dimension)}</td><td>{esc(rendered)}</td></tr>")
        out += ["</tbody></table><h2>Evidence-linked findings</h2><ol>"]
        for finding in data["findings"]:
            out.append(f"<li><strong>{esc(finding['dimension'])} / {esc(finding['severity'])}</strong>: "
                       f"{esc(finding['message'])} <small>Event IDs: "
                       f"{esc(', '.join(finding['evidence_ids']))}; "
                       f"deduction: {esc(finding['deduction'])}</small></li>")
        out.append("</ol>")
    elif "classification" in data:
        out += [f"<header><h1>Patch evaluation: {esc(data['case_id'])}</h1>",
                f"<p><strong>Classification:</strong> {esc(data['classification'])}</p>",
                f"<small>Engine: {esc(data['engine'])} · SHA256: "
                f"<code>{esc(data['patch_sha256'])}</code></small></header>",
                "<h2>Test outcomes</h2><table><thead><tr><th>Stage</th><th>Status</th>"
                "<th>Failed tests</th></tr></thead><tbody>"]
        for stage in ("baseline", "patched", "oracle"):
            result = data.get(stage)
            if result:
                failed = ", ".join(result["failed_tests"]) or "—"
                out.append(f"<tr><td>{esc(stage)}</td><td>{esc(result['classification'])}</td>"
                           f"<td>{esc(failed)}</td></tr>")
            else:
                out.append(f"<tr><td>{esc(stage)}</td><td>not run</td><td>—</td></tr>")
        out += ["</tbody></table><h2>Evidence</h2><ul>"]
        out += [f"<li>{esc(line)}</li>" for line in data["evidence"]]
        out.append("</ul>")
        if data.get("edge_case_results"):
            out.append("<h2>Independent edge-case checklist</h2><ul>")
            out += [f"<li><code>{esc(name)}</code>: {esc(status)}</li>"
                    for name, status in data["edge_case_results"].items()]
            out.append("</ul>")
        if data.get("application_error"):
            out.append(f"<h2>Patch application error</h2><pre>{esc(data['application_error'])}</pre>")
        out.append("<h2>Changed files</h2><ul>")
        out += [f"<li><code>{esc(name)}</code></li>" for name in data["changed_files"]]
        out.append("</ul><h2>Raw test evidence</h2>")
        for stage in ("baseline", "patched", "oracle"):
            result = data.get(stage)
            if not result:
                continue
            process = result["process"]
            out.append(f"<details><summary>{esc(stage)} — exit {esc(process['exit_code'])}"
                       f"; duration {esc(process['duration_seconds'])}s</summary>"
                       f"<pre>{esc(process['stdout'] + chr(10) + process['stderr'])}</pre></details>")
    else:
        out.append(f"<pre>{esc(json.dumps(data, indent=2))}</pre>")
    out.append("</main></body></html>\n")
    return "".join(out)


def write_reports(report: BaseModel, prefix: Path) -> list[Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_out = prefix.with_suffix(".json")
    md_out = prefix.with_suffix(".md")
    html_out = prefix.with_suffix(".html")
    json_out.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown = report_markdown(report)
    md_out.write_text(markdown, encoding="utf-8")
    html_out.write_text(report_html(report), encoding="utf-8")
    return [json_out, md_out, html_out]


def compare_evaluations(paths: list[Path]) -> dict[str, Any]:
    """Compare only compatible trajectory reports; no invented scoring conversion."""
    if len(paths) < 2:
        raise ValueError("Comparison requires at least two reports")
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    kinds = {"trajectory" if "dimension_scores" in x else
             "patch" if "classification" in x else "unknown" for x in reports}
    if len(kinds) != 1 or "unknown" in kinds:
        raise ValueError("Cannot compare incompatible evaluation schemas")
    if "trajectory" in kinds:
        entries = [{"source": str(path), "task_id": data["task_id"],
                    "observable_score": data["total_score"],
                    "dimensions": data["dimension_scores"],
                    "review_required": data["review_required"]}
                   for path, data in zip(paths, reports, strict=True)]
        if len({e["task_id"] for e in entries}) != 1:
            raise ValueError("All attempts must belong to the same task")
        return {"kind": "trajectory", "attempts": entries,
                "ranking_by_observable_score": sorted(entries,
                    key=lambda x: x["observable_score"], reverse=True),
                "warning": "Scores exclude unobservable semantic correctness; rankings are not proof of task success."}
    entries = [{"source": str(path), "case_id": data["case_id"],
                "classification": data["classification"], "patch_sha256": data["patch_sha256"]}
               for path, data in zip(paths, reports, strict=True)]
    if len({e["case_id"] for e in entries}) != 1:
        raise ValueError("All patches must belong to the same case")
    return {"kind": "patch", "attempts": entries,
            "warning": "Classification is based on test evidence, not a formal proof."}
