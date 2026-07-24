# Analyse critique — S.C.R.O.O.G.E. (Telemetry Token) — Synthèse & gaps restants

- **Date d'analyse** : 2026-07-09
- **Documents précédents** :
  - `2026-07-07-analyse-projet-SCROOGE.md` (initial)
  - `2026-07-07-analyse-projet-SCROOGE-post-P0.md`
  - `2026-07-07-analyse-projet-SCROOGE-post-P1.md`
- **Branche** : `main` — HEAD **`89e42d5`**
- **Objet** : nouvelle passe de vérification, comparatif avant/après sur toute la trajectoire, et roadmap des gaps pour améliorer la note
- **Statut** : brouillon de décision — à annoter par le mainteneur

> Cette synthèse consolide les 3 analyses précédentes et **vérifie l'état réel du code** après 11 commits post-P1 (`020be54` → `89e42d5`). **102 tests passent**, couverture **81.76 %** (seuil 80 % atteint sur `hub_files/src/utils`).

---

## 1. Brief comparatif des notes (avant → après)

| Axe | Initial<br>(07/07 matin) | Post-P0<br>(07/07 AM) | Post-P1<br>(07/07 PM) | **Actuel<br>(09/07)** | Δ total | Trajectoire |
|---|---:|---:|---:|---:|---:|---|
| Architecture & design | 7.5 | 7.5 | 7.5 | **8.0** | +0.5 | Dashboard découpé en modules ES ; `ConfigManager` centralisé ; A/B intégré au pipeline |
| Maintenabilité | 6.0 | 6.5 | 7.0 | **7.5** | +1.5 | Lockfile Python, mypy durci, chemins génériques ; `install_stack.py` et hook 755 l. restent lourds |
| Sécurité | 7.0 | 7.0 | 8.5 | **9.0** | +2.0 | Host + token + CORS retiré ; **7 tests sécurité** (`test_serve_security.py`) |
| Respect des normes | 7.5 | 8.0 | 8.0 | **8.5** | +1.0 | `CHANGELOG` / `CONTRIBUTING` / `SECURITY` ; `--cov-fail-under=80` |
| Qualité des tests | 5.0 | 6.0 | 6.0 | **7.5** | +2.5 | **102 tests** (+21), 16 modules ; couverture 82 % sur `utils` ; racine toujours peu couverte |
| Fiabilité mesure tokens | 4.0 | 6.5 | 7.5 | **8.0** | +4.0 | tiktoken model-aware propagé, cache provider-aware, coeffs configurables, A/B ; reste heuristique |
| Stack agents / coûts | 8.0 | 8.0 | 8.0 | **8.0** | = | Approche inchangée ; qualité du résumé KV et enforcement dur non évalués |

### Note globale pondérée

| Jalón | Note |
|---|---:|
| **Initial** (07/07 matin) | **~6.4 / 10** |
| Post-P0 | ~7.0 |
| Post-P1 | ~7.6 |
| **Actuel** (09/07) | **~8.0 / 10** |

**Lecture en une phrase** : en deux jours, le projet est passé d'un prototype crédible sur la forme mais fragile sur la mesure, à une stack **défendable** (sécurité, tests, gouvernance) avec une comptabilité tokens **sérieusement améliorée** — il reste surtout à **mesurer plutôt qu'estimer** et à **étendre les tests au cœur racine**.

---

## 2. Bilan consolidé : ce qui a été traité

### P0 — 4/4 ✅ (commit `49ccd5e`)
- tiktoken + cache LRU (`telemetry_common.estimate_tokens`)
- Libellés KPI *(estimated/estimé)* + README qualifié
- Tests `telemetry_metrics.py`
- Alignement ruff/mypy (pre-commit + CI)

### P1 — 6/7 ✅ (commit `f10f9d8`)
- Comptabilité cache-aware (`adjusted_billed_sum`, `cache_read/write_sum`)
- Sécurité serveur (Host, token session, CORS retiré, auth `/api/*`)
- Plafond transcript 500 k car.
- Chemins/username en dur supprimés (`install_stack.py`)
- `pip-audit` bloquant en CI

### P1-bis — 4/4 ✅ (commits `020be54`, `23eb1a5`, `6bb5f74`, `3a12f8d`)
| Action | Statut | Preuve |
|---|---|---|
| Propagation `model_name` → `estimate_tokens` | ✅ | `semantic-compress-pretool.py` lit `model` / `CODEX_MODEL` / `CURSOR_MODEL` ; fallback env dans `telemetry_common._get_tiktoken_encoding` |
| Poids cache **provider-aware** | ✅ | `telemetry_metrics._cache_read_weight()` : 0.1× Claude/Gemini, 0.5× GPT/o1/o3 |
| Tests sécurité + cache-aware | ✅ | `test_serve_security.py` (7 tests) ; `test_telemetry_metrics.py` étendu (cache + provider weights + A/B) |
| Framework **A/B** + coeffs configurables | ✅ | `AB_TEST_ENABLED` / `AB_TEST_RATIO` ; groupe `control` sans compression ; `GIT_CACHE_SAVINGS_COEFFICIENT` / `GUARDRAIL_SAVINGS_COEFFICIENT` via `ConfigManager` ; KPI `ab_test` dans `summarize_report` + section dashboard |

