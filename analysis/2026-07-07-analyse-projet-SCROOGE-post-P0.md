# Analyse critique — S.C.R.O.O.G.E. (Telemetry Token) — Post-traitement P0

- **Date d'analyse** : 2026-07-07 (après-midi)
- **Document précédent** : `analysis/2026-07-07-analyse-projet-SCROOGE.md`
- **Branche** : `main` — modifications **non commitées** en cours (11 fichiers modifiés + 1 nouveau test)
- **Objet** : re-vérification après traitement des actions **P0**, mise à jour de la note, et redéfinition des priorités restantes
- **Statut** : brouillon de décision — à annoter par le mainteneur

> Contexte : suite à la première analyse, les 4 actions **P0** ont été implémentées. Ce document **vérifie** leur réalisation dans le code réel (pas seulement l'intention) et réévalue le projet.

---

## 1. Vérification des P0 (état réel du code)

| # | Action P0 | Statut | Preuve dans le code |
|---|---|---|---|
| 1 | Remplacer `estimate_tokens (len/4)` par un tokenizer réel + cache | ✅ **Fait** | `telemetry_common.py:324` — `estimate_tokens` via **tiktoken `cl100k_base`**, `@lru_cache(1024)`, fallback `len/4`. Réutilisé (avec fallback local) dans `adaptive_context_manager.py:77`, `token_budget_guardrail.py:18`, et le hook `token-telemetry.py`. |
| 2 | Distinguer KPI « estimés » vs « mesurés » + qualifier les claims README | ✅ **Fait** (labels) | `README.md` : « saves up to 98 %/95 % **(estimated)** ». `dashboard.js` : libellés `Tokens (estimated)`, `RTK gain (estimated)`, `Hook gain (estimated)`… (EN + FR). Capture ajoutée de `cache_read_tokens` / `cache_write_tokens` dans `token-telemetry.py`. |
| 3 | Tests unitaires sur `telemetry_metrics.py` | ✅ **Fait** | Nouveau `hub_files/src/utils/test_telemetry_metrics.py` (~230 l.). **11 tests passent en 0.23 s**, couverture 98 % du module. |
| 4 | Aligner les versions ruff/mypy (pyproject / pre-commit / CI) | ✅ **Fait** | `pre-commit` : ruff **v0.15.20**, mypy **v2.1.0**. CI : `pip install ruff==0.15.20 mypy==2.1.0`. Cohérent avec `pyproject` (`ruff>=0.15.20`, `mypy>=2.1.0`). |

**Conclusion : les 4 P0 sont effectivement traités et vérifiés.** La suite de tests passe (`11 passed`).

---

## 2. Note globale mise à jour (scorecard)

| Axe | Avant | Après | Δ | Commentaire |
|---|---|---|---|---|
| Architecture & design | 7.5 | 7.5 | = | Inchangé. |
| Maintenabilité | 6.0 | 6.5 | ↑ | Dérive de versions d'outillage résolue. Monolithes et chemins en dur subsistent. |
| Sécurité | 7.0 | 7.0 | = | Aucun des points sécurité n'était P0 ; CORS `*` / POST non authentifié inchangés. |
| Respect des normes | 7.5 | 8.0 | ↑ | Outillage aligné et épinglé sur les 3 sources. |
| Qualité des tests | 5.0 | 6.0 | ↑ | `telemetry_metrics` couvert (le cœur du chiffrage). `serve_dashboard`/`install_stack` toujours non testés. |
| Fiabilité de la mesure de tokens | 4.0 | 6.5 | ↑↑ | tiktoken + honnêteté des libellés. Reste : encodage figé `cl100k_base`, coefficients counterfactuels toujours modélisés, tokens de cache captés mais non agrégés. |
| Stack agents / réduction coûts (approche) | 8.0 | 8.0 | = | Approche inchangée (les évolutions profondes étaient P1/P2). |

**Note moyenne pondérée : ~6.4 → ~7.0 / 10.** Le gain principal porte, comme visé, sur la **crédibilité de la mesure** — qui était le talon d'Achille identifié.

---

## 3. Qualité des correctifs (revue critique)

### Bon
- **Centralisation** : le tokenizer est défini une fois dans `telemetry_common.estimate_tokens` et importé ailleurs → SSOT respecté, avec fallback local robuste en cas d'`ImportError` (utile pour les hooks exécutés hors venv).
- **Robustesse** : `disallowed_special=()` évite les exceptions sur tokens spéciaux ; double `try/except` (import puis encodage) ; `lru_cache` limite le coût CPU sur textes répétés.
- **Honnêteté** : le suffixe *(estimated/estimé)* est appliqué de façon cohérente EN + FR sur les KPI proxy.
- **Pas de régression** : les tests existants + les 11 nouveaux passent.

### Réserves / dette résiduelle
1. **Encodage figé `cl100k_base`** : c'est le tokenizer GPT-4/3.5. Pour **GPT-4o (`o200k_base`), Claude, Gemini**, cela reste une approximation (meilleure que `len/4`, mais pas *model-aware*). Idéal : sélection d'encodage par provider/modèle.
2. **Coefficients counterfactuels toujours présents** : `telemetry_metrics.py` conserve `after*0.12` (cache Git), `prompt*0.35`, cycles `4-streak`, `chars/4` (diff-only). Le libellé *(estimated)* rend le tout **honnête** mais pas **mesuré**. La correction de fond (comptabilité cache-aware + A/B) reste à faire → **P1**.
3. **`cache_read_tokens` / `cache_write_tokens` captés mais non exploités** : ils sont écrits dans les événements par `token-telemetry.py`, mais **ne sont pas encore agrégés** dans `telemetry_metrics.py` ni affichés au dashboard. Capture ≠ comptabilité. À finaliser.
4. **Lecture intégrale du transcript en mémoire** : `_populate_subagent_stop_row` lit désormais tout le fichier transcript (`read_text`) pour le tokeniser. Sur de gros transcripts, coût CPU/mémoire non borné (tiktoken sur plusieurs Mo). Envisager un plafond de taille ou un échantillonnage.
5. **Travail non commité** : 11 fichiers modifiés + 1 test non suivi. À committer proprement (message dédié P0) pour tracer la décision et déclencher la CI.

---

## 4. Ce qui n'a pas bougé (rappel — non P0)

- **Sécurité serveur** : CORS `Access-Control-Allow-Origin: *` + `POST /api/dashboard-layout` non authentifié, pas de validation d'en-tête `Host` (risque DNS-rebinding sur données locales sensibles). → **P1**.
- **Chemins/username en dur** dans `install_stack.py` + réécriture par `str.replace` en cascade. → **P1**.
- **Monolithes** : `dashboard.js` (~2.9k l.), `install_stack.py` (~1k l.), hook `semantic-compress-pretool.py` (703 l.). → **P2**.
- **mypy laxiste** : `check_untyped_defs=false` + large `ignore_errors=true`. → **P2**.
- **Reproductibilité** : pas de lockfile Python ; incohérence de version Python (3.12 desktop vs 3.14 build). → **P2**.
- **Gouvernance repo** : pas de `CHANGELOG`/`CONTRIBUTING`/`SECURITY.md`, pas de `--cov-fail-under`. → **P2**.
- **`pip-audit` en `continue-on-error`** (les CVE ne bloquent pas la CI). → **P1**.

---

## 5. Priorités restantes (mises à jour)

### P1 — Robustesse & mesure de fond (mois)
- [ ] **Comptabilité cache-aware** : agréger `cache_read_tokens`/`cache_write_tokens` (déjà captés) dans `telemetry_metrics` et le dashboard ; distinguer coût *cache-write* (plein) vs *cache-read* (~10× moins cher).
- [ ] **Calibration A/B** des coefficients counterfactuels restants (ou les remplacer par du mesuré via les `usage` des APIs).
- [ ] **Encodage token *model-aware*** : `o200k_base` pour GPT-4o, mapping par provider ; garder `cl100k_base` en défaut.
- [ ] **Sécuriser le serveur** : validation `Host`, retrait/restriction CORS `*`, token local, auth sur POST.
- [ ] Éliminer chemins/username en dur (templates au lieu de `str.replace`).
- [ ] Durcir `pip-audit` (gate sur criticité haute).
- [ ] Plafonner la lecture de transcript dans le hook de télémétrie.

### P2 — Dette & évolution (trimestre)
- [ ] Découper les monolithes (`dashboard.js`, `install_stack.py`, hook 703 l.).
- [ ] Réduire la liste `ignore_errors` de mypy ; typer réellement le cœur.
- [ ] Tests sur `serve_dashboard.py` et `install_stack.py`.
- [ ] Lockfile Python + version Python unique cible.
- [ ] `CHANGELOG` / `CONTRIBUTING` / `SECURITY.md` + `--cov-fail-under`.
- [ ] CCR sémantique, seuils adaptatifs, enforcement dur du guardrail.

---

## 6. Conclusion

Les **P0 sont traités, vérifiés et testés** : le point le plus critique de la première analyse — la **crédibilité de la mesure de tokens** — est nettement amélioré (tiktoken réel + libellés honnêtes + tests du module d'agrégation). La note globale passe de **~6.4 à ~7.0/10**.

Il reste toutefois un écart entre **capter** l'information de coût (fait) et la **comptabiliser fidèlement** (les coefficients heuristiques et les tokens de cache non agrégés) : c'est désormais l'enjeu **P1** central pour transformer l'honnêteté d'affichage en **mesure auditable**. Les sujets sécurité (CORS/auth) et portabilité (chemins en dur) restent ouverts et devraient suivre.

**Reco immédiate** : committer le lot P0 avec un message dédié pour figer la décision et lancer la CI complète.
