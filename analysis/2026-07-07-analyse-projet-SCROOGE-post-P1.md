# Analyse critique — S.C.R.O.O.G.E. (Telemetry Token) — Post-traitement P1

- **Date d'analyse** : 2026-07-07 (fin d'après-midi)
- **Documents précédents** : `2026-07-07-analyse-projet-SCROOGE.md` (initial) · `2026-07-07-analyse-projet-SCROOGE-post-P0.md`
- **Branche** : `main` — commit vérifié **`f10f9d8`** *« feat(telemetry): implement cache-aware token billing, server security, and portability (P1) »*
- **Objet** : re-vérification après traitement des actions **P1**, mise à jour de la note, priorités restantes
- **Statut** : brouillon de décision — à annoter par le mainteneur

> Ce document **vérifie dans le code réel** (commit `f10f9d8`) le traitement des actions P1 listées dans le document post-P0, réévalue le projet, et pointe la dette résiduelle.

---

## 1. Vérification des P1 (état réel du code)

| # | Action P1 | Statut | Preuve dans le code |
|---|---|---|---|
| 1 | Comptabilité **cache-aware** (agréger `cache_read/cache_write`) | ✅ **Fait** | `telemetry_metrics.py` (`summarize_report`) : `adjusted_billed_sum`, `cache_read_sum`, `cache_write_sum`, `latest_adjusted`. Poids **0.1×** sur les tokens lus en cache : `adj_in = (in_tok - c_read) + c_read*0.1`. Consommé côté `dashboard.js` (`cache_read_tokens`, `cache_write_tokens`, `latestCacheRead/Write`). |
| 2 | Encodage token **model-aware** (`o200k_base` pour GPT-4o) | ⚠️ **Fait partiellement** | `telemetry_common.py` : `_get_tiktoken_encoding(model_name)` → `o200k_base` si `gpt-4o`/`o1`, sinon `cl100k_base` ; `estimate_tokens(text, model_name)`. **Mais aucun appelant ne passe `model_name`** → en pratique, défaut `cl100k_base`. Voir §3. |
| 3 | **Sécuriser le serveur** (Host, CORS, token, auth POST) | ✅ **Fait** | `serve_dashboard.py` : `validate_request()` rejette tout `Host` ≠ `127.0.0.1`/`localhost` (400) ; token `secrets.token_hex(16)` exigé sur `/api/*` (403 sinon) ; en-têtes `Access-Control-Allow-Origin: *` **supprimés** ; token injecté dans le HTML servi via `window.__TELEMETRY_TOKEN__` + monkey-patch `fetch` (en-tête `X-Telemetry-Token`). |
| 4 | **Plafonner la lecture du transcript** | ✅ **Fait** | `token-telemetry.py` : `f.read(500000)` (500 k caractères max). |
| 5 | Éliminer **chemins/username en dur** | ✅ **Fait** | `install_stack.py` : **0 occurrence** de `/Users/blegouge` ; hooks `crg-pre-commit.sh` / `log-crg-pre-commit.py` nettoyés (placeholders génériques). |
| 6 | Durcir **`pip-audit`** dans la CI | ✅ **Fait** | `.github/workflows/ci.yml` : `continue-on-error: true` **retiré** → les CVE font désormais échouer le job sécurité. |
| — | Calibration **A/B** des coefficients counterfactuels | ❌ **Non fait** | `telemetry_metrics.py` conserve `after*0.12`, `prompt*0.35`, cycles `4-streak`, `chars/4`. (Était le sous-item « de fond » de P1.) |

**Suite de tests** : `81 passed` (exécution hors sandbox, `.venv-desktop`). *(Note : en environnement sandboxé restreint, 2 tests échouent artificiellement — `git init` bloqué et écriture interdite vers `~/.cursor/projects/ccr_cache/` — ce ne sont pas des régressions ; la CI redirige `CURSOR_HOME` vers le workspace.)*

**Conclusion : 6/7 actions P1 traitées et vérifiées.** Seule la calibration A/B (fond de la mesure) reste ouverte, et l'encodage model-aware n'est branché qu'à moitié.

---

## 2. Note globale mise à jour (scorecard)

| Axe | Initial | Post-P0 | Post-P1 | Commentaire |
|---|---|---|---|---|
| Architecture & design | 7.5 | 7.5 | 7.5 | Inchangé. |
| Maintenabilité | 6.0 | 6.5 | 7.0 | Chemins/username en dur supprimés. Monolithes subsistent. |
| Sécurité | 7.0 | 7.0 | **8.5** | Host validation + token local + CORS `*` retiré + POST authentifié. Reste : logique sécurité non testée. |
| Respect des normes | 7.5 | 8.0 | 8.0 | Stable. |
| Qualité des tests | 5.0 | 6.0 | 6.0 | `telemetry_metrics` couvert, mais la **nouvelle logique sécurité** (`serve_dashboard`) reste non testée. |
| Fiabilité de la mesure de tokens | 4.0 | 6.5 | **7.5** | Cache-aware + infra model-aware. Reste : `model_name` non propagé, poids 0.1× figé, coefficients toujours modélisés. |
| Stack agents / réduction coûts (approche) | 8.0 | 8.0 | 8.0 | Inchangé. |

