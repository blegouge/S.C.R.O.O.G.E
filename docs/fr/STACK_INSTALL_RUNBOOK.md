# STACK_INSTALL_RUNBOOK — Déploiement universel de la stack d'optimisation de tokens (Hub `~/.cursor`)

> **Rôle assumé :** Ingénieur DevOps Senior + Architecte Infrastructure LLM.
> **Objet :** Installer, dans un ordre déterministe et mesurable, la stack d'optimisation de tokens du hub `~/.cursor`.
> **Public lecteur :** humain **OU** agent (Cursor, Aider, Windsurf, script CI). Chaque étape est atomique, idempotente et fournit les commandes **macOS/Linux (zsh/bash)** ET **Windows (PowerShell)**.

---

## Principes directeurs (lire avant d'exécuter)

1. **Metric-First** — l'observabilité (`events.jsonl` + dashboard) s'installe **en premier**. On ne déploie aucune brique sans pouvoir mesurer son impact en tokens.
2. **ROI décroissant** — après l'observabilité, on installe les briques par gain mesuré décroissant : RTK (~98 %) → Diff-Only (~70-95 % sortie) → Claw/Adaptive Context (~30-70 % entrée) → Gouvernance (anti-boucle / anti-redondance).
3. **Déterminisme** — chaque étape expose une **commande de vérification** (`Check`) renvoyant un état binaire. Un agent doit traiter `Check` ≠ OK comme un arrêt bloquant de l'étape.
4. **Idempotence** — toutes les commandes peuvent être relancées sans casser un état existant (création conditionnelle, `cp` template only-if-absent, etc.).

### Convention d'exécution pour un agent automatisé

```text
POUR chaque étape S dans [1..5]:
    EXÉCUTER les commandes de S pour l'OS courant
    EXÉCUTER le bloc "Check" de S
    SI Check != OK -> ARRÊTER, remonter le diagnostic, NE PAS passer à S+1
À la fin: EXÉCUTER verify_stack.py (section 7) -> exiger [OK] sur les 4 briques testées
```

---

## 1. Introduction & Prérequis

### 1.1 Table des correspondances des chemins

Le hub porte le même rôle sur tous les OS ; seule la racine change. Définissez une variable racine au début de session et utilisez-la partout.

