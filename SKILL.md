---
name: ClaudeProjectExport
description: >
  Extract specific projects from a Claude.ai data export ZIP file. Lists all projects
  in the export, lets the user pick which to extract, and saves project knowledge docs
  and related conversations to chosen directories. Trigger with /ClaudeProjectExport.
  Use when the user has a Claude.ai export ZIP and wants to pull project data to their
  local drive, mentions "claude export", "extract projects from export", or wants to
  migrate Claude.ai project context into Claude Code.
user_invocable: true
---

# Claude Export Extractor — Claude Code Skill

Extract projects from a Claude.ai data export ZIP into local directories for use with Claude Code.

## What This Skill Does

Claude.ai projects contain knowledge docs, prompt templates, and conversation history. This skill
extracts specific projects from an export ZIP into organized local folders so the content can be
used as context for Claude Code work.

**Output structure per project:**
```
<output_dir>/
  project_knowledge/          # Knowledge docs, attachments, prompt template
    _project_metadata.json    # Project name, UUID, dates, counts
    _prompt_template.md       # Project custom instructions (if any)
    <knowledge files>...      # All uploaded docs, deduplicated
  conversations/              # Related conversation history as markdown
    <conversation>.md ...     # One file per conversation
```

## Workflow

### Step 1: Locate the ZIP

Ask the user for the path to their Claude.ai export ZIP file. Common locations:
- `~/Downloads/`
- `C:\Downloads\`
- The user may have already mentioned it

Verify the file exists before proceeding.

### Step 2: List projects

Run the extractor in JSON mode to get a machine-readable project list:

```bash
PYTHONIOENCODING=utf-8 python ~/.claude/skills/ClaudeProjectExport/claude_export_extractor.py "<zip_path>" --json
```

This returns a JSON array with each project's name, doc count, conversation count, and size.

### Step 3: Present projects to the user

Show the projects in a clean table format. Ask which projects to extract.

### Step 4: Get output directories

For each selected project, ask where to save the output. Suggest a sensible default based on
the project name and current working directory.

### Step 5: Extract

Run the extractor in non-interactive mode:

```bash
PYTHONIOENCODING=utf-8 python ~/.claude/skills/ClaudeProjectExport/claude_export_extractor.py "<zip_path>" --extract <nums> --output "<dir1>,<dir2>"
```

### Step 6: Report results

Confirm what was saved: doc count, conversation count, output paths.

## Notes

- Conversations are matched to projects by keyword similarity (no UUID link in export format)
- Duplicate docs within a project are automatically deduplicated by filename
- `PYTHONIOENCODING=utf-8` is required on Windows to avoid emoji encoding errors
- Pass `all` numbers to `--extract` for a full dump