**Note moyenne pondérée : ~6.4 → ~7.0 → ~7.6 / 10.** Les deux plus fortes progressions cumulées portent bien sur la **sécurité** et la **fiabilité de la mesure** — les deux faiblesses initiales majeures.

---

## 3. Qualité des correctifs P1 (revue critique)

### Bon
- **Sécurité serveur bien conçue** : validation `Host` (anti DNS-rebinding), token aléatoire par session, injection transparente côté client via patch `fetch` → le dashboard reste fonctionnel sans intervention utilisateur, tout en fermant l'accès API aux tiers.
- **Cache-aware fondé sur du réel** : l'ajustement s'appuie sur `cache_read/cache_write` réellement captés (plus sur un pur coefficient inventé) → progrès net vers une mesure auditable.
- **Portabilité** : suppression des chemins personnels, plafond transcript borné (coût CPU/mémoire maîtrisé).
- **CI durcie** : `pip-audit` bloquant.
- **Non-régression** : 81 tests verts.

### Réserves / dette résiduelle
1. **`model_name` non propagé (⚠️ le correctif #2 ne « mord » pas)** : `estimate_tokens(text, model_name)` existe mais **aucun appelant ne transmet le modèle** ; l'encodage reste donc `cl100k_base` en pratique. Pour bénéficier réellement de `o200k_base` (GPT-4o/o1), il faut passer le champ modèle des événements aux appels. En l'état, c'est de l'infrastructure dormante.
2. **Poids cache `0.1×` codé en dur = hypothèse Anthropic** : la lecture cache est ~0.1× chez Anthropic, mais ~0.5× chez OpenAI et différent chez Gemini. Un facteur unique fausse le *billed ajusté* selon le provider → le rendre **provider-aware**.
3. **Coefficients counterfactuels toujours modélisés** : `0.12` (cache Git), `0.35` (guardrail), cycles `4-streak`, `chars/4` (diff-only) restent des estimations non calibrées. Honnêtes (label *estimated*) mais non mesurées → **A/B à faire**.
4. **Nouvelle logique sécurité non testée** : `validate_request` (Host/token), l'injection `fetch` et les réponses 400/403 n'ont **aucun test**. Régression future facile à introduire sur un chemin critique.
5. **Fallback token en query string** (`?token=`) : la voie principale est l'en-tête (bien), mais le fallback `?token=` peut fuiter via historique/referrer. Acceptable en local, à documenter/retirer si possible.

---

## 4. Ce qui reste ouvert (P2 — inchangé)

- **Monolithes** : `dashboard.js` (~2.9k l.), `install_stack.py` (~1k l.), hook `semantic-compress-pretool.py` (703 l.).
- **mypy laxiste** : `check_untyped_defs=false` + large `ignore_errors=true`.
- **Tests manquants** : `serve_dashboard.py` (dont la sécurité) et `install_stack.py`.
- **Reproductibilité** : pas de lockfile Python ; version Python 3.12 vs 3.14 (build).
- **Gouvernance repo** : pas de `CHANGELOG`/`CONTRIBUTING`/`SECURITY.md`, pas de `--cov-fail-under`.

---

## 5. Priorités restantes (mises à jour)

### P1-bis — Finir la fidélité de mesure (semaines)
- [ ] **Propager `model_name`** depuis les événements jusqu'à `estimate_tokens` (sinon `o200k_base` reste inactif).
- [ ] **Poids cache provider-aware** (0.1× Anthropic / ~0.5× OpenAI / Gemini) au lieu du `0.1×` figé.
- [ ] **Tests** sur `validate_request` (Host/token, 400/403) et sur l'agrégation cache-aware (`adjusted_billed_sum`).
- [ ] **A/B / calibration** des coefficients counterfactuels restants (ou bascule vers du mesuré via `usage`).

### P2 — Dette & évolution (trimestre)
- [ ] Découper les monolithes (`dashboard.js`, `install_stack.py`, hook 703 l.).
- [ ] Réduire `ignore_errors` de mypy ; typer réellement le cœur.
- [ ] Tests `serve_dashboard.py` / `install_stack.py`.
- [ ] Lockfile Python + version Python unique cible.
- [ ] `CHANGELOG` / `CONTRIBUTING` / `SECURITY.md` + `--cov-fail-under`.
- [ ] CCR sémantique, seuils adaptatifs, enforcement dur du guardrail.

---

## 6. Conclusion

Les actions **P1 sont traitées à 6/7 et vérifiées dans le code** (commit `f10f9d8`, 81 tests verts). Les deux faiblesses historiques — **sécurité du serveur** et **fidélité de la mesure de tokens** — progressent nettement (7.0 → 8.5 et 6.5 → 7.5). La note globale passe de **~7.0 à ~7.6/10**.

Deux nuances critiques subsistent avant de considérer la mesure comme pleinement auditable :
- l'**encodage model-aware est dormant** tant que `model_name` n'est pas propagé (le correctif #2 n'a pas encore d'effet réel) ;
- le **poids cache `0.1×`** et les **coefficients counterfactuels** restent des hypothèses non calibrées et provider-génériques.

Enfin, la **nouvelle logique de sécurité mérite ses propres tests** : c'est désormais un chemin critique non couvert. Ces points constituent le **P1-bis** recommandé avant d'attaquer la dette P2 (monolithes, mypy, gouvernance).