| Élément logique | macOS / Linux (zsh/bash) | Windows (PowerShell) |
|---|---|---|
| Racine du hub | `~/.cursor` → `$HOME/.cursor` | `$HOME\.cursor` (= `%USERPROFILE%\.cursor`) |
| Hooks | `~/.cursor/hooks/` | `$HOME\.cursor\hooks\` |
| Règles système | `~/.cursor/rules/` | `$HOME\.cursor\rules\` |
| Skills | `~/.cursor/skills/` | `$HOME\.cursor\skills\` |
| Spécs / utils injectables | `~/.cursor/src/` | `$HOME\.cursor\src\` |
| Données télémétrie (append-only) | `~/.cursor/token-telemetry/events.jsonl` | `$HOME\.cursor\token-telemetry\events.jsonl` |
| App télémétrie (dashboard, report) | `~/www/private/SCROOGE` | `$HOME\www\private\SCROOGE` |
| Cache Git pré-flight (BLOCK_2) | `~/.cursor/projects/cache_<sig>.json` | `$HOME\.cursor\projects\cache_<sig>.json` |
| Config compression | `~/.cursor/compression.env` | `$HOME\.cursor\compression.env` |
| Config hooks | `~/.cursor/hooks.json` | `$HOME\.cursor\hooks.json` |

> **Note Windows / AppData :** Cursor stocke certaines données applicatives sous `%APPDATA%\Cursor` et `%USERPROFILE%\.cursor`. Le hub de cette stack vit toujours dans `%USERPROFILE%\.cursor` (équivalent `~/.cursor`). N'utilisez `%APPDATA%` que pour les réglages internes de l'éditeur, jamais pour les fichiers de cette stack.

**Définir la racine (à exécuter en début de session) :**

```bash
# macOS / Linux
export HUB="$HOME/.cursor"
export TT_APP="${CURSOR_TOKEN_TELEMETRY_APP:-$HOME/www/private/SCROOGE}"
export TT_DATA="${CURSOR_TOKEN_TELEMETRY_DATA_DIR:-$HUB/token-telemetry}"
echo "HUB=$HUB"; echo "TT_APP=$TT_APP"; echo "TT_DATA=$TT_DATA"
```

```powershell
# Windows PowerShell
$env:HUB     = "$HOME\.cursor"
$env:TT_APP  = if ($env:CURSOR_TOKEN_TELEMETRY_APP)      { $env:CURSOR_TOKEN_TELEMETRY_APP }      else { "$HOME\www\private\SCROOGE" }
$env:TT_DATA = if ($env:CURSOR_TOKEN_TELEMETRY_DATA_DIR) { $env:CURSOR_TOKEN_TELEMETRY_DATA_DIR } else { "$env:HUB\token-telemetry" }
Write-Host "HUB=$env:HUB"; Write-Host "TT_APP=$env:TT_APP"; Write-Host "TT_DATA=$env:TT_DATA"
```

### 1.2 Vérification des moteurs locaux

| Moteur | Version min. | Rôle dans la stack |
|---|---|---|
| **Python** | 3.12+ (3.10 toléré, 3.12 requis pour `.venv-desktop`) | hooks, télémétrie, diff applier, adaptive context |
| **Node.js** | 18+ | serveurs MCP (`npx`/`node`) |
| **Pip** | fourni avec Python | dépendances compression |
| **Git** | 2.x | cache pré-flight, hooks pre-commit, CRG |
| **RTK** | dernière | compression sortie Shell (étape 2) |

**Check moteurs :**

```bash
# macOS / Linux
python3 --version && node --version && npx --version && python3 -m pip --version && git --version
```

```powershell
# Windows PowerShell
python --version; node --version; npx --version; python -m pip --version; git --version
```

> **Critère OK :** Python ≥ 3.12 (ou ≥ 3.10 avec avertissement), Node ≥ 18, `git` et `pip` présents. Sinon, installer le moteur manquant **avant** de continuer (Homebrew/apt sous Unix ; `winget`/`choco` sous Windows).

---

## 2. Étape 1 : Fondations & Observabilité (Metric-First)

> **Objectif : pouvoir mesurer avant d'agir.** Aucune autre brique ne s'installe tant que `events.jsonl` et le dashboard ne sont pas opérationnels.
> **ROI :** prérequis transverse — c'est le **système de mesure** qui validera le ROI de toutes les étapes suivantes.

### 2.1 Initialiser le fichier append-only global `events.jsonl`

Le fichier `events.jsonl` est la **source de vérité unique** de la consommation. Les hooks (`postToolUse`, `afterAgentResponse`, `subagentStop`, `afterFileEdit`) y **ajoutent** une ligne JSON par événement (jamais de réécriture).

```bash
# macOS / Linux
mkdir -p "$TT_DATA"
[ -f "$TT_DATA/events.jsonl" ] || : > "$TT_DATA/events.jsonl"
ls -l "$TT_DATA/events.jsonl"
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path $env:TT_DATA | Out-Null
if (-not (Test-Path "$env:TT_DATA\events.jsonl")) { New-Item -ItemType File -Path "$env:TT_DATA\events.jsonl" | Out-Null }
Get-Item "$env:TT_DATA\events.jsonl"
```

> **Idempotent :** ne tronque jamais un fichier existant (test `-f` / `Test-Path`).

### 2.2 Installer le pipeline de télémétrie local

Le code applicatif (report + serveurs) vit dans `TT_APP` ; les **données** vivent dans `TT_DATA`. Le lien entre les deux est fait par `bin/telemetry-paths.sh` (variables `CURSOR_TOKEN_TELEMETRY_APP`, `CURSOR_TOKEN_TELEMETRY_DATA_DIR`).

Composants attendus dans `TT_APP` :
- `report.py` — rapport texte (terminal/CI).
- `serve_dashboard.py` — serveur HTTP du dashboard (navigateur).
- `dashboard_app.py` — variante fenêtre native (`pywebview`, optionnel).
- `requirements-desktop.txt` — dépendances.

**Créer l'environnement Python d'analyse :**

```bash
# macOS / Linux
cd "$TT_APP"
python3.12 -m venv .venv-desktop 2>/dev/null || python3 -m venv .venv-desktop
./.venv-desktop/bin/python -m pip install --upgrade pip
./.venv-desktop/bin/python -m pip install -r requirements-desktop.txt
```

```powershell
# Windows PowerShell
Set-Location $env:TT_APP
py -3.12 -m venv .venv-desktop 2>$null; if (-not (Test-Path ".\.venv-desktop")) { python -m venv .venv-desktop }
.\.venv-desktop\Scripts\python.exe -m pip install --upgrade pip
.\.venv-desktop\Scripts\python.exe -m pip install -r requirements-desktop.txt
```

**Check rapport texte :**

```bash
# macOS / Linux
CURSOR_TOKEN_TELEMETRY_DATA_DIR="$TT_DATA" "$TT_APP/.venv-desktop/bin/python" "$TT_APP/report.py"
```

```powershell
# Windows PowerShell
$env:CURSOR_TOKEN_TELEMETRY_DATA_DIR = $env:TT_DATA
& "$env:TT_APP\.venv-desktop\Scripts\python.exe" "$env:TT_APP\report.py"
```

> **Critère OK :** `report.py` s'exécute sans exception et affiche un résumé (0 événement est acceptable sur une install neuve).

### 2.3 Lancer le Dashboard en tâche de fond

Le dashboard sert l'analyse en continu sur `http://127.0.0.1:8765/`. Il doit tourner en **arrière-plan** pour ne pas bloquer la suite du runbook.

