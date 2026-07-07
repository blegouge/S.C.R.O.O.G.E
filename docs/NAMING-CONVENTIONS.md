# Conventions de Nommage de la Stack d'Optimisation

Ce document définit les règles de nommage des hooks, des skills et des serveurs MCP pour garantir la cohérence de l'architecture multi-agents.

---

## 1. Hooks (IDE Agent Hooks)

Les hooks sont des scripts exécutés aux différents stades du cycle de vie de l'agent (avant l'usage d'un outil, après une réponse, etc.).

### Règle générale
Les nouveaux hooks doivent suivre le format suivant :
```
hk_<event>_<purpose>.<extension>
```

*   **`hk_`** : Préfixe obligatoire pour distinguer les hooks des scripts CLI génériques.
*   **`<event>`** : L'événement déclencheur de l'IDE :
    *   `pretool` (e.g. `preToolUse`)
    *   `posttool` (e.g. `postToolUse`)
    *   `after_response` (e.g. `afterAgentResponse`)
    *   `stop` (e.g. `stop`)
*   **`<purpose>`** : Description concise en anglais (kebab-case ou snake_case) du but du hook (e.g., `compress`, `diff`, `compliance`).
*   **`<extension>`** : `.sh` pour les wrappers shell légers, `.py` pour les scripts logiques Python.

### Exemples :
*   `hk_pretool_compress.py` (remplace à terme `semantic-compress-pretool.py`)
*   `hk_after_response_diff.py` (remplace à terme `diff-only-apply.py`)
*   `hk_stop_compliance.py` (remplace à terme `stop-compliance.py`)

*Note : Les fichiers existants dans `hub_files/hooks/` conservent leurs noms pour préserver la compatibilité ascendante avec les installations actives, mais toute nouvelle brique doit adopter la nouvelle convention.*

---

## 2. Skills (Dossiers de compétences agents)

Les skills sont des dossiers contenant des instructions structurées (`SKILL.md`) et des ressources d'aide.

### Règle générale
Les dossiers de skills doivent être écrits en **kebab-case** en anglais :
```
<domain>-<action-or-purpose>
```

*   **`<domain>`** : Le périmètre technique ou fonctionnel concerné (e.g., `jira`, `git`, `a11y`, `api`, `db`).
*   **`<action-or-purpose>`** : L'action effectuée par le skill ou sa fonction principale (e.g., `triage`, `cleanup`, `debugging`).

### Exemples :
*   `jira-ticket-triage` (Triage de ticket Atlassian)
*   `spec-driven-idempotency` (Gestion de l'idempotence parent/subagent)
*   `safe-output-hygiene` (Redondance et nettoyage de secrets)
*   `dependency-change-risk` (Analyse d'impact de package)

---

## 3. MCP (Model Context Protocol)

Les intégrations MCP étendent le contexte de l'agent via des serveurs externes.

### Règle générale
Les serveurs et outils MCP doivent être déclarés en **kebab-case** :
```
<source>-mcp
```
Ou simplement le nom de la source s'il est unique.

*   Les outils exposés par le serveur doivent utiliser le snake_case avec la source en préfixe ou un verbe d'action clair :
    *   Exemple : `get_architecture_overview_tool` (dans le serveur `code-review-graph`)
