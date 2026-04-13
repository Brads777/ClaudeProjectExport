# Claude Project Export — Extract Projects from Claude.ai Data Exports

> **The missing tool for Claude.ai power users.** Selectively extract projects, knowledge docs, prompt templates, and conversation history from your Claude.ai data export ZIP file.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#installation)

## The Problem

When you export your data from [Claude.ai](https://claude.ai), you get **one giant ZIP** with every conversation you've ever had. If you have 88 projects and 950 conversations, there's no way to extract just the projects you need.

**Claude Project Export** solves this. Point it at your export ZIP, pick the projects you want, and get clean local folders with all the knowledge docs, prompt templates, and related conversations — organized and ready to use.

## Key Features

- **Interactive project picker** — see all your projects listed with doc counts, conversation counts, and sizes, then pick by number
- **Selective extraction** — extract one project, multiple projects, or everything
- **Smart conversation matching** — automatically finds conversations related to each project (Claude.ai exports don't link them)
- **Three modes** — interactive (human), JSON (automation), CLI (scripted)
- **Zero dependencies** — pure Python 3.10+ stdlib, nothing to install
- **Claude Code skill** — install as a `/ClaudeProjectExport` slash command

## Quick Start

```bash
git clone https://github.com/Brads777/ClaudeProjectExport.git
cd ClaudeProjectExport
python claude_export_extractor.py ~/Downloads/your-claude-export.zip
```

That's it. No `pip install`, no virtual environment, no config file.

## How to Export Your Data from Claude.ai

1. Go to [claude.ai](https://claude.ai) and sign in
2. Click your **profile icon** (bottom-left corner)
3. Click **Settings**
4. Under the **Account** section, click **Export Data**
5. Claude sends you an email with a download link (usually arrives within a few minutes)
6. Download the ZIP file — it contains four JSON files:

| File | Contents |
|------|----------|
| `conversations.json` | All your chat history (every conversation you've had) |
| `projects.json` | Your projects with knowledge docs and prompt templates |
| `memories.json` | Saved memories |
| `users.json` | Account info |

## Usage

### Interactive Mode (Recommended)

```bash
python claude_export_extractor.py path/to/claude-export.zip
```

You'll see a table of all your projects:

```
  #  Project Name                                        Docs  Convos      Size     Created
───────────────────────────────────────────────────────────────────────────────────────────────
  1  My Research Project                                   12      28   340 KB  2025-11-03
  2  Course Materials                                       7       5    78 KB  2026-01-15
  3  API Documentation                                      3       2    12 KB  2026-03-20

Enter project numbers to extract (comma-separated, e.g. '1,3,5')
Or 'all' to extract everything, or 'q' to quit:
> 1,2
```

Then choose output directories for each, confirm, and extract.

### Non-Interactive Mode

```bash
# Extract projects 1 and 3 to specific directories
python claude_export_extractor.py export.zip --extract 1,3 --output "./research,./course"
```

### JSON Mode (for Automation)

```bash
# Get machine-readable project list
python claude_export_extractor.py export.zip --json
```

Returns a JSON array you can pipe into other tools:

```json
[
  {
    "number": 1,
    "name": "My Research Project",
    "doc_count": 12,
    "conv_count": 28,
    "total_kb": 340.2,
    "has_prompt": true
  }
]
```

## Output Structure

Each extracted project creates this organized layout:

```
<output_dir>/
├── project_knowledge/
│   ├── _project_metadata.json    # Project name, UUID, dates, doc/conversation counts
│   ├── _prompt_template.md       # Project custom instructions (if the project had one)
│   ├── research-paper.pdf        # Knowledge docs you uploaded to the project
│   ├── api-spec.yaml             #   (deduplicated — no duplicates)
│   └── notes.md                  #   (original filenames preserved)
└── conversations/
    ├── Building the API client.md         # Related conversations as readable markdown
    ├── Debugging auth flow.md             #   (matched by project name keywords)
    └── Architecture review.md
```

## How Conversation Matching Works

Claude.ai's export format **does not link conversations to projects** by ID — there's no `project_uuid` field on conversations. This tool matches conversations to projects using keyword similarity on the project name.

For example, a project named "NEU Marketing 2700" will match conversations containing "2700", "marketing", or "NEU" in their titles. This catches most relevant conversations but may occasionally include false positives.

## Use Cases

- **Migrate Claude.ai projects to Claude Code** — extract your project knowledge and use it as local context
- **Back up specific projects** — don't lose important research when your Claude.ai subscription changes
- **Audit project history** — review all knowledge docs and conversations organized by project
- **Course material extraction** — pull out teaching materials, rubrics, and student interaction history
- **Share project context** — extract a project's knowledge base to share with collaborators

## Claude Code Integration

This tool also works as a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill. Install it as a `/ClaudeProjectExport` slash command:

```bash
mkdir -p ~/.claude/skills/ClaudeProjectExport
cp claude_export_extractor.py SKILL.md ~/.claude/skills/ClaudeProjectExport/
```

Then in Claude Code, type `/ClaudeProjectExport` and follow the prompts.

## Requirements

- **Python 3.10+** (uses `match` statements and modern type hints)
- No external packages — stdlib only (`zipfile`, `json`, `argparse`, `pathlib`)
- Works on **Windows**, **macOS**, and **Linux**

## FAQ

### Does this extract images or file attachments from conversations?

It extracts text content from attachments (the `extracted_content` field in the export), but binary files (images, PDFs) are not included in Claude.ai's export format — only their text extractions are.

### Why aren't my conversations linked to the right project?

Claude.ai's export format doesn't include a project-to-conversation link. The tool uses keyword matching on conversation titles, which works well for most cases but isn't perfect. Projects with very generic names (like "Test") may match too many conversations.

### Can I extract conversations that aren't in any project?

Currently the tool focuses on project-based extraction. For a full dump of all conversations, use the export ZIP directly — `conversations.json` contains everything.

### Does this work with Claude.ai Team/Enterprise exports?

It should work with any Claude.ai data export that follows the standard format (`conversations.json`, `projects.json`). The schema is auto-detected.

## Contributing

Issues and PRs welcome. The codebase is a single Python file — easy to read and modify.

## License

[MIT License](LICENSE) — use it however you want.

## Author

**Brad Scheller** — building [ToolsIQ](https://toolsiq.ai), an AI-powered toolkit for education and business.

---

*Built with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — Anthropic's agentic coding tool.*
