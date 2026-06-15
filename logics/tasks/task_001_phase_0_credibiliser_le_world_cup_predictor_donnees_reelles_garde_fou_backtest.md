## task_001_phase_0_credibiliser_le_world_cup_predictor_donnees_reelles_garde_fou_backtest - Phase 0 - Credibiliser le World Cup Predictor (donnees reelles, garde-fou, backtest)
> From version: 1.0.0
> Schema version: 1.0
> Status: Done
> Understanding: 95%
> Confidence: 90%
> Progress: 100%
> Complexity: Medium
> Theme: Implementation delivery
> Reminder: Update status/understanding/confidence/progress and linked request/backlog references when you edit this doc.

# Definition of Done (DoD)
- [x] AC1 - `data_sources.py` + `scripts/fetch_results.py` telechargent martj42 vers data/raw/ (validation header, ecriture atomique, fallback manuel doc). Verifie : 49 477 matchs telecharges.
- [x] AC2 - `config.MIN_RESULTS_FOR_RELIABLE` (2000) + `reliability.dataset_reliability()` ; banniere d'avertissement dans le CLI (`worldcup-predict`, `worldcup-backtest`) et statut `reliability` expose par le dashboard.
- [x] AC3 - `backtest.py` (split temporel, log-loss/Brier/accuracy vs baselines base-rate et uniforme) + `worldcup-backtest` ; ecrit outputs/backtest_report.md + .csv.
- [x] AC4 - tests pytest dans tests/ (4 garde-fou + 7 backtest) ; 11 passed.
- [x] Validation : pytest vert ; pipeline tourne sur donnees reelles et jouet.

# Backlog
- `item_001_phase_0_credibiliser_le_world_cup_predictor_donnees_reelles_garde_fou_backtest`

# Acceptance criteria
- AC1: Le dataset martj42 peut etre charge dans data/raw/international_results.csv via une procedure documentee, et le pipeline tourne dessus sans erreur.
- AC2: Sous un seuil configurable de matchs historiques, le CLI et le dashboard emettent un avertissement visible au lieu de predire silencieusement.
- AC3: Un backtest temporel reproductible produit log-loss, Brier, accuracy du modele et des baselines, ecrits dans outputs/backtest_report.*.
- AC4: Des tests pytest valident le garde-fou et le calcul des metriques de backtest.

# AC Traceability
- request-AC1 -> This task. Proof: `src/worldcup_predictor/data_sources.py` + `scripts/fetch_results.py` ; verifie 49 477 matchs telecharges et pipeline OK.
- request-AC2 -> This task. Proof: `config.MIN_RESULTS_FOR_RELIABLE` + `reliability.dataset_reliability()` ; banniere CLI affichee, statut `reliability` expose par `web_server.dashboard_status`.
- request-AC3 -> This task. Proof: `src/worldcup_predictor/backtest.py` + `worldcup-backtest` ; ecrit outputs/backtest_report.md et .csv.
- request-AC4 -> This task. Proof: `tests/test_reliability.py` + `tests/test_backtest.py` ; 11 passed.

# Validation
- Run `python3 -m logics_manager lint --require-status`.
- Run `python3 -m logics_manager flow finish task task_001_phase_0_credibiliser_le_world_cup_predictor_donnees_reelles_garde_fou_backtest.md` after implementation.
- Finish workflow executed on 2026-06-15.
- Linked backlog/request close verification passed.

# Report
- Livraison Phase 0 complete. Fichiers ajoutes : src/worldcup_predictor/{data_sources,reliability,backtest,backtest_cli}.py, scripts/fetch_results.py, tests/{test_reliability,test_backtest}.py. Modifies : config.py (seuil + chemins backtest), cli.py (garde-fou), web_server.py + web/{index.html,app.js,styles.css} (banniere fiabilite), pyproject.toml (entry point worldcup-backtest), README.md.
- Verification : `pytest` -> 11 passed. `worldcup-predict` et `worldcup-backtest` affichent la banniere UNRELIABLE sur les 12 matchs jouet. `scripts/fetch_results.py` -> 49 477 matchs telecharges (AC1 OK).
- Bug corrige pendant les tests : `backtest.score` clippait les probas a 1.0 avant normalisation (entrees non normalisees ecrasees) -> normalisation d'abord, puis clip borne basse.
- Hors scope (verrouille pour Phase 1) : feature building O(n^2) rend le backtest plein dataset lent (borne par --max-test) ; Elo/FIFA neutralises a l'entrainement (signal fort inutilise) ; class_weight=balanced sur-predit les nuls ; pas de calibration. Ces points sont la cible des phases suivantes.
- Finished on 2026-06-15.
- Linked backlog item(s): `item_001_phase_0_credibiliser_le_world_cup_predictor_donnees_reelles_garde_fou_backtest`
- Related request(s): `req_000_phase_0_credibiliser_predictor`

# AI Context
- Summary: Implement phase 0 - credibiliser le world cup predictor (donnees reelles, garde-fou, backtest).
- Keywords: task, implementation, backlog, runtime, python
- Use when: You need a bounded implementation task for a backlog item.
- Skip when: The work is still at the request or backlog shaping stage.

# Links
- Request: `req_000_phase_0_credibiliser_predictor`
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)