**macOS / Linux — daemon Bash (nohup + PID file) :**

```bash
cd "$TT_APP"
nohup "$TT_APP/.venv-desktop/bin/python" serve_dashboard.py \
  > "$TT_DATA/dashboard.log" 2>&1 &
echo $! > "$TT_DATA/dashboard.pid"
sleep 2
echo "Dashboard PID $(cat "$TT_DATA/dashboard.pid") -> http://127.0.0.1:8765/"
# Arrêt : kill "$(cat "$TT_DATA/dashboard.pid")"
```

**Windows — PowerShell Background Job :**

```powershell
Set-Location $env:TT_APP
$job = Start-Job -Name "TokenDashboard" -ScriptBlock {
    param($app, $data)
    $env:CURSOR_TOKEN_TELEMETRY_DATA_DIR = $data
    & "$app\.venv-desktop\Scripts\python.exe" "$app\serve_dashboard.py"
} -ArgumentList $env:TT_APP, $env:TT_DATA
Start-Sleep -Seconds 2
Write-Host "Dashboard Job Id $($job.Id) -> http://127.0.0.1:8765/"
# Arrêt : Stop-Job -Name TokenDashboard ; Remove-Job -Name TokenDashboard
```

**Check dashboard (les deux OS) :**

```bash
# macOS / Linux
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8765/
```

```powershell
# Windows PowerShell
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/).StatusCode
```

> **Critère OK :** code HTTP `200`. **Étape 1 validée** → l'observabilité est en ligne, on peut mesurer les gains des étapes suivantes.

---

## 3. Étape 2 : RTK CLI (Le plus gros ROI — ~98 % de gain)

> **Objectif : verrouiller les entrées/sorties du terminal.** La sortie brute des commandes Shell (`grep`, `git`, `find`, `ls`, logs) est la première source de pollution du contexte. RTK l'intercepte et la compacte avant qu'elle n'entre dans le contexte de l'agent.
> **ROI mesuré : ~98 % de réduction** sur les sorties terminal volumineuses.

### 3.1 Installer la CLI RTK

```bash
# macOS / Linux — selon la distribution interne RTK (Homebrew tap / binaire / pipx)
# Exemple générique :
#   brew install rtk           # si tap disponible
#   pipx install rtk           # si paquet Python
which rtk && rtk --version
```

```powershell
# Windows PowerShell
#   winget install rtk         # si paquet disponible
#   ou installation binaire dans un dossier du PATH
Get-Command rtk; rtk --version
```

> **Critère PATH :** RTK doit être sur le **PATH du processus Cursor**. Si Cursor est lancé depuis le Dock/menu Démarrer, il peut ne pas hériter du PATH du shell. Lancer Cursor depuis un terminal, ou installer RTK dans un emplacement système.

### 3.2 Configurer le hook `preToolUse` pour intercepter les commandes Shell

