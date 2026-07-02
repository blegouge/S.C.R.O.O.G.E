# Runbook onboarding — plateforme Antigravity IA (hub `~/.gemini/antigravity`)

**Public :** développeurs qui veulent le même niveau de configuration agent (rules, hooks, MCP, télémétrie, compression).  
**Plateforme cible :** macOS + zsh (Linux possible avec adaptations mineures).  
**Durée estimée :** 2–4 h première installation · 30 min si le hub est déjà versionné.

**Documents liés :**
- [`ANTIGRAVITY-IA-OPTIMISATION.md`](ANTIGRAVITY-IA-OPTIMISATION.md) — référence fonctionnelle complète
- [`CODE-REVIEW-GRAPH-INSTALLATION-GUIDE.md`](CODE-REVIEW-GRAPH-INSTALLATION-GUIDE.md) — CRG détaillé
- [`../RAPPORT-ANALYSE-ANTIGRAVITY-IA.md`](../RAPPORT-ANALYSE-ANTIGRAVITY-IA.md) — audit / notes
- [`../token-telemetry/COMPRESSION_README.md`](../token-telemetry/COMPRESSION_README.md) — Claw / LLMLingua
- [`../token-telemetry/README.md`](../token-telemetry/README.md) — dashboard télémétrie

---

## Sommaire

