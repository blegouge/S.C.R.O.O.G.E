# Personal skills (all projects)

Skills in this folder are available in **every** Antigravity project.

**Path:** `~/.gemini/antigravity/skills/` → `/Users/blegouge/.antigravity/skills/`

## How to add a skill

1. Create a subfolder per skill, e.g. `my-workflow/`.
2. Add a `SKILL.md` file with YAML frontmatter and instructions:

```markdown
---
name: my-workflow
description: What this skill does and when the agent should use it
---

# My Workflow

## Instructions
Step-by-step guidance for the agent.
```

## Example layout

```
skills/
├── README.md
├── my-skill/
│   └── SKILL.md
└── another-skill/
    ├── SKILL.md
    └── reference.md   # optional
```

Once you add a skill here, Antigravity will load it for all your projects.