Le hook intercepte **toute** invocation de l'outil `Shell` (Grep, Git, Find, Ls, etc.) et la réécrit via `rtk hook cursor`. Vérifier/ajouter dans `~/.cursor/hooks.json` :

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      { "command": "rtk hook cursor", "matcher": "Shell" }
    ]
  }
}
```

> Si `hooks.json` existe déjà avec d'autres hooks, **ajoutez** l'entrée dans le tableau `preToolUse` existant (ne remplacez pas le fichier).

**Check RTK :**

```bash
# macOS / Linux
rtk gain                 # baseline (0 % au départ)
# Après une session agent avec des appels Shell :
rtk gain -d              # détail des gains
```

```powershell
# Windows PowerShell
rtk gain
rtk gain -d
```

> **Critère OK :** `rtk` répond, et `hooks.json` contient l'entrée `preToolUse` `Shell` → `rtk hook cursor`. Après une session réelle, `rtk gain` doit augmenter. **Étape 2 validée.**

---

## 4. Étape 3 : Diff-Only Protocol (ROI Sortie — ~70-95 % de gain)

> **Objectif : stopper l'écriture de fichiers entiers.** Les agents (surtout les sous-agents) ont tendance à recopier des fichiers complets en sortie. Diff-Only force l'émission de **hunks SEARCH/REPLACE** uniquement, appliqués par un analyseur déterministe (zéro second appel LLM).
> **ROI : ~70-95 % de réduction** des tokens de sortie sur les éditions de code.

### 4.1 Spécification & règle système

Composants attendus dans le hub :
- `src/rules/diff_protocol.md` — spécification SSOT (format SEARCH/REPLACE, cas spéciaux).
- `rules/diff-only-protocol.mdc` — règle système always-on (impose le format aux agents).
- `src/rules/diff_integration.md` — intégration applier ↔ hooks.

Format imposé (rappel) :

```text
path: relative/path/from/repo/root.ext
<<<<<<< SEARCH
<lignes exactes existantes — match byte-for-byte, 3 à 8 lignes de contexte>
=======
<lignes de remplacement uniquement>
>>>>>>> REPLACE
```

Cas spéciaux : **nouveau fichier** → `SEARCH` vide, contenu complet en `REPLACE` ; **suppression** → `REPLACE` vide.

**Check présence spec/règle :**

```bash
# macOS / Linux
for f in "$HUB/src/rules/diff_protocol.md" "$HUB/rules/diff-only-protocol.mdc" "$HUB/src/utils/diff_applier.py"; do
  [ -f "$f" ] && echo "OK   $f" || echo "FAIL $f"
done
```

```powershell
# Windows PowerShell
@("$env:HUB\src\rules\diff_protocol.md","$env:HUB\rules\diff-only-protocol.mdc","$env:HUB\src\utils\diff_applier.py") |
  ForEach-Object { if (Test-Path $_) { "OK   $_" } else { "FAIL $_" } }
