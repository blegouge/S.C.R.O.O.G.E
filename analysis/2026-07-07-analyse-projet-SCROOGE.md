# Analyse critique — S.C.R.O.O.G.E. (Telemetry Token)

- **Date d'analyse** : 2026-07-07
- **Branche** : `main` (dernier commit `d5703ef`)
- **Périmètre** : maintenabilité, sécurité, respect des normes, axes d'évolution, et évaluation spécifique de la *stack agents / réduction de coûts en tokens*
- **Statut du document** : brouillon de décision — à annoter par le mainteneur

> Ce document est volontairement **critique**. Les points forts sont réels et nombreux, mais l'objectif ici est de faire ressortir les risques et les leviers d'amélioration pour prioriser.

---

## 1. Note globale (scorecard)

| Axe | Note /10 | Tendance | Commentaire synthétique |
|---|---|---|---|
| Architecture & design | 7.5 | ↗ | Séparation par providers, SSOT `telemetry_paths`/`telemetry_metrics`, pipeline en blocs déterministes. Quelques monolithes. |
| Maintenabilité | 6.0 | → | Bonne base typée, mais fichiers trop gros, dérive de versions d'outils, chemins personnels en dur. |
| Sécurité | 7.0 | ↗ | Hygiène secrets correcte, CI sécurité présente. Faiblesses : CORS `*`, endpoint non authentifié, mypy laxiste. |
| Respect des normes | 7.5 | ↗ | PEP 621, PEP 8 (ruff), typage PEP 604, pre-commit, MIT. Manque quelques fichiers de gouvernance. |
| Qualité des tests | 5.0 | → | 11 modules de tests sur `hub_files/src/utils` uniquement. **Le cœur métier (calcul des économies, serveur HTTP, installeur) n'est pas testé.** |
| Fiabilité de la mesure de tokens | 4.0 | ⚠ | Point le plus faible : estimation `len/4` + coefficients heuristiques inventés. Voir §5. |
| Stack agents / réduction coûts (approche) | 8.0 | ↗ | Approche riche, multi-couches, originale et bien pensée conceptuellement. |

**Note moyenne pondérée : ~6.4 / 10** — Projet solide et ambitieux, avec une ingénierie soignée sur la forme, mais dont la **crédibilité du chiffrage** (sa proposition de valeur centrale) et la **couverture de tests du cœur métier** sont les deux talons d'Achille.

---

## 2. Vue d'ensemble du projet

Stack locale (Python 3.12+ / JS vanilla) qui :
- intercepte / journalise les événements d'agents IA (`events.jsonl` → SQLite `telemetry.db`),
- applique plusieurs stratégies de compression de contexte (Claw Compactor, LLMLingua, SmartCrusher, CCR),
- réassemble les prompts en blocs *cache-friendly* et compacte l'historique,
- expose un dashboard HTTP local (`127.0.0.1:8765`) + CLI `report.py` + app macOS (PyInstaller),
- impose une gouvernance (task-brief validator, consumption report, token-budget guardrail).

Volumétrie : ~4 400 lignes Python racine, ~3 500 lignes `hub_files/src/utils`, ~2 000 lignes de hooks, `dashboard.js` ~2 900 lignes, 153 fichiers versionnés.

---

## 3. Points forts (à préserver)

- **Hygiène des secrets** : `.env`, `compression.env`, `telemetry.db`, `ccr_cache/` sont `.gitignore`. Seuls des templates `*.example` sont versionnés. Fichier secrets écrit en `chmod 600`.
- **CI complète** (`.github/workflows/ci.yml`) : ruff (lint+format), mypy, ESLint, Prettier, **bandit + pip-audit + gitleaks**, tests sur matrice 3.12/3.13, puis `verify_stack.py`.
- **Typage moderne** : `from __future__ import annotations`, `dataclass(slots=True)`, unions PEP 604, `TypedDict`-like dicts.
- **SSOT** : `telemetry_paths.py` (chemins), `telemetry_metrics.py` partagé entre `report.py` et le dashboard → parité CLI/UI garantie.
- **Sous-processus sûrs** : appels `subprocess.run` avec listes d'arguments, `timeout`, `check=False`, **jamais `shell=True`**, pas de `eval`/`exec`/`pickle`.
- **Serveur borné localhost** + limite de taille de body POST (`> 65536` rejeté) + parsing JSON défensif.
- **Idées d'architecture fortes** : ordre de blocs déterministe pour saturer le cache de prompt, cache Git *pre-flight* sans appel LLM, fallbacks en cascade (flash → heuristique).

