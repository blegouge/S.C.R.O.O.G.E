# Analyse critique d'expert IA — S.C.R.O.O.G.E. (Telemetry Token)

- **Date d'analyse** : 2026-07-24
- **Analyste** : Expert IA (revue indépendante, vérification par le code réel)
- **Branche / HEAD** : `main` @ `f6ae45f` (72 commits) — arbre de travail **propre**
- **Objet** : audit complet et noté de la stack (architecture, implémentation, mesure, CI, tests, sécurité, gouvernance, stack agents), avec axes d'amélioration
- **Posture** : critique et factuelle. Chaque note est adossée à une preuve vérifiée dans le code, pas à l'intention affichée.

> **Avertissement de méthode.** Les analyses précédentes du dossier `analysis/` ont été rédigées en partie par les assistants IA qui ont *construit* la stack. Elles convergent vers **8.3/10** et sont, à mon sens, **trop favorables** — notamment sur la couverture de tests et la « fiabilité de mesure ». Ce document **re-vérifie tout** et corrige plusieurs chiffres. Fait aggravant : le dépôt a été **restructuré aujourd'hui** (`899ebab`, `f6ae45f`, layout « domain-driven » `src/telemetry`, `src/compaction`, `src/bridge`), ce qui rend les analyses antérieures **périmées** sur les chemins et une partie des constats.

---

## 1. Ce que fait réellement la stack

S.C.R.O.O.G.E. est un **méta-outil** : il instrumente des agents de codage IA (Cursor, Claude Code, Gemini, Codex, Antigravity) via des *hooks*, *rules* et *skills* pour (a) **mesurer** la consommation de tokens et (b) **la réduire** par compression de contexte (Claw Compactor, LLMLingua-2, SmartCrusher, CCR, RTK, Diff-Only). La télémétrie part en `events.jsonl` (append-only, lock `fcntl`) puis se synchronise dans SQLite, et un dashboard local (HTTP `http.server` + JS vanilla) affiche des KPI et un graphe *counterfactuel* « usage observé vs consommation estimée sans optimisation ».

Stack technique : Python 3.12+ (cœur), JS vanilla ES-modules (dashboard), PyInstaller (app macOS), SQLite, tiktoken + tokenizer Claude offline (BPE, `tokenizer.json` 4,4 Mo embarqué), LLMLingua-2/transformers.

**Verdict d'ensemble** : artisanat de très bon niveau pour un projet personnel, avec une hygiène (lint/type/sécurité/CI) supérieure à la moyenne. Mais il porte une **faille conceptuelle structurante** (§5) et une **dette de tests réelle** masquée par une gate de couverture en trompe-l'œil (§4.5).

---

## 2. Scorecard critique (mes notes)