### P2 — partiellement traité (Wave 1, commit `6bb5f74` + `feb24bb`)
| Action P2 | Statut | Détail |
|---|---|---|
| Découper `dashboard.js` | ⚠️ **Partiel** | 6 modules ES (`dashboard_api.js`, `_charts`, `_stats`, `_tables`, `_translations`, `_utils`) ; orchestrateur `dashboard.js` encore **1 281 l.** |
| Réduire mypy laxiste | ✅ | `check_untyped_defs = true` ; `ignore_errors` supprimé ; `telemetry_common`/`telemetry_metrics` ajoutés au scope |
| Lockfile Python | ⚠️ **Partiel** | `requirements-desktop.lock` présent ; pas de lock dev (`requirements-dev`) |
| Gouvernance repo | ✅ | `CHANGELOG.md` (v1.1.0), `CONTRIBUTING.md`, `SECURITY.md` |
| `--cov-fail-under` | ⚠️ **Partiel** | Gate 80 % actif, mais **uniquement sur `hub_files/src/utils`** — pas sur `serve_dashboard`, `telemetry_metrics` racine, `install_stack` |
| Tests `serve_dashboard` / `install_stack` | ⚠️ **Partiel** | Sécurité couverte ; pas de tests API complète ni installeur |
| CCR sémantique / seuils adaptatifs / guardrail dur | ❌ | Non fait |

---

## 3. Ce qui reste en suspens (gaps par impact sur la note)

### 🔴 Gap 1 — Mesure encore partiellement heuristique (impact : **Fiabilité mesure** 8.0 → 9.0)

**Constat** : les coefficients counterfactuels sont désormais **configurables** (`GIT_CACHE_SAVINGS_COEFFICIENT=0.12`, `GUARDRAIL_SAVINGS_COEFFICIENT=0.35`) et calibrables via A/B, mais :
- le cache Git et le guardrail **n'utilisent pas** les `usage` réels des APIs quand disponibles ;
- `diff_only_saved_tokens` reste `chars_saved / 4` ;
- les cycles guardrail `4 - streak` sont toujours codés en dur ;
- **Claude/Anthropic** n'a pas de tokenizer dédié (tiktoken `cl100k_base` reste une approximation pour les modèles Anthropic).

**Actions recommandées** :
1. Prioriser `billed_total_tokens` + `cache_read/write` **mesurés** quand présents ; ne retomber sur les coeffs qu'en fallback explicite (badge « modélisé »).
2. Brancher un compteur Anthropic (API `count_tokens` ou lib dédiée) pour les événements `claude-*`.
3. Documenter dans le dashboard la **source** de chaque KPI : `measured` | `estimated` | `configured`.

**Gain estimé** : +0.5 à +1.0 sur « Fiabilité mesure » → **+0.1 à +0.15** sur la note globale.

---

### 🟠 Gap 2 — Couverture de tests limitée au périmètre `utils/` (impact : **Tests** 7.5 → 8.5)

**Constat** :
- 102 tests, 82 % de couverture — **mais** le scope `--cov` ne couvre que `hub_files/src/utils`.
- Modules racine critiques **non couverts par la gate** : `serve_dashboard.py` (hors sécurité), `telemetry_metrics.py`, `telemetry_db.py`, `install_stack.py`, `report.py`.
- `install_stack.py` (~1 063 l.) : **0 test**.

**Actions recommandées** :
1. Étendre `--cov` à `telemetry_metrics.py`, `serve_dashboard.py`, `telemetry_db.py`.
2. Tests d'intégration HTTP : `/api/events`, `/api/report-summary`, sync SQLite, POST layout avec token.
3. Tests smoke `install_stack.py` (dry-run / mock filesystem).

**Gain estimé** : +0.5 à +1.0 sur « Qualité tests » → **+0.1** global.

---

### 🟠 Gap 3 — Monolithes résiduels (impact : **Maintenabilité** 7.5 → 8.5)

**Constat** :
| Fichier | Lignes | Évolution |
|---|---:|---|
| `dashboard.js` | 1 281 | ↓ de ~2 900 (modularisation ES) mais orchestrateur encore gros |
| `install_stack.py` | 1 063 | ≈ inchangé |
| `semantic-compress-pretool.py` | 755 | ↑ (A/B + model propagation) |