1. [Ce que vous obtenez](#1-ce-que-vous-obtenez)
2. [Prérequis](#2-prérequis)
3. [Vue d'ensemble du déploiement](#3-vue-densemble-du-déploiement)
4. [Phase A — Récupérer le hub](#4-phase-a--récupérer-le-hub)
5. [Phase B — Outils système](#5-phase-b--outils-système)
6. [Phase C — Secrets MCP](#6-phase-c--secrets-mcp)
7. [Phase D — Environnement compression](#7-phase-d--environnement-compression)
8. [Phase E — Hooks Antigravity](#8-phase-e--hooks-antigravity)
9. [Phase F — Code Review Graph](#9-phase-f--code-review-graph)
10. [Phase G — RTK](#10-phase-g--rtk)
11. [Phase H — Télémétrie & dashboard](#11-phase-h--télémétrie--dashboard)
12. [Phase I — Repo métier (`AGENT.md`)](#12-phase-i--repo-métier-agentmd)
12b. [Phase J — Intégration Cursor & Session Reset](#12b-phase-j--intégration-cursor--session-reset)
13. [Health check automatisé](#13-health-check-automatisé)
14. [Vérification manuelle (smoke tests)](#14-vérification-manuelle-smoke-tests)
15. [Runbook équipe — rollout](#15-runbook-équipe--rollout)
16. [Dépannage](#16-dépannage)
17. [Checklist finale](#17-checklist-finale)

---

## 1. Ce que vous obtenez

| Capacité | Mécanisme |
|----------|-----------|
| Moins de tokens CLI | **RTK** (`preToolUse` Shell) |
| Moins de tokens subagent | **Claw Compactor** + contexte adaptatif 5 blocs |
| Code patché, pas recopié | **Diff-Only** + hook apply |
| Subagents contrôlés | Caps + **validation brief** (`TASK_BRIEF_ENFORCE=deny`) |
| Transparence conso | **Télémétrie** + Consumption report (hook `stop`) |
| Revues / impact ciblés | **code-review-graph** (CLI + MCP) |
| Workflows Jira | Rules + skills (`/jira-create`, `/jira-prompting`) |
| Intégrations prod | MCP (Datadog, Grafana, MySQL, GitLab, Atlassian, …) |

**Principe :** mesurer avec les hooks, enforcer ce que les règles seules ne garantissent pas, alléger le contexte statique (4 rules always-on).

---

## 2. Prérequis

| Outil | Version min. | Usage |
|-------|--------------|-------|
| **Antigravity** | récent (hooks supportés) | IDE + agents |
| **macOS** ou Linux | — | guide testé macOS |
| **zsh** | — | shell par défaut |
| **Python 3** | 3.10+ (3.12 pour venv compression) | hooks, télémétrie |
| **Node.js** | 18+ | MCP `npx` |
| **Git** | 2.x | CRG, repos métier |
| **uv** / **uvx** | récent | MCP `code-review-graph` |
| **RTK** | installé globalement | compression CLI |

Optionnel : `pip`, Homebrew, accès réseau interne (MCP Grafana, MySQL, ES…).

---

## 3. Vue d'ensemble du déploiement

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Hub ~/.gemini/antigravity (rules, skills, hooks, src, token-telemetry)│
└───────────────────────────┬─────────────────────────────────┘
                            │
     ┌──────────────────────┼──────────────────────┐
     ▼                      ▼                      ▼
  RTK + uv            mcp.secrets.env         .venv-desktop
  (CLI)               (privé 600)             (Claw/LLMLingua)
     │                      │                      │
     └──────────────────────┼──────────────────────┘
                            ▼
              Antigravity lit hooks.json + mcp.json
                            │
                            ▼
              Repo métier + AGENT.md + CRG build
```

**Ordre recommandé :** A → B → C → D → E → F → G → H → I → health-check → smoke tests.

---

## 4. Phase A — Récupérer le hub

### Option 1 — Copie depuis une machine de référence

Copier **au minimum** ces chemins vers `~/.gemini/antigravity/` :

```
.antigravity/
├── AGENT.md
├── hooks.json
├── mcp.json                    # sans secrets (voir phase C)
├── mcp.secrets.env.example
├── compression.env.example
├── rules/                      # tous les .mdc
├── skills/                     # arborescence SKILL.md
├── hooks/                      # scripts .sh + .py
├── src/                        # validators, diff_applier, guardrail
├── bin/                        # mcp-env-exec.sh, claw-compactor, health-check-hub.sh
├── token-telemetry/            # sans .venv-* ni dist/ si trop lourd
└── docs/
```

**Ne pas copier / régénérer localement :**
- `mcp.secrets.env` (credentials personnels)
- `token-telemetry/events.jsonl` (historique perso)
- `projects/`, `extensions/` (générés par Antigravity)
- `.venv-desktop/`, `.venv-build/`, `dist/`

### Option 2 — Dépôt Git d'équipe (recommandé à terme)

Versionner le hub (sans secrets) dans un repo `antigravity-hub` ; chaque dev :

```bash
git clone <url-antigravity-hub> ~/.gemini/antigravity-hub-template
rsync -a --exclude='.git' ~/.gemini/antigravity-hub-template/ ~/.gemini/antigravity/
```

Ajouter au `.gitignore` du repo hub :
```
mcp.secrets.env
token-telemetry/events.jsonl
token-telemetry/.venv-*/
token-telemetry/dist/
projects/
```

### Adapter les chemins personnels

Dans `hooks.json`, remplacer les chemins absolus par des relatifs si possible :

```json
"command": "./hooks/crg-update.sh"
```

au lieu de `/Users/<vous>/.antigravity/hooks/crg-update.sh`.

Dans `mcp.json`, adapter :
- `code-explorer` → `--path` vers votre racine code (`~/www`, `~/projects`, …)
- scripts Node custom (`custom-grafana-server.js`, etc.)

---

## 5. Phase B — Outils système

```bash
# Python
python3 --version

# Node
node --version && npx --version

# uv (CRG MCP)
curl -LsSf https://astral.sh/uv/install.sh | sh
uvx --version

# Rendre les scripts exécutables
chmod +x ~/.gemini/antigravity/bin/*.sh
chmod +x ~/.gemini/antigravity/hooks/*.sh
```

---

## 6. Phase C — Secrets MCP

### 6.1 Créer le fichier secrets

```bash
cp ~/.gemini/antigravity/mcp.secrets.env.example ~/.gemini/antigravity/mcp.secrets.env
chmod 600 ~/.gemini/antigravity/mcp.secrets.env
```

Remplir les variables (exemples) :

```bash
export GRAFANA_API_TOKEN="glsa_..."
export ES_USERNAME="..."
export ES_PASSWORD="..."
export MYSQL_PASSWORD="..."
export DD_API_KEY="..."
export DD_APP_KEY="..."
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
export GITLAB_TOKEN="glpat-..."
```

### 6.2 Vérifier mcp.json

- Les serveurs sensibles doivent utiliser `"command": "~/.gemini/antigravity/bin/mcp-env-exec.sh"` + `args: ["node", ...]` ou `["npx", ...]`.
- **Aucun** token en clair dans `mcp.json`.
- `atlassian` peut rester en URL SSE (auth OAuth côté Antigravity).

### 6.3 Activer les MCP dans Antigravity

1. **Antigravity → Settings → Tools & MCP**
2. Vérifier que les serveurs listés dans `mcp.json` apparaissent
3. Connecter **Atlassian** si besoin (flux navigateur)
4. Redémarrer Antigravity après modification de `mcp.json` ou secrets

### 6.4 Rotation

Si un token a déjà été commité en clair : **révoquer et régénérer** avant de continuer.

---

## 7. Phase D — Environnement compression

Le hook Task (`semantic-compress-pretool.sh`) utilise `.venv-desktop` pour Claw Compactor (et optionnellement LLMLingua).

```bash
cd ~/.gemini/antigravity/token-telemetry
python3.12 -m venv .venv-desktop    # ou python3 si 3.12 indispo
./.venv-desktop/bin/pip install -r requirements-desktop.txt
```

Configurer la compression persistante :

```bash
cp ~/.gemini/antigravity/compression.env.example ~/.gemini/antigravity/compression.env
```

Contenu recommandé :

```bash
COMPRESSION_BACKEND=both          # claw + LLMLingua
TASK_BRIEF_ENFORCE=deny           # bloque Task si brief incomplet
LLMLINGUA_HOOK_RATE=0.6
LLMLINGUA_HOOK_MIN_CHARS=1200
```

Lien symbolique CLI global (optionnel) :

```bash
ln -sf ~/.gemini/antigravity/token-telemetry/.venv-desktop/bin/claw-compactor ~/.gemini/antigravity/bin/claw-compactor
```

**Premier run LLMLingua :** téléchargement modèle Hugging Face (~quelques minutes).

---

## 8. Phase E — Hooks Antigravity

### 8.1 Fichier `~/.gemini/antigravity/hooks.json`

Événements enregistrés :

| Événement | Rôle |
|-----------|------|
| `preToolUse` Shell | RTK rewrite |
| `preToolUse` Task | Validation brief + compression 5 blocs |
| `postToolUse` | Télémétrie sortie outils |
| `afterAgentResponse` | Diff-Only apply + télémétrie |
| `stop` | Enforcement Consumption report |
| `subagentStop` | Diff-Only subagent |
| `afterFileEdit` | Δ lignes + CRG update |
| `sessionStart` | CRG session |
| `beforeShellExecution` | CRG pre-commit |

### 8.2 Activer dans Antigravity

- Vérifier **Settings → Hooks** (ou équivalent selon version)
- Le fichier user-level est `~/.gemini/antigravity/hooks.json`
- Sauvegarder → Antigravity recharge ; sinon **redémarrer Antigravity**

### 8.3 Désactiver temporairement

```bash
export ANTIGRAVITY_DIFF_ONLY_DISABLE=1
export ANTIGRAVITY_CONSUMPTION_ENFORCE_DISABLE=1
# compression.env : TASK_BRIEF_ENFORCE=off
```

### 8.4 Consumption report — format exact

Le hook `stop` parse la réponse. Colon **après** le gras :

```markdown
## Consumption report
- **Work mode**: direct tools only
- **Tool activity**: 5 tool calls
- **Token risk level**: low
- **Main cost drivers**: …
- **Optimization applied**: …
- exact token count unavailable in this environment
```

Voir [`../rules/consumption-report.mdc`](../rules/consumption-report.mdc).

### 8.5 Brief subagent Task — format obligatoire

Si `TASK_BRIEF_ENFORCE=deny`, le Task est **bloqué** sans :

```
Skill: spec-driven-idempotency
MCP task class: LOCAL_CODE
[MCP_ALLOWLIST]: code-review-graph
[CONTEXT]
src/foo.py:10-25
<extrait>
[AC]
- …
```

Exception : `subagent_type=explore` + `RESCAN: allowed` + scope étroit.

---

## 9. Phase F — Code Review Graph

### 9.1 Installer le CLI

Suivre [`CODE-REVIEW-GRAPH-INSTALLATION-GUIDE.md`](CODE-REVIEW-GRAPH-INSTALLATION-GUIDE.md).

Résumé :

```bash
# via uv tool ou pipx
uv tool install code-review-graph
# ou
pipx install code-review-graph

code-review-graph --version
```

### 9.2 MCP global

Déjà dans `mcp.json` :

```json
"code-review-graph": {
  "command": "uvx",
  "args": ["code-review-graph", "serve"]
}
```

### 9.3 Par repo métier

```bash
cd /chemin/vers/votre-repo
code-review-graph register "$PWD" --alias "$(basename "$PWD")"
code-review-graph build
code-review-graph status
```

Les hooks `crg-session-start.sh`, `crg-update.sh`, `crg-pre-commit.sh` maintiennent le graphe à jour.

### 9.4 Registry multi-repo

`~/.code-review-graph/registry.json` — optionnel : daemon watch (voir guide CRG).

---

## 10. Phase G — RTK

RTK compresse la sortie des commandes Shell avant qu'elle n'entre dans le contexte agent.

### Installation

Suivre la doc interne RTK (Confluence VPG) ou le README du projet RTK.

### Vérification

```bash
which rtk
rtk gain
```

Après une session agent avec des `Shell` tools :

```bash
rtk gain -d
```

Le hook `preToolUse` avec matcher `Shell` appelle `rtk hook antigravity` — RTK doit être sur le **PATH** du processus Antigravity (lancer Antigravity depuis un terminal si besoin, ou installer RTK globalement).

---

## 11. Phase H — Télémétrie & dashboard

### 11.1 Fichier de log

```
~/.gemini/antigravity/token-telemetry/events.jsonl
```

Alimenté automatiquement par les hooks (`postToolUse`, `afterAgentResponse`, `subagentLaunch`, etc.).

### 11.2 Rapport terminal

```bash
python3 ~/.gemini/antigravity/token-telemetry/report.py
```

Indicateurs utiles :
- `Coverage report complet` — compliance Consumption report
- `Idempotence [IDEMPOTENT_CONTEXT_INJECTED]` — briefs valides
- `Hook compression` — Claw / LLMLingua

### 11.3 Dashboard web

```bash
python3 ~/.gemini/antigravity/token-telemetry/serve_dashboard.py
# → http://127.0.0.1:8765/
```

### 11.4 App macOS (optionnel)

```bash
cd ~/.gemini/antigravity/token-telemetry && ./build_macos_app.sh
# → dist/SCROOGE.app
```

---

## 12. Phase I — Repo métier (`AGENT.md`)

Chaque **repo de code** devrait avoir à sa racine un `AGENT.md` :

- but du projet, stack, conventions
- commandes build/test
- périmètres sensibles (pas de secrets)

L'agent lit ce fichier **en priorité** sur le hub global.

Template minimal :

```markdown
# AGENT

## Project Purpose
…

## Technical Stack
…

## Conventions
…

## Testing
npm test / pytest / …
```

Pour les workflows ticket :

```bash
# dans le repo
git fetch
# branche PROJ-123 — voir rule jira-branch-bootstrap
```

---

## 12b. Phase J — Intégration Cursor & Session Reset

### 12b.1 Intégration des règles (.mdc) dans Cursor

Cursor (version 0.40+) utilise le format standardisé `.cursor/rules/*.mdc` pour charger les règles contextuelles spécifiques à un projet.

Pour appliquer les optimisations de jetons et les règles d'orchestration (dont `diff-only`, `token-budget-guardrail`, `session-reset`) dans vos projets ouverts sous Cursor, créez un lien symbolique vers les règles du hub global :

```bash
# Dans le dossier racine de votre projet de code
mkdir -p .cursor/rules
ln -sf ~/.gemini/antigravity/rules/*.mdc .cursor/rules/
```

Désormais, Cursor lira automatiquement les règles à chaque tour de chat ou d'Agent.

### 12b.2 Télémétrie Cursor vs Antigravity

Puisque Cursor n'exécute pas nativement de script de hooks lors de l'appel d'outils, la collecte de sa télémétrie se fait de manière passive en lisant son journal interne.
L'application **S.C.R.O.O.G.E.** (compilée ou lancée via `serve_dashboard.py`) écoute et mutualise les deux sources :
- Utilisez le sélecteur en haut à droite du Dashboard (dropdown) pour basculer instantanément entre **Cursor** et **Antigravity**.
- Les indicateurs (RTK, Claw, Diff-Only) s'adapteront à la source active.

### 12b.3 Protocole "Session Reset" (Context Compressor)

L'accumulation de l'historique dans le panneau de chat crée une consommation quadratique $O(N^2)$ de crédits. Pour contourner cette limite de l'IDE :
1. **Détecter la surcharge** : Après 10 à 15 messages ou lorsque le volume de jetons augmente, l'agent ou le développeur suggère de réinitialiser la session.
2. **Générer le résumé** : Demandez à l'agent : `génère le résumé de session reset`. L'agent produit un bloc structuré `# RESUMING SESSION` décrivant l'objectif actif, le statut des tâches et les fichiers ouverts.
3. **Reset** : Copiez ce bloc, cliquez sur **New Chat** (CMD+L ou CMD+K) dans l'IDE pour vider le contexte, et collez le bloc comme premier message. L'agent reprend instantanément avec une consommation de jetons minimale.

---

## 13. Health check automatisé

Script : **`~/.gemini/antigravity/bin/health-check-hub.sh`**

```bash
# Ajouter au PATH (optionnel, dans ~/.zshrc)
export PATH="$HOME/.antigravity/bin:$PATH"

# Contrôle rapide
health-check-hub.sh

# Complet (+ tests unitaires Python)
health-check-hub.sh --full

# Sortie JSON (CI / script équipe)
health-check-hub.sh --json
```

### Codes de sortie

| Code | Signification |
|------|----------------|
| `0` | Tout OK |
| `1` | Avertissements (ex. RTK absent, secrets vides) |
| `2` | Échecs bloquants (hooks manquants, mcp.json invalide) |

### Ce qui est vérifié

- Présence `hooks.json`, `rules/`, `skills/`, scripts hooks exécutables
- RTK, Python, venv-desktop, claw-compactor
- `mcp.secrets.env` (permissions 600)
- Absence de secrets évidents dans `mcp.json`
- Validators Python (`task_brief_validator`, `consumption_report_validator`)
- `code-review-graph`, `uvx`, `report.py`
- `compression.env` / `TASK_BRIEF_ENFORCE`

---

## 14. Vérification manuelle (smoke tests)

Exécuter après le health check.

### Test 1 — RTK

1. Ouvrir un repo dans Antigravity
2. Demander à l'agent : « liste les fichiers à la racine avec une commande shell »
3. Vérifier `rtk gain` augmente

### Test 2 — Télémétrie

1. Une conversation agent avec au moins 1 tool call
2. `python3 ~/.gemini/antigravity/token-telemetry/report.py` → événements > 0

### Test 3 — Consumption report

1. Demander une question simple
2. La réponse doit finir par `## Consumption report` avec 5 champs
3. Si absent → le hook `stop` déclenche un followup (max 2 fois)

### Test 4 — Task brief (si vous utilisez des subagents)

1. Lancer un subagent **sans** brief structuré → doit être **refusé**
2. Relancer avec `Skill:`, `[CONTEXT]`, `[AC]`, MCP class → accepté

### Test 5 — MCP

1. Antigravity → Tools & MCP → serveurs verts
2. Demander « vérif MCP » → probe complet (1×/jour ensuite stamp)

### Test 6 — CRG (dans un repo buildé)

```bash
cd votre-repo
code-review-graph detect-changes
```

---

## 15. Runbook équipe — rollout

### Semaine 0 — Préparation (lead)

| # | Action | Responsable |
|---|--------|-------------|
| 1 | Créer repo `antigravity-hub` sans secrets | Lead |
| 2 | Documenter tokens MCP (vault / 1Password) | SecOps |
| 3 | Publier ce runbook + `health-check-hub.sh` | Lead |

### Semaine 1 — Pilotes (2–3 devs)

| # | Action |
|---|--------|
| 1 | Installer prérequis + hub |
| 2 | `health-check-hub.sh --full` → 0 ou 1 |
| 3 | Smoke tests 1–6 |
| 4 | Feedback : chemins absolus, MCP manquants |

### Semaine 2 — Généralisation

| # | Action |
|---|--------|
| 1 | Session 30 min : démo dashboard + `/jira-create` |
| 2 | `AGENT.md` obligatoire sur repos actifs |
| 3 | CRG `build` sur top 5 repos |
| 4 | KPI équipe : `rtk gain` + `report.py` hebdo |

### Rôles

| Rôle | Mission |
|------|---------|
| **Dev** | Hub local, secrets, AGENT.md repo |
| **Lead IA / platform** | Évolution rules/skills, health-check CI |
| **SecOps** | Rotation tokens, audit `mcp.secrets.env` |

---

## 16. Dépannage

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| Hooks ne tournent pas | Antigravity pas rechargé | Redémarrer Antigravity ; vérifier Settings → Hooks |
| RTK 0 % savings | Pas sur PATH de Antigravity | `which rtk` depuis terminal qui lance Antigravity |
| Task toujours refusé | Brief incomplet | Suivre template § 8.5 ; ou `TASK_BRIEF_ENFORCE=warn` temporaire |
| Boucle Consumption report | Mauvais format `**Label:**` | Utiliser `**Label**:` (voir § 8.4) |
| MCP rouge | Token expiré / script manquant | `mcp.secrets.env` ; logs MCP dans Antigravity |
| CRG vide | Pas de `build` | `code-review-graph build` dans le repo |
| Claw import error | venv absent | Phase D — `pip install -r requirements-desktop.txt` |
| LLMLingua lent | 1er téléchargement HF | Attendre ; ou `COMPRESSION_BACKEND=claw` seul |
| `subagentStop` 0 events | Hook Antigravity souvent inactif | **Fallback** `postToolUse` Task ; `diagnose-subagent-telemetry.sh` |

### Logs utiles

- Antigravity : **Output → Hooks**
- stderr hooks : `[adaptive-context]`, `[diff-only]`, `[consumption-report]`, `[task-brief]`

---

## 17. Checklist finale

Cocher avant de considérer l'onboarding terminé :

- [ ] `health-check-hub.sh` → exit 0 ou 1 acceptable
- [ ] `mcp.secrets.env` mode 600, tokens remplis
- [ ] `compression.env` avec `TASK_BRIEF_ENFORCE=deny`
- [ ] `.venv-desktop` + claw import OK
- [ ] RTK installé, `rtk gain` fonctionne
- [ ] `hooks.json` chargé par Antigravity
- [ ] Au moins 1 repo avec `AGENT.md` + CRG `build`
- [ ] `report.py` montre des événements après une session
- [ ] Consumption report visible en fin de réponse agent
- [ ] Dashboard accessible (optionnel)

---

**Maintenance :** relancer `health-check-hub.sh --full` après toute mise à jour du hub ou upgrade Antigravity.

**Contact / évolutions :** modifier ce runbook et `AGENT.md` ; tenir `RAPPORT-ANALYSE-ANTIGRAVITY-IA.md` à jour pour les audits.
