<p align="center">
  <img src="assets/icon.jpg" alt="S.C.R.O.O.G.E Logo" width="160" style="border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);" />
</p>

# 🚀 S.C.R.O.O.G.E - Context Optimization & Telemetry Stack

> **Métriques locales par proxy et compression intelligente des invites (prompts) pour les IDE de nouvelle génération**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Platform: macOS | Linux | Windows](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey.svg)](#)
[![Supported IDEs: Cursor | Antigravity | Claude Code | Gemini | Codex](https://img.shields.io/badge/IDEs-Cursor%20%7C%20Antigravity%20%7C%20ClaudeCode%20%7C%20Gemini%20%7C%20Codex-purple.svg)](#)
[![Licence: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../../LICENSE)

S.C.R.O.O.G.E (Smart Context Reducer & Optimized Observability Governance Engine) est une suite locale de métriques de proxy de développement et d'optimisation conçue pour mesurer, visualiser et réduire considérablement le coût d'exécution des workflows de programmation assistés par IA. Elle intercepte automatiquement les requêtes d'agent, applique des stratégies de compression agressives et surveille la conformité de l'espace de travail en temps réel.

---

## 📸 Aperçu du Dashboard

### 📊 Métriques principales et Gains
Le tableau de bord propose un thème "style terminal" néon sombre avec des cartes de KPI, des histogrammes de tokens en temps réel et un graphique factuel affichant l'utilisation observée par rapport à la consommation estimée sans optimisations.
![Main Dashboard View](assets/dashboard_main.png)

### 🔍 Détails des sous-agents et Conformité
Faites défiler vers le bas pour suivre chaque session de sous-agent, analyser les contrôles de conformité aux règles (par exemple, les rapports de consommation, la vérification des briefs de tâche) et identifier les outils générant le plus d'économies.
![Detailed View](assets/dashboard_details.png)

---

## ✨ Fonctionnalités Clés

1. **📊 Télémétrie locale S.C.R.O.O.G.E**
   - Enregistre les métriques de manière asynchrone dans un fichier local `events.jsonl`, puis les synchronise de façon incrémentale dans une base SQLite centrale (`telemetry.db`).
   - Les endpoints de requêtes interrogent directement la base SQLite indexée pour des recherches rapides en O(log N).
   - S'exécute aussi comme une **App macOS Desktop native** (via PyInstaller) pour une expérience autonome sans navigateur.

2. **🗜️ Compression de contexte & Optimisations**
   - **RTK Gain** : S'intègre avec les économies de commandes shell (jusqu'à 98% d'économie sur les exécutions de commandes).
   - **Protocole Diff-Only** : Applique des correctifs de type SEARCH/REPLACE pour éviter de réécrire des fichiers entiers, économisant jusqu'à 95% des tokens de sortie.
   - **Claw Compactor & LLMLingua** : Réduit la taille du contexte dynamique en élaguant les informations de faible importance avant l'envoi de la requête.
   - **Moteurs locaux Headroom** : `SmartCrusher` (élagage structurel) et `CCR` (Compress-Cache-Retrieve) pour les gros blocs de logs.

3. **🔄 Routage de contexte adaptatif**
   - Assemble les requêtes de manière déterministe :
     1. `BLOCK_1` : Règles système globales, règles Cursor locales et skills actives.
     2. `BLOCK_1B` : Garde-fous du budget de tokens.
     3. `BLOCK_2` : État Git et Workspace.
     4. `BLOCK_3` : Historique des messages compressé.
     5. `BLOCK_4` : Dernière requête utilisateur.
   - Compacte l'historique au-delà des seuils configurés (défauts code : 8 messages / 3000 tokens ; le `compression.env` livré les monte à 10 / 4000). Voir [ADAPTIVE_CONTEXT_ROUTING.md](../../ADAPTIVE_CONTEXT_ROUTING.md).

4. **⚡ Cache Git Pré-flight**
   - Calcule une signature basée sur `git branch + HEAD SHA + modified files`.
   - Réutilise instantanément les états d'espace de travail déjà compactés, évitant un appel de résumé LLM redondant.

5. **🛡️ Conformité et Gouvernance**
   - Bloque les sous-agents si le brief de tâche est manquant ou invalide.
   - Valide que l'agent génère un rapport de consommation structuré à la fin de chaque tour.
   - Tous les hooks utilisent une enveloppe d'exécution fail-safe pour s'assurer qu'aucun crash de script ne bloque l'éditeur de code.

---

## 📂 Structure du Dépôt

Le cœur Python est packagé sous `src/`, l'interface sous `dashboard/`, et tout ce qui est déployé dans un hub d'agent/IDE (`~/.cursor`, `~/.codex`, `~/.gemini/antigravity`, …) réside sous `hub_files/`.

| Chemin | Description |
|---|---|
| 🛠️ [install_stack.py](../../install_stack.py) | Script d'installation interactif, idempotent et automatisé. |
| 📁 [src/telemetry/](../../src/telemetry/) | Cœur télémétrie : base SQLite ([telemetry_db.py](../../src/telemetry/telemetry_db.py)), résolution des chemins/providers ([telemetry_paths.py](../../src/telemetry/telemetry_paths.py), [providers_config.py](../../src/telemetry/providers_config.py)), configuration ([telemetry_config.py](../../src/telemetry/telemetry_config.py)), agrégation des KPI ([telemetry_metrics.py](../../src/telemetry/telemetry_metrics.py)), taxonomie mesuré/modélisé ([measurement_source.py](../../src/telemetry/measurement_source.py)), résolveur du binaire RTK ([rtk_resolver.py](../../src/telemetry/rtk_resolver.py)). |
| 📁 [src/compaction/](../../src/compaction/) | Moteurs de compression : LLMLingua ([token_compactor.py](../../src/compaction/token_compactor.py)), adaptateur Claw ([claw_compactor_adapter.py](../../src/compaction/claw_compactor_adapter.py)), adaptateur Headroom ([headroom_adapter.py](../../src/compaction/headroom_adapter.py)), SmartCrusher ([smart_crusher.py](../../src/compaction/smart_crusher.py)), cache CCR ([ccr_manager.py](../../src/compaction/ccr_manager.py)). |
| 📁 [src/bridge/](../../src/bridge/) | Ingestion de logs externes dans la télémétrie ([hermes_telemetry_bridge.py](../../src/bridge/hermes_telemetry_bridge.py)). |
| 📁 [dashboard/](../../dashboard/) | SPA web ([dashboard.html](../../dashboard/dashboard.html), JS/CSS), backend HTTP ([serve_dashboard.py](../../dashboard/serve_dashboard.py)) et chargeur de fenêtre native ([dashboard_app.py](../../dashboard/dashboard_app.py)). |
| 📁 [cli/](../../cli/) | Outil de rapport en terminal ([report.py](../../cli/report.py)). |
| 📁 [hub_files/](../../hub_files/) | Couche d'intégration agent/IDE déployée dans le hub : `hooks/` (télémétrie, Diff-Only, RTK, compression, conformité), `providers/` (détection par IDE), `rules/` (`*.mdc`), `skills/`, `src/utils/` (adaptive context manager, diff applier, garde-fous, résumeurs + tests unitaires) et `bin/` (scripts utilitaires). |
| 📁 [docs/](../../docs/) | Documentation et vérificateur post-installation ([verify_stack.py](../verify_stack.py)). |
| 📁 [examples/](../../examples/) | Exemples d'intégration : middleware de compression et smoke test du flash summarizer. |
| 📁 [native_app/](../../native_app/) | Spec PyInstaller ([SCROOGE.spec](../../native_app/SCROOGE.spec)) pour le bundle `.app` macOS. |

---

## 🚀 Guide d'Installation

Clonez le dépôt (le nom du dossier ne doit pas se terminer par un point — requis sous Windows) :

```bash
git clone git@github.com:blegouge/S.C.R.O.O.G.E.git
cd S.C.R.O.O.G.E
```

Exécutez l'installateur automatisé depuis la racine du dépôt :

```bash
python3 install_stack.py
```

### Ce que fait l'installateur :
1. **Sélection du dossier cible (Hub)** : Détecte et déploie les templates de configuration dans `~/.cursor`, `~/.gemini/antigravity`, `~/.codex` ou un emplacement personnalisé.
2. **Dossier de codebases** : Demande le chemin de votre dossier de projets pour configurer le MCP code-explorer.
3. **Moteur de compression** : Configure l'utilisation de `claw`, `headroom`, les deux (`both`), ou désactive la compaction.
4. **uv / uvx** : Propose d’installer Astral uv (fournit uvx) s’il est absent, selon l’OS, avec confirmation.
5. **Configuration interactive des secrets** : Récupère vos clés d'API (Grafana, GitHub, MySQL, etc.) et les stocke dans un fichier `.env` sécurisé (`chmod 600`).
6. **Environnement virtuel Python** : Crée un environnement dédié `.venv-desktop` et y installe les dépendances.
7. **Normalisation des règles/skills** : Réécrit dynamiquement les références textuelles selon l'IDE cible (Cursor, Antigravity, Claude Code ou Codex).
8. **Validation** : Exécute [docs/verify_stack.py](../verify_stack.py) pour valider l'état fonctionnel de chaque brique.
9. **Lancement de service** : Propose de lancer automatiquement le démon du dashboard en tâche de fond sur le port `8765`.

---

## ⚙️ Vue d'ensemble des configurations

### 1. `compression.env`
Définit les paramètres et seuils pour la compression de contexte (voir [hub_files/compression.env.example](../../hub_files/compression.env.example)) :
```ini
# Configuration de la compression de contexte
COMPRESSION_BACKEND=claw
# deny = bloque les briefs invalides, warn = journalise seulement, off = ignore
TASK_BRIEF_ENFORCE=warn
LLMLINGUA_HOOK_RATE=0.5
LLMLINGUA_HOOK_MIN_CHARS=2500
ADAPTIVE_CTX_TOKEN_THRESHOLD=4000
ADAPTIVE_CTX_MESSAGE_THRESHOLD=10
CCR_ENABLED=1
CCR_THRESHOLD_CHARS=4000
SMART_CRUSHER_N=10
SMART_CRUSHER_M=10
```

### 2. `mcp.secrets.env`
Stocke les clés d'API et identifiants privés chargés par les scripts wrappers MCP :
```ini
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_...
GRAFANA_API_TOKEN=glsa_...
MYSQL_PASSWORD=...
```

### 3. `hooks.json` & `mcp.json`
Situés dans le dossier Hub (ex: `~/.cursor/` ou `~/.codex/`), ils définissent les hooks actifs (ex: `postToolUse`, `afterAgentResponse`) et enregistrent les serveurs MCP locaux.

---

## 🖥️ Utilisation

### Rapport en Terminal
Affichez le résumé de consommation de votre session active (depuis la racine du dépôt) :
```bash
python3 cli/report.py
```

### Lancement du Dashboard Web
Si vous ne l'avez pas lancé lors de l'installation, exécutez :
```bash
python3 dashboard/serve_dashboard.py
# Ouvrir http://127.0.0.1:8765/
```

### Compilation en Application macOS autonome (`.app`)
Pour générer un exécutable double-cliquable dans votre Dock macOS :
```bash
./build_macos_app.sh
```
Cela générera `dist/SCROOGE.app` via PyInstaller, inclura l'icône de l'application et effectuera une signature locale.

---

## 🔒 Confidentialité & Rotation
Les charges utiles échangées avec l'assistant (pouvant contenir du code, des clés de projets ou des chemins de fichiers locaux) sont journalisées exclusivement en local dans le fichier `events.jsonl`.
Gardez ce fichier privé et effectuez des rotations ou purges régulières.
