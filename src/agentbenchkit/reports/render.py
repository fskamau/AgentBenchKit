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
        lines += ["", "## Modified files", ""]
        lines += [f"- `{name}`" for name in data["changed_files"]]
    else:
        lines = ["# Evaluation report", "", "```json", json.dumps(data, indent=2), "```"]
    return "\n".join(lines) + "\n"


def write_reports(report: BaseModel, prefix: Path) -> list[Path]:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_out = prefix.with_suffix(".json")
    md_out = prefix.with_suffix(".md")
    html_out = prefix.with_suffix(".html")
    json_out.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    markdown = report_markdown(report)
    md_out.write_text(markdown, encoding="utf-8")
    safe_markdown = html.escape(markdown)
    # Preformatted Markdown remains readable, with safely escaped untrusted evidence.
    content = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
               "<meta name='viewport' content='width=device-width'>"
               "<title>AgentBenchKit evaluation</title>"
               "<style>body{font:15px/1.6 system-ui;margin:2rem auto;max-width:950px;"
               "padding:0 1.5rem;color:#232323}pre{white-space:pre-wrap;overflow-wrap:anywhere;"
               "background:#f4f4f4;padding:1.5rem;border-radius:5px}</style>"
               "</head><body><main><pre>" + safe_markdown + "</pre></main></body></html>\n")
    html_out.write_text(content, encoding="utf-8")
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