---

## 4. Problèmes de maintenabilité

### 4.1 Dérive de versions d'outillage (à corriger vite, faible effort)
- `pre-commit` épingle **ruff v0.3.0** et **mypy v1.9.0**, alors que `pyproject.toml` exige **ruff>=0.15.20** et **mypy>=2.1.0**.
- La CI installe `ruff`/`mypy` **sans épinglage** (`pip install ruff mypy`) → version « latest » différente encore.
- **Conséquence** : trois sources de vérité divergentes ; un lint qui passe en local peut échouer en CI (et inversement). Aligner les trois.

### 4.2 Chemins et identité personnels codés en dur
- `install_stack.py` (`rewrite_config_content`) contient `/Users/blegouge/.cursor`, `/Users/blegouge/www`, `/Users/blegouge`, `/Users/blegouge/.gemini/antigravity` en remplacement littéral.
- **Problèmes** : fuite du nom d'utilisateur de l'auteur dans un dépôt destiné à d'autres, non portable, et **réécriture de config par `str.replace` en cascade** = fragile (ordre-dépendant, risque de double substitution).
- Recommandation : dériver depuis `Path.home()` / variables d'environnement, et remplacer la réécriture par un rendu de templates (placeholders `{{...}}` déjà partiellement présents — généraliser).

### 4.3 Monolithes
- `dashboard.js` (~2 900 l.), `install_stack.py` (~1 050 l.), `hooks/semantic-compress-pretool.py` (703 l.), `telemetry_metrics.py` (539 l.).
- Difficiles à tester unitairement et à faire évoluer. Découper par responsabilité (rendu / fetch / charts côté JS ; étapes d'install côté Python).

### 4.4 Typage mypy en trompe-l'œil
- `check_untyped_defs = false` + un large `[[tool.mypy.overrides]]` avec `ignore_errors = true` couvrant `providers_config`, `report`, `serve_dashboard`, `headroom_adapter`, `utils.*`, `hub_files.src.utils.*`.
- **Résultat** : mypy ne vérifie réellement qu'une petite fraction du code. Le « badge type-checked » est largement cosmétique. Réduire progressivement la liste d'exceptions.

### 4.5 Incohérence d'environnements Python
- `.venv-desktop` en 3.12 mais artefacts `__pycache__` en **3.14** (`.venv-build`). Cibler explicitement les versions supportées pour éviter des surprises de compat (ex. `numpy<2`, `transformers<5`).

### 4.6 Reproductibilité des dépendances
- `pyproject` n'utilise que des bornes basses (`>=`). Pas de lockfile Python (seul `package-lock.json` existe côté npm).
- Recommandation : lockfile (`uv.lock`/`pip-tools`) pour des builds reproductibles, surtout pour l'app packagée.

---

## 5. Fiabilité de la mesure de tokens (⚠ point critique — proposition de valeur)

C'est le sujet le plus important car **tout le produit vend une mesure d'économie de tokens**.

### 5.1 Estimation par proxy `len/4`
- Partout, `estimate_tokens(text) = (len(text)+3)//4` (`adaptive_context_manager.py`, `token_budget_guardrail.py`, etc.).
- Ce proxy **ne correspond à aucun tokenizer réel** : il varie fortement selon le modèle (BPE OpenAI vs Anthropic vs code vs langues non-anglaises). Erreur typique de 15–40 %.

### 5.2 Coefficients « counterfactuels » inventés
Dans `telemetry_metrics.py` / `token_budget_guardrail.py`, des économies sont **fabriquées** par des multiplicateurs arbitraires :
- `row_git_cache_tokens_preserved` : `after * 0.12` quand cache hit ;
- guardrail : `prompt_tokens * 0.35 + max(...)`, cycles `4 - streak`, `input * 0.35`… ;
- `diff_only_saved_tokens` : `chars_saved / 4`.
Ces valeurs ne sont pas mesurées ; elles alimentent pourtant les KPI « économies » du dashboard et les claims du README (« up to 98 % », « up to 95 % »).

**Risque** : sur-promesse / chiffres non défendables en audit. Pour un outil de *gouvernance des coûts*, la mesure doit être auditable.

### 5.3 Absence de tests sur ce cœur métier
- Aucun test ne couvre `telemetry_metrics.py`, `serve_dashboard.py`, ni `install_stack.py`. Le code le plus susceptible d'être faux (les maths d'économie) est celui qui n'est **pas** testé (couverture ciblée uniquement sur `hub_files/src/utils`).