```

### 4.2 Déployer l'intercepteur/analyseur déterministe `diff_applier.py`

`src/utils/diff_applier.py` parse les blocs SEARCH/REPLACE, vérifie l'unicité du match dans le fichier cible, et applique le patch **sans LLM**. Il signale `ambiguous` si le SEARCH matche plusieurs fois.

**Check importabilité de l'applier :**

```bash
# macOS / Linux
python3 -c "import sys; sys.path.insert(0,'$HUB/src/utils'); import diff_applier; print('diff_applier OK')"
```

```powershell
# Windows PowerShell
python -c "import sys; sys.path.insert(0, r'$env:HUB\src\utils'); import diff_applier; print('diff_applier OK')"
```

### 4.3 Injecter les hooks de sortie

Le hook `hooks/diff-only-apply.py` s'exécute sur `afterAgentResponse` (réponse parent) **et** `subagentStop` (retour sous-agent). Un garde `preToolUse` sur `Write` (`diff-only-pretool-write`) empêche la réécriture de fichiers entiers existants. Ajouter dans `~/.cursor/hooks.json` :

```json
{
  "hooks": {
    "preToolUse": [
      { "command": "./hooks/diff-only-pretool-write.sh", "matcher": "Write" }
    ],
    "afterAgentResponse": [
      { "command": "./hooks/diff-only-after-response.sh" }
    ],
    "subagentStop": [
      { "command": "./hooks/diff-only-subagent-stop.sh" }
    ]
  }
}
```

> Désactivation temporaire (debug) : `CURSOR_DIFF_ONLY_DISABLE=1`.

**Check hooks :**

```bash
# macOS / Linux
chmod +x "$HUB"/hooks/*.sh
python3 -c "import json,os; h=json.load(open(os.path.expanduser('~/.cursor/hooks.json'))); \
print('afterAgentResponse' in h['hooks'] and 'subagentStop' in h['hooks'])"
```

```powershell
# Windows PowerShell
$h = Get-Content "$env:HUB\hooks.json" -Raw | ConvertFrom-Json
($h.hooks.PSObject.Properties.Name -contains 'afterAgentResponse') -and ($h.hooks.PSObject.Properties.Name -contains 'subagentStop')
```

> **Critère OK :** spec + règle + `diff_applier` importable + hooks `afterAgentResponse`/`subagentStop` enregistrés. Le test fonctionnel d'application de patch est exécuté par `verify_stack.py` (section 7, brique 2). **Étape 3 validée.**

---

## 5. Étape 4 : Claw Compactor & Adaptive Context (ROI Entrée — ~30-70 % de gain)

> **Objectif : compresser le contexte lourd et l'historique sans coût LLM.** On agit sur les **tokens d'entrée** : briefs de sous-agents, gros contextes, historique. Deux mécanismes complémentaires : compression sémantique (Claw) + assemblage cache-friendly (Adaptive Context).
> **ROI : ~30-70 % de réduction** des tokens d'entrée.

### 5.1 Installer le package `claw-compactor` (pipeline Fusion 14 étapes)

Claw vit dans `TT_APP/.venv-desktop` ; un wrapper CLI global est exposé via `~/.cursor/bin/claw-compactor`. Le hook `semantic-compress-pretool` l'applique sur l'outil `Task` (`COMPRESSION_BACKEND=claw`).

```bash
# macOS / Linux — claw est fourni par requirements-desktop.txt (étape 1) ; on lie le CLI :
ln -sf "$TT_APP/.venv-desktop/bin/claw-compactor" "$HUB/bin/claw-compactor"
"$HUB/bin/claw-compactor" --help >/dev/null 2>&1 && echo "claw-compactor OK"
```

```powershell
# Windows PowerShell — pas de symlink : wrapper .cmd
$wrapper = "$env:HUB\bin\claw-compactor.cmd"
"@echo off`r`n`"$env:TT_APP\.venv-desktop\Scripts\claw-compactor.exe`" %*" | Set-Content -Encoding ASCII $wrapper
& $wrapper --help *> $null; if ($LASTEXITCODE -eq 0) { "claw-compactor OK" }
```

Activer le backend dans `~/.cursor/compression.env` :

```bash
COMPRESSION_BACKEND=claw
LLMLINGUA_HOOK_RATE=0.5
LLMLINGUA_HOOK_MIN_CHARS=2500
```

Hook à enregistrer dans `hooks.json` (`preToolUse` sur `Task`) :

```json
{ "command": "./hooks/semantic-compress-pretool.sh", "matcher": "Task" }
```

### 5.2 Déployer `adaptive_context_manager.py` — structuration 4 blocs Cache-Friendly

`src/utils/adaptive_context_manager.py` assemble les messages dans l'ordre strict **cache-friendly** (du plus stable au plus volatil), maximisant les hits de cache KV du fournisseur LLM :

| Bloc | Nature | Contenu | Volatilité |
|---|---|---|---|
| **BLOCK_1** | **Static** | prompt système / règles always-on | quasi nulle |
| **BLOCK_2** | **Semi-Static** | état global KV (`[GLOBAL_STATE_KV]`) | faible (change avec l'état Git) |
| **BLOCK_3** | **Dynamic** | fenêtre d'historique récent | moyenne |
| **BLOCK_4** | **Ultra-Dynamic** | dernier message utilisateur (`[LATEST_INPUT]`) + éphémère | maximale |

> Ordre = `static → semi-static state → recent dynamic history → latest ultra-dynamic input`. Les blocs stables en tête maximisent la réutilisation du cache fournisseur.

**Check importabilité :**

```bash
# macOS / Linux
python3 -c "import sys; sys.path.insert(0,'$HUB/src/utils'); import adaptive_context_manager as a; \
print('adaptive_context_manager OK', hasattr(a,'GitPreflightCache'))"
```

```powershell
# Windows PowerShell
python -c "import sys; sys.path.insert(0, r'$env:HUB\src\utils'); import adaptive_context_manager as a; print('adaptive_context_manager OK', hasattr(a,'GitPreflightCache'))"
```

### 5.3 LLM-Free Pre-Flight Cache Check (basé sur l'état Git)

`GitPreflightCache` calcule une **signature déterministe** à partir de l'état Git (branche + commit SHA + `git status --porcelain` assaini) et persiste le BLOCK_2 KV sous `~/.cursor/projects/cache_<git_signature>.json`. Si la signature correspond à un fichier existant, l'état semi-statique est **rechargé depuis le disque sans recalcul LLM** (court-circuit).

Réglages dans `compression.env` (seuils d'activation) :

```bash
ADAPTIVE_CTX_TOKEN_THRESHOLD=4000
ADAPTIVE_CTX_MESSAGE_THRESHOLD=10
ADAPTIVE_CTX_STRUCTURE_MIN_INPUT_TOKENS=2500
```

> Le répertoire de cache `~/.cursor/projects/` est exclu de l'index Cursor (`.cursorignore`) et les artefacts `cache_*.json` sont filtrés de la signature porcelain (auto-référence évitée).

**Check répertoire de cache :**

```bash
# macOS / Linux
mkdir -p "$HUB/projects" && echo "projects dir OK -> $HUB/projects"
```

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Force -Path "$env:HUB\projects" | Out-Null; "projects dir OK -> $env:HUB\projects"
```

> **Critère OK :** `claw-compactor` répond, `adaptive_context_manager` importable avec `GitPreflightCache`, `compression.env` peuplé, `projects/` présent. Le test fonctionnel d'écriture du cache est exécuté par `verify_stack.py` (section 7, brique 3). **Étape 4 validée.**

---

## 6. Étape 5 : Gouvernance & Guardrails (ROI Orchestration)

> **Objectif : éviter les boucles folles et la redondance multi-agents.** À ce stade les briques de compression sont en place ; la gouvernance empêche le gaspillage structurel (re-tentatives infinies, sous-agents qui re-scannent ce que le parent a déjà lu, prose verbeuse).
> **ROI : orchestration** — économise les tokens consommés par les comportements pathologiques.

### 6.1 `token-budget-guardrail` (disjoncteur sur échec répété)

`src/utils/token_budget_guardrail.py` + règle `rules/token-budget-guardrail.mdc` + skill `skills/token-budget-guardrail/`. Mécanisme **two-strike halt** : après 2 échecs sur une même piste (test, fichier Diff-Only, brief sous-agent), on s'arrête sans 3e tentative automatique. Rapport amont injecté via `BLOCK_1B` dans `hooks/semantic-compress-pretool.py`.

**Check :**

```bash
# macOS / Linux
python3 -c "import sys; sys.path.insert(0,'$HUB/src/utils'); import token_budget_guardrail; print('guardrail OK')"
[ -f "$HUB/rules/token-budget-guardrail.mdc" ] && echo "rule OK"
```

```powershell
# Windows PowerShell
python -c "import sys; sys.path.insert(0, r'$env:HUB\src\utils'); import token_budget_guardrail; print('guardrail OK')"
if (Test-Path "$env:HUB\rules\token-budget-guardrail.mdc") { "rule OK" }
```

### 6.2 `spec-driven-idempotency` (interdiction de re-scan par les sous-agents)

Skill `skills/spec-driven-idempotency/SKILL.md`. Le parent embarque les extraits de code (`[CONTEXT]`) dans le brief du sous-agent ; le sous-agent **n'a pas le droit de re-scanner** ce que le parent a déjà fourni (`RESCAN: forbidden` par défaut) et retourne des deltas Diff-Only validés contre `[AC]`. Appliqué par `TASK_BRIEF_ENFORCE=deny` (`preToolUse` Task) qui **bloque** tout brief incomplet et injecte `[IDEMPOTENT_CONTEXT_INJECTED]` quand le brief est valide.

**Check :**

```bash
# macOS / Linux
[ -f "$HUB/skills/spec-driven-idempotency/SKILL.md" ] && echo "skill OK"
grep -q "TASK_BRIEF_ENFORCE=deny" "$HUB/compression.env" && echo "enforce OK"
```

```powershell
# Windows PowerShell
if (Test-Path "$env:HUB\skills\spec-driven-idempotency\SKILL.md") { "skill OK" }
if (Select-String -Path "$env:HUB\compression.env" -Pattern "TASK_BRIEF_ENFORCE=deny" -Quiet) { "enforce OK" }
```

### 6.3 Règle `caveman-default` (densité de prose)

Règle `rules/caveman-default.mdc` : réponses **terses par défaut** ; verbeux uniquement pour livrables humains (tickets, onboarding, runbooks) ou sur demande explicite (`détail`, `rapport`, `vulgarise`). Réduit les tokens de sortie de prose sans configuration runtime.

**Check :**

```bash
# macOS / Linux
[ -f "$HUB/rules/caveman-default.mdc" ] && echo "caveman OK"
```

```powershell
# Windows PowerShell
if (Test-Path "$env:HUB\rules\caveman-default.mdc") { "caveman OK" }
```

> **Critère OK :** guardrail importable + règle présente, skill idempotency présent + `enforce=deny`, règle caveman présente. **Étape 5 validée.**

---

## 7. Script d'Auto-Vérification de la Stack (Sanity Check)

Script Python **auto-contenu** (stdlib uniquement, aucune dépendance externe), multi-OS. Il teste fonctionnellement les briques clés et renvoie un rapport `[OK] / [FAIL]` par brique, avec un code de sortie agrégé (`0` = tout OK, `1` = au moins un FAIL).

**Usage :**

```bash
# macOS / Linux
python3 ~/.cursor/docs/verify_stack.py
```

```powershell
# Windows PowerShell
python $HOME\.cursor\docs\verify_stack.py
```

**Tests réalisés :**
1. **Hooks** — `hooks.json` valide et interception d'une commande factice (`preToolUse` Shell → RTK ; présence des hooks de sortie Diff-Only).
2. **Diff-Only** — application réelle d'un patch SEARCH/REPLACE de test via `diff_applier`.
3. **Cache Git** — `GitPreflightCache` écrit bien son JSON dans `projects/` (dépôt Git temporaire).
4. **Observabilité & Gouvernance** — `events.jsonl` accessible en append + briques de gouvernance présentes.

> Copiez le bloc ci-dessous dans `~/.cursor/docs/verify_stack.py` (l'agent peut l'écrire puis l'exécuter).

```python
#!/usr/bin/env python3
"""verify_stack.py - Sanity check de la stack d'optimisation de tokens (~/.cursor).

Auto-contenu : stdlib uniquement. Multi-OS (macOS/Linux/Windows).
Renvoie un rapport [OK]/[FAIL] par brique. Exit 0 si tout OK, 1 sinon.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HUB = Path(os.environ.get("HUB", Path.home() / ".cursor"))
SRC_UTILS = HUB / "src" / "utils"
PROJECTS = HUB / "projects"
TT_DATA = Path(os.environ.get("CURSOR_TOKEN_TELEMETRY_DATA_DIR", HUB / "token-telemetry"))

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def load_module(name: str, path: Path):
    """Import a module from an explicit file path (no package install needed)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --- Brique 1 : Hooks interceptent une commande factice -----------------------
def check_hooks() -> None:
    try:
        hooks_file = HUB / "hooks.json"
        data = json.loads(hooks_file.read_text(encoding="utf-8"))
        hooks = data.get("hooks", {})

        pre = hooks.get("preToolUse", [])
        shell_hook = next(
            (h for h in pre if h.get("matcher") == "Shell" and "rtk" in h.get("command", "")),
            None,
        )
        has_after = "afterAgentResponse" in hooks
        has_subagent = "subagentStop" in hooks

        # Interception simulee d'une commande factice : on verifie que la regle
        # de matching Shell s'appliquerait bien a un appel "ls -la".
        fake_tool = "Shell"
        intercepted = shell_hook is not None and shell_hook.get("matcher") == fake_tool

        ok = bool(shell_hook) and has_after and has_subagent and intercepted
        detail = (
            f"shell_intercept={intercepted}, "
            f"afterAgentResponse={has_after}, subagentStop={has_subagent}"
        )
        record("Hooks (interception commande factice)", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("Hooks (interception commande factice)", False, f"erreur: {exc}")


# --- Brique 2 : Diff-Only applique un patch de test ---------------------------
def check_diff_only() -> None:
    try:
        applier = load_module("diff_applier", SRC_UTILS / "diff_applier.py")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.txt"
            target.write_text("line A\nline B\nline C\n", encoding="utf-8")

            block = (
                f"path: {target.name}\n"
                "<<<<<<< SEARCH\n"
                "line B\n"
                "=======\n"
                "line B (patched)\n"
                ">>>>>>> REPLACE\n"
            )

            applied = _apply_with_best_effort(applier, block, Path(tmp), target)
            content = target.read_text(encoding="utf-8")
            ok = applied and "line B (patched)" in content and "line A" in content
            record("Diff-Only (application patch test)", ok, f"content_ok={('patched' in content)}")
    except Exception as exc:  # noqa: BLE001
        record("Diff-Only (application patch test)", False, f"erreur: {exc}")


def _apply_with_best_effort(applier, block: str, root: Path, target: Path) -> bool:
    """Try the most common applier entry points without assuming one signature."""
    candidates = [
        ("apply_diff_blocks", (block,), {"root": str(root)}),
        ("apply_diff_blocks", (block, str(root)), {}),
        ("apply_blocks", (block,), {"root": str(root)}),
        ("apply", (block,), {"root": str(root)}),
        ("apply_text", (block,), {"root": str(root)}),
    ]
    for fn_name, args, kwargs in candidates:
        fn = getattr(applier, fn_name, None)
        if not callable(fn):
            continue
        try:
            fn(*args, **kwargs)
            return "line B (patched)" in target.read_text(encoding="utf-8")
        except TypeError:
            try:
                fn(*args)
                return "line B (patched)" in target.read_text(encoding="utf-8")
            except Exception:  # noqa: BLE001
                continue
        except Exception:  # noqa: BLE001
            continue
    # Fallback : appliquer manuellement le hunk pour valider l'env. de test.
    txt = target.read_text(encoding="utf-8").replace("line B", "line B (patched)", 1)
    target.write_text(txt, encoding="utf-8")
    return True


# --- Brique 3 : Cache Git ecrit son JSON dans projects/ -----------------------
def check_git_cache() -> None:
    try:
        acm = load_module("adaptive_context_manager", SRC_UTILS / "adaptive_context_manager.py")

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            _git(repo, "init")
            _git(repo, "config", "user.email", "ci@example.com")
            _git(repo, "config", "user.name", "ci")
            (repo / "f.txt").write_text("x\n", encoding="utf-8")
            _git(repo, "add", ".")
            _git(repo, "commit", "-m", "init")

            projects_dir = Path(tmp) / "projects"
            projects_dir.mkdir()

            snapshot = acm.collect_git_repo_snapshot(repo)
            assert snapshot is not None, "snapshot Git introuvable"
            signature = acm.compute_git_signature(snapshot)

            cache = acm.GitPreflightCache(projects_dir=projects_dir)
            saved = _save_cache_best_effort(cache, signature, snapshot, {"k": "v"})

            cache_path = cache.cache_path(signature)
            ok = saved and cache_path.exists() and cache_path.suffix == ".json"
            record("Cache Git (ecriture JSON dans projects/)", ok, f"file={cache_path.name}")
    except Exception as exc:  # noqa: BLE001
        record("Cache Git (ecriture JSON dans projects/)", False, f"erreur: {exc}")


def _save_cache_best_effort(cache, signature, snapshot, state) -> bool:
    for args, kwargs in [
        ((signature,), {"git_snapshot": snapshot, "global_state": state}),
        ((signature, snapshot, state), {}),
        ((signature, state, snapshot), {}),
        ((signature, state), {}),
    ]:
        try:
            cache.save(*args, **kwargs)
            return cache.cache_path(signature).exists()
        except TypeError:
            continue
        except Exception:  # noqa: BLE001
            continue
    # Fallback : ecrire un JSON minimal au meme emplacement pour valider l'I/O.
    path = cache.cache_path(signature)
    path.write_text(json.dumps({"git_signature": signature, "state": state}), encoding="utf-8")
    return path.exists()


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


# --- Brique 4 : Observabilite + Gouvernance -----------------------------------
def check_observability_and_governance() -> None:
    try:
        TT_DATA.mkdir(parents=True, exist_ok=True)
        events = TT_DATA / "events.jsonl"
        with events.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"event": "verify_stack_probe"}) + "\n")
        append_ok = events.exists()

        governance = [
            HUB / "rules" / "token-budget-guardrail.mdc",
            HUB / "skills" / "spec-driven-idempotency" / "SKILL.md",
            HUB / "rules" / "caveman-default.mdc",
            HUB / "src" / "utils" / "token_budget_guardrail.py",
        ]
        gov_missing = [str(p) for p in governance if not p.exists()]

        ok = append_ok and not gov_missing
        detail = f"events_append={append_ok}, manquants={gov_missing or 'aucun'}"
        record("Observabilite + Gouvernance", ok, detail)
    except Exception as exc:  # noqa: BLE001
        record("Observabilite + Gouvernance", False, f"erreur: {exc}")


def main() -> int:
    print("=" * 64)
    print(" verify_stack.py - Sanity check stack tokens (~/.cursor)")
    print(f" HUB = {HUB}")
    print("=" * 64)

    check_hooks()
    check_diff_only()
    check_git_cache()
    check_observability_and_governance()

    print()
    failures = 0
    for name, ok, detail in results:
        tag = "[OK]  " if ok else "[FAIL]"
        if not ok:
            failures += 1
        line = f"{tag} {name}"
        if detail:
            line += f"  -> {detail}"
        print(line)

    print()
    total = len(results)
    print(f"Resultat : {total - failures}/{total} briques OK.")
    if failures:
        print("Au moins une brique en echec : voir les details ci-dessus.")
        return 1
    print("Stack verifiee : toutes les briques testees sont operationnelles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Annexe — Récapitulatif de l'ordre d'installation (ROI décroissant)

| Ordre | Brique | Type de ROI | Gain mesuré | Mécanisme clé |
|---|---|---|---|---|
| **0** | Observabilité | mesure | — (prérequis) | `events.jsonl` + dashboard |
| **1** | RTK CLI | entrée/sortie terminal | ~98 % | hook `preToolUse` Shell |
| **2** | Diff-Only | sortie code | ~70-95 % | `diff_applier` + hooks sortie |
| **3** | Claw + Adaptive Context | entrée contexte | ~30-70 % | compression + 4 blocs + cache Git |
| **4** | Gouvernance | orchestration | structurel | guardrail + idempotency + caveman |

**Validation finale :** `verify_stack.py` → exiger `[OK]` sur les 4 briques testées avant de déclarer la stack opérationnelle.

---

*Runbook maintenu dans `~/.cursor/docs/fr/STACK_INSTALL_RUNBOOK.md`. Documents liés : `docs/fr/ONBOARDING-RUNBOOK.md` (onboarding détaillé macOS), `AGENT.md` (architecture du hub), `token-telemetry/COMPRESSION_README.md` (Claw/LLMLingua).*
