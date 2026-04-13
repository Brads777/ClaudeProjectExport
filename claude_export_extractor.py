#!/usr/bin/env python3
# ©2026 Brad Scheller
"""
Claude.ai Export Extractor
==========================
Interactive tool for extracting specific projects from a Claude.ai data export ZIP.

Usage:
    python claude_export_extractor.py <path_to_zip>
    python claude_export_extractor.py <path_to_zip> --json       # machine-readable project list
    python claude_export_extractor.py <path_to_zip> --extract <project_nums> --output <dirs>

Examples:
    # Interactive mode — pick projects, set output dirs
    python claude_export_extractor.py ~/Downloads/claude_export.zip

    # Machine-readable — for Claude Code skill automation
    python claude_export_extractor.py export.zip --json

    # Non-interactive — extract projects 1,3 to specific dirs
    python claude_export_extractor.py export.zip --extract 1,3 --output "/path/one,/path/two"
"""

import zipfile
import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_name(name: str, max_len: int = 80) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "_", name)
    name = re.sub(r"_+", "_", name)
    name = re.sub(r"\s+", " ", name).strip().strip("_. ")
    return name[:max_len] or "untitled"


def ts(iso: str) -> str:
    """Format ISO timestamp to readable string."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso or ""


def ts_short(iso: str) -> str:
    """Format ISO timestamp to short date."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


def detect_extension(content: str, filename: str = "") -> str:
    """Guess file extension if filename doesn't already have one."""
    if "." in Path(filename).name:
        return ""
    stripped = content.strip()
    if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
        return ".html"
    if stripped.startswith("<?xml") or stripped.startswith("<svg"):
        return ".xml"
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
            return ".json"
        except Exception:
            pass
    if stripped.startswith("---\n") or re.match(r"^#{1,3}\s", stripped):
        return ".md"
    if stripped.startswith("def ") or stripped.startswith("import ") or stripped.startswith("class "):
        return ".py"
    return ".txt"


# ── Data loading ──────────────────────────────────────────────────────────────