### 5.4 Recommandations (mesure honnête)
1. Remplacer `len/4` par un **vrai comptage** : `tiktoken` (OpenAI), endpoint `count_tokens` Anthropic, ou tokenizer HF selon provider — avec cache.
2. Séparer clairement **mesuré vs modélisé** dans le schéma d'événements et sur le dashboard (badge « estimation » vs « mesuré »).
3. Exploiter les `usage` réels renvoyés par les APIs (input/output/**cache_read/cache_write**) plutôt que des proxys — surtout avec le *prompt caching* (lecture cache ~10× moins chère) qui est justement l'objet de l'assemblage en blocs.
4. Ajouter une campagne A/B (avec/sans stack) sur un échantillon pour calibrer/valider les coefficients restants.
5. Couvrir de tests les agrégations de `telemetry_metrics.py` (cas limites : zéro event, valeurs négatives, troncatures).

---

## 6. Sécurité

| Sévérité | Constat | Détail / recommandation |
|---|---|---|
| Moyenne | **CORS `Access-Control-Allow-Origin: *`** sur toutes les réponses API + **POST `/api/dashboard-layout` non authentifié** | Le dashboard sert des données potentiellement sensibles (chemins, requêtes, extraits de code — le README le reconnaît). Sur `127.0.0.1`, une page web malveillante ou un process local peut lire l'API (risque type *DNS rebinding* aggravé par CORS `*`). Ajouter validation de l'en-tête `Host`, retirer le CORS `*` (ou le restreindre), et un token local. |
| Faible | `bandit` skip `B110` (try/except/pass) | Peut masquer des erreurs silencieuses ; à réévaluer au cas par cas. |
| Faible | `pip-audit` en `continue-on-error: true` | Les vulnérabilités de dépendances **n'échouent pas** la CI. Acceptable en phase early, mais à durcir (au moins alerte visible / gate sur criticité haute). |
| Info | Fuite du username auteur dans `install_stack.py` | Voir §4.2. |
| Bon | Secrets, `chmod 600`, gitleaks (CI + pre-commit), pas de `shell=True` | RAS, à maintenir. |

---

## 7. Respect des normes

- **Bon** : PEP 621 (`pyproject`), PEP 8 (ruff E/W/F/I/B/UP/N/C4), typage PEP 484/604, `pre-commit`, licence MIT, README riche et illustré, docstrings présentes sur la plupart des fonctions publiques.
- **Manques** : pas de `CHANGELOG.md`, `CONTRIBUTING.md`, ni `SECURITY.md` ; pas de politique de versioning explicite (le projet est en `1.0.0`) ; règles ruff désactivées discutables (`F841` variables inutilisées, `N806`) qui masquent du code mort ; pas de couverture minimale imposée (`--cov-fail-under`).

---

## 8. Évaluation de l'approche « stack agents / réduction des coûts » (note : 8/10)

### 8.1 Ce qui est remarquable
L'empilement est cohérent et couvre plusieurs surfaces complémentaires :
- **Static Prompt Registry** : bloc système stable trié → maximise les *cache hits* de prompt.
- **Adaptive Context Manager** : assemblage 4 blocs + compaction au-delà de 8 msg / 3000 tokens, KV state.
- **Git pre-flight cache** : réutilisation du BLOCK_2 **sans appel LLM** via signature `branch+SHA+porcelain` — excellent rapport gain/coût.
- **Compression multi-backend** : Claw Compactor (défaut, zéro inférence), LLMLingua (2e passe), SmartCrusher, CCR (dé-duplication par cache sha256).
- **Gouvernance** : task-brief validator (bloque les subagents mal briefés), consumption report, **token-budget guardrail** (ROI gate, two-strike halt), masquage MCP par classe de tâche.
- **RTK** (shell), **Diff-Only** (SEARCH/REPLACE), **code-review-graph** : réduisent la verbosité des sorties d'outils.

### 8.2 Limites de l'approche
- **Mesure = proxy** (cf. §5) : impossible de savoir si la stack gagne réellement des tokens nets, d'autant que l'assemblage ajoute un *overhead* structurel (les blocs `BLOCK_*`, les rapports guardrail injectés) — partiellement suivi (`hook_overhead_tokens`) mais non validé.
- **Guardrail = consigne textuelle** injectée dans le prompt : l'« enforcement » dépend de l'obéissance du modèle, pas d'un blocage réel au niveau outil (sauf le task-brief hook `deny`). Efficacité réelle non mesurée.
- **Résumé KV heuristique naïf** (regex `clé: valeur`) : risque de **perdre des contraintes critiques** → un coût de correction (re-prompts, erreurs) qui peut dépasser l'économie de tokens. La qualité du résumé n'est pas évaluée.
- **Seuils fixes** (8 / 3000 / 1200 chars…) non adaptatifs par modèle/tâche.
- **CCR par sha256 exact** : ne dé-duplique que des blocs identiques ; rien pour les quasi-doublons (contextes de subagents qui se recouvrent).

### 8.3 Évolutions proposées (priorisées)
1. **Comptage réel + comptabilité *cache-aware*** : consommer `usage.cache_read/cache_write` des APIs ; c'est le levier n°1 et il rend enfin les gains **auditables** (P0).
2. **Séparer mesuré vs estimé** dans les KPI et arrêter les claims « up to 98 % » non sourcés (P0, crédibilité).
3. **Éval qualité du résumé KV** : jeu de tests « contrainte préservée / perdue » avant d'agresser les taux de compression (P1).
4. **Seuils adaptatifs / appris** par modèle et par type de tâche (P2).
5. **CCR sémantique** (embeddings / near-dup) au lieu du seul hash exact (P2).
6. **Enforcement dur du guardrail** au niveau tool-layer plutôt que consigne (P2).
7. **Boucle de calibration A/B** continue pour valider les coefficients restants (P1).

---

## 9. Plan d'action priorisé (pour décision)

### P0 — Crédibilité & justesse (semaine)
- [ ] Remplacer `estimate_tokens (len/4)` par un tokenizer réel + cache.
- [ ] Marquer explicitement les KPI « estimés » vs « mesurés » ; retirer/qualifier les claims chiffrés du README.
- [ ] Tests unitaires sur `telemetry_metrics.py` (maths d'économie).
- [ ] Aligner les versions ruff/mypy entre `pyproject`, `pre-commit` et CI.

### P1 — Robustesse (mois)
- [ ] Sécuriser le serveur : validation `Host`, retrait CORS `*`, token local, auth sur POST.
- [ ] Comptabilité *cache-aware* via `usage` des providers + A/B de calibration.
- [ ] Éliminer les chemins/username en dur (templates au lieu de `str.replace`).
- [ ] Durcir `pip-audit` (gate sur criticité haute).

### P2 — Dette & évolution (trimestre)
- [ ] Découper les monolithes (`dashboard.js`, `install_stack.py`, hook 703 l.).
- [ ] Réduire la liste `ignore_errors` de mypy ; viser un vrai typage du cœur.
- [ ] Lockfile Python + version Python unique cible.
- [ ] Ajouter `CHANGELOG`, `CONTRIBUTING`, `SECURITY.md`, `--cov-fail-under`.
- [ ] CCR sémantique, seuils adaptatifs, enforcement guardrail.

---

## 10. Conclusion

Projet **ambitieux, bien outillé et conceptuellement en avance** sur la question de la maîtrise des coûts d'agents IA. L'ingénierie « de forme » (CI, typage, secrets, SSOT) est au-dessus de la moyenne. Le risque principal n'est **pas** la sécurité ni le style, mais la **fiabilité de la mesure** : tant que les économies reposent sur `len/4` et des coefficients inventés, la valeur affichée n'est pas auditable — ce qui est paradoxal pour un outil de gouvernance des coûts. Prioriser le comptage réel et les tests du cœur métier transformerait un très bon prototype en produit défendable.