**Actions recommandées** :
1. Extraire la logique A/B et compression de `semantic-compress-pretool.py` vers un module `utils/compression_pipeline.py`.
2. Découper `install_stack.py` en étapes (`detect_hub`, `write_secrets`, `install_hooks`, `verify`).
3. Réduire `dashboard.js` à un bootstrap < 300 l. (tout le reste déjà en modules).

**Gain estimé** : +0.5 sur « Maintenabilité » → **+0.07** global.

---

### 🟡 Gap 4 — Stack agents : qualité et enforcement non mesurés (impact : **Stack agents** 8.0 → 8.5)

**Constat** (inchangé depuis l'analyse initiale) :
- **Guardrail** = consigne textuelle ; pas de blocage outil (sauf task-brief `deny`).
- **Résumé KV heuristique** : pas de jeu de tests « contrainte préservée / perdue ».
- **CCR** : dé-duplication par hash exact uniquement (pas de near-dup sémantique).
- **Seuils** (8 msg / 3000 tok / 1200 chars) : fixes, non adaptatifs.

**Actions recommandées** :
1. Benchmark qualité KV : 20–30 scénarios avec assertions sur contraintes critiques.
2. POC CCR sémantique (embeddings locaux ou MinHash sur blocs > 4 k chars).
3. Guardrail dur : bloquer `Read` > N lignes sans preuve RTK (hook `preToolUse`).

**Gain estimé** : +0.5 sur « Stack agents » → **+0.07** global.

---

### 🟡 Gap 5 — Finitions mineures

| Item | Statut | Action |
|---|---|---|
| Token en query string (`?token=`) | ⚠️ | Documenter risque referrer ; préférer header uniquement |
| `hub_files/skills/README.md` | ⚠️ | Encore un chemin `/Users/blegouge/.antigravity/skills/` en dur |
| Dossier `analysis/` | ⚠️ | 3 docs versionnés ; ce document à ajouter au suivi git |
| Lockfile dev | ❌ | Ajouter `requirements-dev.lock` pour CI reproductible |
| Version projet | ℹ️ | `CHANGELOG` annonce **1.1.0** mais `pyproject.toml` reste **1.0.0** — aligner |

---

## 4. Roadmap pour améliorer la note (priorisée)

### Wave 2 — Mesure auditable (2–3 semaines) → cible **~8.3**
- [ ] Schéma événement : champ `measurement_source` (`api_usage` | `tiktoken` | `coefficient` | `proxy`)
- [ ] Prioriser tokens mesurés API ; coeffs en fallback documenté
- [ ] Tokenizer Anthropic pour événements Claude
- [ ] Étendre `--cov` aux modules racine critiques

### Wave 3 — Robustesse produit (1 mois) → cible **~8.5**
- [ ] Tests intégration HTTP complets (`serve_dashboard`)
- [ ] Tests smoke `install_stack` (mock)
- [ ] Refactor `semantic-compress-pretool.py` + `install_stack.py`
- [ ] Aligner version `pyproject` ↔ `CHANGELOG`

### Wave 4 — Stack agents avancée (trimestre) → cible **~8.7–9.0**
- [ ] Benchmark qualité résumé KV
- [ ] CCR sémantique (near-dup)
- [ ] Guardrail enforcement dur (tool-layer)
- [ ] Seuils adaptatifs par modèle/tâche

---

## 5. Projection de note si gaps fermés

| Scénario | Note estimée | Conditions |
|---|---:|---|
| **Actuel** (09/07) | **~8.0** | État vérifié |
| Wave 2 complète | ~8.3 | Mesure majoritairement API + cov étendue |
| Wave 2 + 3 | ~8.5 | Tests racine + refactor monolithes |
| Wave 2 + 3 + 4 | ~8.8–9.0 | Stack agents mesurée et enforceable |

---

## 6. Conclusion

Le projet a **consommé quasi intégralement** les plans P0, P1 et P1-bis identifiés dans les analyses du 07/07, et entamé le P2 (gouvernance, modularisation dashboard, mypy durci, lockfile desktop, gate couverture). La trajectoire est nette : **+1.6 point** en deux jours sur la note globale (~6.4 → ~8.0), portée surtout par la **fiabilité de mesure** (+4.0) et la **sécurité** (+2.0).

Les gaps restants ne sont plus des « fondations manquantes » mais des **finitions de produit** :
1. **Mesurer plutôt qu'estimer** (le levier n°1 pour la crédibilité),
2. **Étendre les tests** au-delà de `hub_files/src/utils`,
3. **Réduire les monolithes** résiduels,
4. **Évaluer et durcir** la stack agents (qualité KV, enforcement).

La recommandation immédiate : lancer **Wave 2** (mesure auditable + cov étendue) — c'est le meilleur ratio effort/gain pour passer de **8.0 à ~8.3** sans toucher à l'architecture agents.