| Axe | Note antérieure (10/07) | **Ma note (24/07)** | Écart | Justification vérifiée |
|---|:---:|:---:|:---:|---|
| Architecture & design | 8.0 | **7.5** | ↘ | Découpage domain-driven sain, mais couplage fort à un écosystème de hooks maison ; monolithes résiduels. |
| Qualité d'implémentation | 7.7 | **7.5** | ↘ | Code propre, typé, fail-safe hooks. Mais `dashboard.js` 1294 l., `install_stack.py` 1049 l., hook compress 755 l. |
| **Fiabilité de la mesure** | 9.0 | **6.0** | ↘↘↘ | Tokenizers réels (bien), MAIS savings encore largement **modélisés** par coefficients ; auto-mesure sans vérité terrain (§5). Le 9.0 était surévalué. |
| Sécurité | 9.0 | **8.0** | ↘ | Host + token session + anti-traversal solides. Réserves : token en query-string, `bandit --skip` large, CVE `pip-audit` suppressée. |
| CI / CD | — | **7.5** | n/a | Pipeline complet (lint, mypy, bandit, gitleaks, pip-audit, tests 3.12/3.13). Mais mypy sur allowlist figée + `ignore_missing_imports`. |
| **Tests & couverture** | 8.0 | **5.5** | ↘↘ | Couverture réelle **67 %** (pas 82 %), plusieurs modules cœur à **0 %**. Gate 80 % ne couvre que `hub_files/src/utils`. |
| Respect des normes | 8.5 | **8.0** | ↘ | pre-commit strict, formatage auto. Mais version `pyproject` 1.0.0 ≠ CHANGELOG 1.1.0 ; `analysis/` **gitignoré**. |
| Gouvernance / repro | — | **6.5** | n/a | CHANGELOG/CONTRIBUTING/SECURITY présents ; pas de lockfile dev, versions Python hétérogènes. |
| Stack agents (approche) | 8.0 | **7.5** | ↘ | Approche riche et cohérente, mais guardrail = consigne (peu d'*enforcement* dur), qualité KV non benchmarkée. |

### Note globale pondérée : **~6.9 / 10**

> Écart franc avec le **8.3** annoncé précédemment. La divergence porte surtout sur **la mesure** et **les tests**, deux axes où les analyses antérieures ont pris les intentions/labels pour des garanties. Le projet reste **au-dessus de la moyenne**, mais le récit « stack mature pour un usage de production » est prématuré.

---

## 3. Architecture & implémentation

**Points forts**
- Restructuration `src/telemetry` / `src/compaction` / `src/bridge` : séparation des responsabilités saine, SSOT sur `telemetry_metrics.summarize_report` (parité `report.py` ↔ dashboard).
- Résolution de chemins robuste (dev vs PyInstaller frozen, multi-provider) ; `hook_fail_safe` évite qu'un hook plante l'éditeur (bonne défense en profondeur).
- Choix techno frugal (SQLite + `http.server` + JS vanilla) parfaitement dimensionné pour un outil local.

**Réserves**
- **Monolithes** persistants : `dashboard.js` (1294 l.), `install_stack.py` (1049 l.), `hub_files/hooks/semantic-compress-pretool.py` (755 l.) mélangent trop de responsabilités.
- **Couplage écosystémique fort** : la valeur dépend entièrement de l'installation d'un jeu de hooks/rules/skills maison et de coefficients calibrés. C'est un *lock-in méthodologique* : hors de cet écosystème, la stack ne mesure plus rien.
- Multiplication des branches (`feat/*`, `pr-11..16`, `temp/merge-*`) : hygiène Git à assainir.

---

## 4. Analyse détaillée

### 4.1 Fiabilité de la mesure de tokens — **6.0** (le point le plus surévalué)

**Ce qui est réel et bon**
- `estimate_tokens_with_source()` (`src/telemetry/telemetry_common.py`) utilise **tiktoken** (`o200k_base` pour GPT-4o/o1, sinon `cl100k_base`) et un **tokenizer Claude BPE offline**, avec `lru_cache` et fallback `proxy` (len/4). Le traçage `measurement_source` est une bonne idée.

**Ce qui pèche (et pourquoi 9.0 était faux)**
1. **Sélection d'encodage partielle** : Gemini n'a **aucun** tokenizer dédié → retombe sur `cl100k_base` (approximation). Le label « model-aware » est donc partiel.
2. **Le label conflate** : Claude tokenizer *exact* et tiktoken *approché* sont tous deux étiquetés `tokenizer` — impossible de distinguer *exact* vs *approché* côté dashboard.
3. **Les « économies » restent largement modélisées** :
   - `git_cache_savings_coefficient` (0.12) et `guardrail_savings_coefficient` (0.35) — coefficients (`telemetry_metrics.py:87`, `:128`).
   - Guardrail loop halt : `cycles = max(1, 4 - streak)` **codé en dur** (`:124`).
   - Diff-Only : `estimated_chars_saved / 4` (`:267`) — proxy pur.
   Le suffixe *(estimated)* rend l'affichage honnête, mais **ne transforme pas une estimation en mesure**.
4. **Fallback silencieux** : si tiktoken *et* le tokenizer Claude sont indisponibles, on bascule en `proxy` sans que la note globale s'en aperçoive.

### 4.2 Sécurité — **8.0**

Réellement solide pour un outil localhost (`dashboard/serve_dashboard.py`) :
- Validation stricte du header `Host` (anti DNS-rebinding), `secrets.token_hex(16)` par session, auth `/api/*`, anti directory-traversal (`is_relative_to`), pas de `shell=True`, timeouts sur `subprocess`.
- Tests dédiés `test_serve_security.py` (couverture 100 %).

**Réserves honnêtes**
- **Token accepté en query-string** (`?token=`) en repli du header → risque de fuite via logs/referrer. À restreindre au header.
- **`bandit --skip B101,B108,B110,B310,B404,B603,B607`** : skip large ; `B310` (urllib open) mérite justification explicite plutôt qu'un skip global.
- **`pip-audit ... --ignore-vuln PYSEC-2026-597`** : une CVE est **suppressée** en CI sans justification tracée dans le repo. À documenter (raison + échéance de levée).

### 4.3 CI/CD — **7.5**

`.github/workflows/ci.yml` : 3 jobs (lint+format, sécurité, tests matrix 3.12/3.13) + `verify_stack.py`. Sérieux.
- **Faiblesses** : `mypy` tourne sur une **allowlist figée** (`pyproject [tool.mypy] files=[...]`) → un nouveau module non listé **n'est pas typé-vérifié**. `ignore_missing_imports = true` global affaiblit le typage. Pas de cache de build PyInstaller ni de job macOS (l'`.app` n'est jamais construite en CI).

### 4.4 Respect des normes — **8.0**

pre-commit strict (ruff, mypy, prettier, gitleaks), config `pyproject` cohérente et épinglée. **Mais** : `version = "1.0.0"` dans `pyproject.toml` alors que le `CHANGELOG` est en **1.1.0** (incohérence non résolue depuis le 09/07).

### 4.5 Tests & couverture — **5.5** (correction majeure)

Suite **verte : 113 tests passent** (vérifié hors sandbox ; l'échec observé en sandbox = `git` indisponible, artefact d'environnement, pas une régression).

**MAIS la couverture réelle contredit le récit à 82 %** (mesurée sur `src/` + `hub_files/src/utils`) :

| Module cœur | Couverture |
|---|:---:|
| `src/compaction/token_compactor.py` | **0 %** |
| `src/compaction/headroom_adapter.py` | **0 %** |
| `src/compaction/claw_compactor_adapter.py` | **0 %** |
| `src/telemetry/rtk_resolver.py` | **0 %** |
| `src/bridge/hermes_telemetry_bridge.py` | **0 %** |
| `src/compaction/smart_crusher.py` | 49 % |
| `src/telemetry/telemetry_common.py` | 54 % |
| `src/telemetry/telemetry_paths.py` | 52 % |
| `hub_files/src/utils/flash_kv_summarizer.py` | 25 % |
| `hub_files/src/utils/diff_applier.py` | 60 % |
| **TOTAL** | **67 %** |

**Coverage theater** : `addopts = --cov=hub_files/src/utils --cov-fail-under=80`. La gate ne regarde **qu'un sous-répertoire** ; tout le cœur `src/` (compaction, mesure, bridge) peut régresser à 0 % **sans faire échouer la CI**. Le « 82 % » annoncé était un chiffre **local** à `utils/`, présenté comme global.

**Autre fragilité** : `test_adaptive_context_git_cache.py` fait de vrais `git init/commit` en `subprocess` dans un test **unitaire** → dépendance à un binaire externe, non hermétique. À reclasser en test d'intégration ou à mocker.

### 4.6 Gouvernance / reproductibilité — **6.5**

- `CHANGELOG` / `CONTRIBUTING` / `SECURITY.md` présents (bien), mais `SECURITY.md` est un template minimal.
- **`analysis/` est gitignoré** (`.gitignore` → `/analysis/`) : les analyses « brouillons de décision à annoter par le mainteneur » **ne sont pas versionnées** — contradiction avec leur rôle de traçabilité.
- Lockfiles desktop par OS présents, mais `requirements-dev.txt` (144 o) **non verrouillé** → CI dev non reproductible. Incohérence Python 3.12 (desktop) vs matrix 3.13.

### 4.7 Stack agents / réduction des coûts — **7.5**

Approche riche et cohérente (CCR, SmartCrusher, A/B, guardrail, diff-only). Réserves inchangées et réelles :
- **Guardrail = consigne textuelle** ; peu d'*enforcement* dur au niveau outil (hormis `TASK_BRIEF_ENFORCE=deny`).
- **CCR** : dé-duplication par **hash exact** seulement (pas de near-dup sémantique).
- **Qualité des résumés KV** non benchmarkée (pas de jeu de tests « contrainte préservée vs perdue »).
- Seuils (8 msg / 3000 tok) **fixes**, non adaptatifs.

---

## 5. La faille conceptuelle centrale : l'auto-mesure

C'est le point que les analyses précédentes n'ont jamais frontalement traité.

> **La télémétrie qui « prouve » la valeur de la stack est produite par la stack elle-même**, à partir de ses propres coefficients, sans vérité terrain externe.

Concrètement : le graphe *counterfactuel* « ce que vous auriez consommé sans optimisation » est **reconstruit** à partir de coefficients (`0.12`, `0.35`, `chars/4`, `4 - streak`) définis… par l'outil. Les claims README « saves up to 98 % / 95 % » sont donc **auto-référentiels**. Le framework A/B (groupe `control` sans compression) est le **seul** mécanisme qui pourrait fournir une mesure indépendante — mais il n'est pas activé par défaut et sa puissance statistique n'est pas démontrée.

Tant que la comptabilité ne s'appuie pas **prioritairement sur les `usage` réels des APIs** (`billed_total_tokens`, `cache_read/write`) avec les coefficients relégués en *fallback badgé*, la « fiabilité de mesure » ne peut honnêtement pas dépasser ~6/10.

---

## 6. Axes d'amélioration priorisés

### P0 — Crédibilité (impact note le plus fort)
1. **Restaurer la vérité de la couverture** : étendre `--cov` à `src/` entier et fixer une gate globale réaliste (ex. démarrer à 65 %, cliquet montant). Supprimer l'illusion « 82 % ».
2. **Mesurer plutôt qu'estimer** : prioriser `billed_total_tokens` + `cache_read/write` mesurés ; n'utiliser les coefficients qu'en fallback explicitement badgé `modélisé` dans le dashboard.
3. **Couvrir les modules à 0 %** : `token_compactor`, `headroom_adapter`, `claw_compactor_adapter`, `rtk_resolver`, `hermes_telemetry_bridge`.

### P1 — Robustesse & honnêteté
4. Distinguer `tokenizer_exact` (Claude) vs `tokenizer_approx` (tiktoken/Gemini→cl100k) dans `measurement_source`.
5. Sécurité : retirer le token en query-string (header only) ; documenter/justifier la CVE `pip-audit` suppressée et les skips bandit.
6. mypy : passer d'une allowlist figée à un scan par répertoire (`src/`, `hub_files/src/utils/`).
7. Reclasser `test_adaptive_context_git_cache` en test d'intégration (ou mocker git).

### P2 — Dette & gouvernance
8. Découper les monolithes (`dashboard.js` → bootstrap < 300 l., `install_stack.py` en étapes testables, extraire le pipeline de compression du hook 755 l.).
9. Aligner la version (`pyproject` ↔ `CHANGELOG`), ajouter `requirements-dev.lock`, unifier la cible Python.
10. Décider du statut de `analysis/` (versionner ou assumer explicitement l'exclusion) ; nettoyer les branches Git.
11. Stack agents : *enforcement* dur du guardrail (hook `preToolUse`), benchmark qualité KV, CCR near-dup sémantique.

---

## 7. Conclusion

S.C.R.O.O.G.E. est un projet **techniquement soigné et ambitieux** : sécurité localhost sérieuse, CI complète, tokenizers réels, architecture propre après restructuration. Il mérite le respect pour un projet personnel.

Mais la revue indépendante fait tomber la note de **8.3 à ~6.9/10**, pour deux raisons factuelles et non cosmétiques :
1. **La couverture de tests est en trompe-l'œil** : 67 % réels, plusieurs modules cœur à 0 %, gate limitée à un sous-dossier.
2. **La mesure reste largement heuristique et auto-référentielle** : l'outil valide ses propres gains avec ses propres coefficients, sans vérité terrain.

Le meilleur ratio effort/gain est clair : **rendre la mesure auditable (P0-2) et la couverture honnête (P0-1)**. Tant que ces deux points ne sont pas traités, la stack doit être présentée comme un **prototype instrumenté crédible**, pas comme une « télémétrie de production ».