def load_export(zip_path: Path):
    """Load projects and conversations from the export ZIP."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()

        proj_file = next((n for n in names if "project" in n.lower() and n.endswith(".json")), None)
        conv_file = next((n for n in names if "conversation" in n.lower() and n.endswith(".json")), None)

        projects = json.loads(zf.read(proj_file)) if proj_file else []
        conversations = json.loads(zf.read(conv_file)) if conv_file else []

    if isinstance(projects, dict):
        projects = projects.get("projects", [projects])
    if isinstance(conversations, dict):
        conversations = conversations.get("conversations", conversations.get("data", []))

    return projects, conversations


def build_project_index(projects, conversations):
    """Build an enriched index of projects with doc counts and matched conversations."""
    # Build keyword-to-conversation mapping
    conv_name_index = []
    for conv in conversations:
        name = (conv.get("name") or "").lower()
        msg_count = len(conv.get("chat_messages") or conv.get("messages") or [])
        conv_name_index.append((name, msg_count, conv))

    index = []
    for proj in projects:
        name = proj.get("name") or proj.get("title") or "Untitled"
        uuid = proj.get("uuid", "")
        created = ts_short(proj.get("created_at", ""))
        description = proj.get("description", "")
        prompt = proj.get("prompt_template", "")
        docs = proj.get("docs") or []

        # Deduplicate docs by filename
        seen = set()
        unique_docs = []
        for d in docs:
            fname = d.get("filename", "untitled")
            if fname not in seen and d.get("content"):
                seen.add(fname)
                unique_docs.append(d)

        # Count total content size
        total_kb = sum(len(d.get("content", "")) for d in unique_docs) / 1024

        # Match conversations by project name keywords
        keywords = _project_keywords(name)
        matched_convos = []
        for cname, mcnt, conv in conv_name_index:
            if any(k in cname for k in keywords):
                matched_convos.append(conv)

        index.append({
            "name": name,
            "uuid": uuid,
            "created": created,
            "description": description,
            "prompt_template": prompt,
            "docs": unique_docs,
            "doc_count": len(unique_docs),
            "total_kb": total_kb,
            "matched_conversations": matched_convos,
            "conv_count": len(matched_convos),
        })

    return index


def _project_keywords(project_name: str) -> list:
    """Generate search keywords from a project name for conversation matching."""
    name_lower = project_name.lower()
    keywords = [name_lower]

    # Split into significant words (3+ chars, skip common words)
    skip = {"the", "for", "and", "with", "from", "into", "this", "that", "create", "course", "project", "new"}
    words = [w for w in re.split(r'\W+', name_lower) if len(w) >= 3 and w not in skip]
    keywords.extend(words)

    return keywords


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_project(entry, output_dir: Path):
    """Extract a single project's docs and conversations to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    docs_dir = output_dir / "project_knowledge"
    conv_dir = output_dir / "conversations"
    docs_dir.mkdir(exist_ok=True)

    stats = {"docs": 0, "conversations": 0, "docs_kb": 0, "convs_msgs": 0}

    # ── Save project metadata ────────────────────────────────────────────
    meta = {
        "name": entry["name"],
        "uuid": entry["uuid"],
        "description": entry["description"],
        "created": entry["created"],
        "extracted_at": datetime.now().isoformat(),
        "doc_count": entry["doc_count"],
        "conversation_count": entry["conv_count"],
    }
    (docs_dir / "_project_metadata.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )

    # ── Save prompt template ─────────────────────────────────────────────
    if entry["prompt_template"]:
        (docs_dir / "_prompt_template.md").write_text(
            entry["prompt_template"], encoding="utf-8"
        )

    # ── Extract knowledge docs ───────────────────────────────────────────
    for doc in entry["docs"]:
        filename = doc.get("filename", "untitled")
        content = doc.get("content", "")
        if not content:
            continue

        ext = detect_extension(content, filename)
        safe = safe_name(filename) + ext
        (docs_dir / safe).write_text(content, encoding="utf-8")
        stats["docs"] += 1
        stats["docs_kb"] += len(content) / 1024

    # ── Extract conversations ────────────────────────────────────────────
    if entry["matched_conversations"]:
        conv_dir.mkdir(exist_ok=True)

        for conv in entry["matched_conversations"]:
            title = conv.get("name") or "Untitled"
            conv_id = conv.get("uuid", "unknown")
            created = ts(conv.get("created_at", ""))
            updated = ts(conv.get("updated_at", ""))
            messages = conv.get("chat_messages") or conv.get("messages") or []

            lines = [
                f"# {title}\n",
                f"- **ID:** {conv_id}",
                f"- **Created:** {created}",
                f"- **Updated:** {updated}",
                f"- **Messages:** {len(messages)}\n",
                "---\n",
            ]

            for msg in messages:
                role = (msg.get("sender") or msg.get("role") or "unknown").upper()
                msg_ts = ts(msg.get("created_at", ""))

                content = _extract_message_content(msg)

                attachments = msg.get("attachments") or msg.get("files") or []
                attach_notes = []
                for att in attachments:
                    fname = att.get("file_name") or att.get("name") or "attachment"
                    ftype = att.get("file_type") or att.get("type") or ""
                    attach_notes.append(f"[Attachment: {fname} ({ftype})]")
                    # Save text-based attachment content
                    att_content = att.get("extracted_content") or att.get("content") or ""
                    if att_content and len(att_content) > 50:
                        att_ext = detect_extension(att_content, fname)
                        att_safe = safe_name(fname) + att_ext
                        att_path = docs_dir / att_safe
                        if not att_path.exists():
                            att_path.write_text(att_content, encoding="utf-8")

                lines.append(f"### {role}  _{msg_ts}_\n")
                if content:
                    lines.append(content.strip())
                    lines.append("")
                for note in attach_notes:
                    lines.append(f"> {note}")
                if attach_notes:
                    lines.append("")
                lines.append("---\n")

            fname = safe_name(title) + ".md"
            out_path = conv_dir / fname
            counter = 1
            while out_path.exists():
                out_path = conv_dir / (safe_name(title) + f"_{counter}.md")
                counter += 1

            out_path.write_text("\n".join(lines), encoding="utf-8")
            stats["conversations"] += 1
            stats["convs_msgs"] += len(messages)

    return stats


def _extract_message_content(msg) -> str:
    """Extract text content from a message, handling multiple schema shapes."""
    raw = msg.get("content") or msg.get("text") or ""

    if isinstance(raw, str):
        return raw

    if isinstance(raw, list):
        parts = []
        for block in raw:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                btype = block.get("type", "")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "tool_result":
                    for inner in block.get("content", []):
                        if isinstance(inner, dict) and inner.get("type") == "text":
                            parts.append(inner.get("text", ""))
                elif btype == "tool_use":
                    inp = block.get("input", {})
                    if isinstance(inp, dict) and "content" in inp:
                        title = inp.get("title", "untitled")
                        parts.append(f"\n[Artifact: {title}]\n{inp['content']}")
        return "\n".join(parts)

    return ""


# ── Display ───────────────────────────────────────────────────────────────────

def print_project_list(index):
    """Print a numbered list of projects."""
    print(f"\n{'#':>3}  {'Project Name':<50}  {'Docs':>5}  {'Convos':>6}  {'Size':>8}  {'Created':>10}")
    print("─" * 95)
    for i, entry in enumerate(index, 1):
        name = entry["name"][:48]
        size = f"{entry['total_kb']:.0f} KB" if entry["total_kb"] < 1024 else f"{entry['total_kb']/1024:.1f} MB"
        print(f"{i:>3}  {name:<50}  {entry['doc_count']:>5}  {entry['conv_count']:>6}  {size:>8}  {entry['created']:>10}")
    print(f"\nTotal: {len(index)} projects")


def print_json_index(index):
    """Print machine-readable JSON index for Claude Code skill automation."""
    output = []
    for i, entry in enumerate(index, 1):
        output.append({
            "number": i,
            "name": entry["name"],
            "uuid": entry["uuid"],
            "created": entry["created"],
            "description": entry["description"],
            "doc_count": entry["doc_count"],
            "conv_count": entry["conv_count"],
            "total_kb": round(entry["total_kb"], 1),
            "has_prompt": bool(entry["prompt_template"]),
        })
    print(json.dumps(output, indent=2))


# ── Interactive mode ──────────────────────────────────────────────────────────

def interactive_mode(index):
    """Run interactive project selection and extraction."""
    print_project_list(index)

    print("\nEnter project numbers to extract (comma-separated, e.g. '1,3,5')")
    print("Or 'all' to extract everything, or 'q' to quit:")
    choice = input("> ").strip()

    if choice.lower() in ("q", "quit", "exit"):
        print("Cancelled.")
        return

    if choice.lower() == "all":
        selected = list(range(len(index)))
    else:
        try:
            selected = [int(x.strip()) - 1 for x in choice.split(",")]
            for s in selected:
                if s < 0 or s >= len(index):
                    print(f"Invalid number: {s+1}")
                    return
        except ValueError:
            print("Invalid input. Enter numbers separated by commas.")
            return

    # Ask for output directories
    extractions = []
    for idx in selected:
        entry = index[idx]
        default_dir = Path.cwd() / safe_name(entry["name"])
        print(f"\nOutput directory for '{entry['name']}'?")
        print(f"  [Enter] for default: {default_dir}")
        dir_input = input("  > ").strip()
        out_dir = Path(dir_input) if dir_input else default_dir
        extractions.append((entry, out_dir))

    # Confirm
    print("\n── Extraction Plan ──")
    for entry, out_dir in extractions:
        print(f"  {entry['name']}")
        print(f"    -> {out_dir}")
        print(f"    {entry['doc_count']} docs, {entry['conv_count']} conversations")
    print()
    confirm = input("Proceed? [Y/n] ").strip()
    if confirm.lower() in ("n", "no"):
        print("Cancelled.")
        return

    # Extract
    for entry, out_dir in extractions:
        print(f"\nExtracting: {entry['name']} -> {out_dir}")
        stats = extract_project(entry, out_dir)
        print(f"  {stats['docs']} docs ({stats['docs_kb']:.0f} KB)")
        print(f"  {stats['conversations']} conversations ({stats['convs_msgs']} messages)")

    print("\nDone!")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract specific projects from a Claude.ai data export ZIP."
    )
    parser.add_argument("zip_path", help="Path to the Claude.ai export ZIP file")
    parser.add_argument("--json", action="store_true",
                        help="Print project list as JSON (for automation)")
    parser.add_argument("--extract", type=str, default=None,
                        help="Comma-separated project numbers to extract (non-interactive)")
    parser.add_argument("--output", type=str, default=None,
                        help="Comma-separated output directories (one per project)")

    args = parser.parse_args()
    zip_path = Path(args.zip_path)

    if not zip_path.exists():
        print(f"ERROR: File not found: {zip_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {zip_path}", file=sys.stderr if args.json else sys.stdout)
    projects, conversations = load_export(zip_path)
    index = build_project_index(projects, conversations)
    print(f"Found {len(index)} projects, {len(conversations)} conversations",
          file=sys.stderr if args.json else sys.stdout)

    # JSON mode — machine-readable output for Claude Code
    if args.json:
        print_json_index(index)
        return

    # Non-interactive mode — extract specified projects
    if args.extract:
        nums = [int(x.strip()) - 1 for x in args.extract.split(",")]
        dirs = args.output.split(",") if args.output else [None] * len(nums)

        if len(dirs) != len(nums):
            print("ERROR: --output must have the same number of paths as --extract", file=sys.stderr)
            sys.exit(1)

        for i, num in enumerate(nums):
            if num < 0 or num >= len(index):
                print(f"ERROR: Invalid project number: {num+1}", file=sys.stderr)
                sys.exit(1)
            entry = index[num]
            out_dir = Path(dirs[i].strip()) if dirs[i] else Path.cwd() / safe_name(entry["name"])
            print(f"\nExtracting: {entry['name']} -> {out_dir}")
            stats = extract_project(entry, out_dir)
            print(f"  {stats['docs']} docs ({stats['docs_kb']:.0f} KB)")
            print(f"  {stats['conversations']} conversations ({stats['convs_msgs']} messages)")

        print("\nDone!")
        return

    # Interactive mode
    interactive_mode(index)


if __name__ == "__main__":
    main()
