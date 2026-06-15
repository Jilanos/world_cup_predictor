## task_003_phase_2_affiner_le_1x2_retrait_score_ponderation_temporelle_selection_modele_par_backtest - Phase 2 - Affiner le 1X2 (retrait score, ponderation temporelle, selection modele par backtest)
> From version: 1.0.0
> Schema version: 1.0
> Status: Done
> Understanding: 95%
> Confidence: 90%
> Progress: 100%
> Complexity: High
> Theme: Implementation delivery
> Reminder: Update status/understanding/confidence/progress and linked request/backlog references when you edit this doc.

# Definition of Done (DoD)
- [x] AC1 - retrait `most_likely_score` de `output.py` (OUTPUT_COLUMNS), `cli.py`, `web_server.py`, README ; code Poisson absent ; pipeline 1X2 OK.
- [x] AC2 - time-decay parametrable : `config.HALF_LIFE_YEARS` + `model.time_decay_weights` calculent un sample_weight par recence applique a l'entrainement CLI/backtest.
- [x] AC3 - `scripts/model_selection.py` compare logistique calibree vs HistGradientBoosting et balaye Elo (K, avantage terrain) ; meilleure config retenue (`HGB`, `ELO_K=30`, `ELO_HOME_ADVANTAGE=80`, `HALF_LIFE_YEARS=12.0`).
- [x] AC4 - backtest reel : config retenue log-loss 0.8448, Brier 0.4958, accuracy 61.5%, donc >= baseline Phase 1 (0.865 / 60.9%).
- [x] AC5 - pytest vert (26 tests) + `tests/test_model_weights.py` couvre time-decay.
- [x] Validation : pytest vert ; lint + audit OK.

# Implementation plan
1. Retrait colonne/score : `output.py`, `cli.py` (drop import poisson + most_likely_score), `web_server.py`, README ; supprimer `poisson.py` ; ajuster tests si besoin.
2. Time-decay : `config.HALF_LIFE_YEARS` ; helper `time_decay_weights(dates, as_of, half_life)` ; `train_logistic_model(..., sample_weight=)` avec routage robuste (valide empiriquement) ; backtest passe les poids.
3. Selection par backtest : script d'experimentation (logistique vs HGB, balayage Elo) ; retenir la meilleure config ; cabler les defauts.
4. Re-backtest reel + consigner vs baseline Phase 1.
5. Tests + lint/audit + finish.

# Backlog
- `item_003_phase_2_affiner_le_1x2_retrait_score_ponderation_temporelle_selection_modele_par_backtest`

# Acceptance criteria
- AC1: `most_likely_score` est absent des sorties (CSV, Markdown, dashboard) et le code Poisson inutilise est supprime ; le pipeline 1X2 reste fonctionnel.
- AC2: Une ponderation temporelle parametrable des echantillons d'entrainement est implementee et appliquee a l'entrainement.
- AC3: Le choix du modele et des hyperparametres Elo est determine par le backtest (procedure reproductible), et la meilleure configuration est retenue.
- AC4: Le backtest sur donnees reelles montre la configuration retenue au niveau ou au-dessus de la baseline Phase 1 (log-loss <= 0.865 et accuracy >= 60.9% sur un test comparable), chiffres consignes ; toute non-amelioration est documentee honnetement.
- AC5: La suite pytest reste verte (tests impactes par le retrait de la colonne mis a jour) avec, le cas echeant, de nouveaux tests (time-decay).

# AC Traceability
- request-AC1 -> This task. Proof: diff `output.py`/`cli.py`/`web_server.py`/README + suppression `poisson.py` ; pipeline tourne.
- request-AC2 -> This task. Proof: `config.HALF_LIFE_YEARS` + helper de poids + `train_logistic_model(sample_weight=...)`.
- request-AC3 -> This task. Proof: script d'experimentation backtest (logistique vs HGB, balayage Elo) ; meilleure config cablee.
- request-AC4 -> This task. Proof: rapport de backtest reel consigne vs baseline Phase 1.
- request-AC5 -> This task. Proof: suite pytest verte + test time-decay.

# Validation
- Run `python3 -m logics_manager lint --require-status`.
- Run `python3 -m logics_manager flow finish task task_003_phase_2_affiner_le_1x2_retrait_score_ponderation_temporelle_selection_modele_par_backtest.md` after implementation.
- `rtk .venv/bin/python -m pytest -q` -> 26 passed.
- `rtk .venv/bin/python -m worldcup_predictor.backtest_cli --max-test 1000` -> model log-loss 0.8448 / Brier 0.4958 / accuracy 61.5%.
- `rtk .venv/bin/python scripts/model_selection.py --elo-k 30 --elo-home-advantage 80 --max-test 200 --output-csv outputs/model_selection_smoke.csv --output-md outputs/model_selection_smoke.md` -> HGB beats logistic on smoke comparison.
- `rtk logics-manager lint --require-status` -> OK.
- `rtk logics-manager audit` -> OK.
- Finish workflow executed on 2026-06-15.
- Linked backlog/request close verification passed.

# Report
- Livraison Phase 2 complete.
- `most_likely_score` et les references Poisson sont absents des sorties et de la doc runtime ; le projet expose uniquement le resultat 1X2.
- Ponderation temporelle appliquee a l'entrainement via `time_decay_weights`, configurable par `HALF_LIFE_YEARS`.
- Selection reproductible ajoutee dans `scripts/model_selection.py`; smoke conserve dans `outputs/model_selection_smoke.*`.
- Backtest reel full dataset, train 48 417 -> test 1 000 recents : modele 0.8448 / 0.4958 / 61.5% vs base-rate 1.0462 / 0.6303 / 48.6%. Amelioration vs Phase 1 : log-loss 0.865 -> 0.8448, accuracy 60.9% -> 61.5%.
- Finished on 2026-06-15.
- Linked backlog item(s): `item_003_phase_2_affiner_le_1x2_retrait_score_ponderation_temporelle_selection_modele_par_backtest`
- Related request(s): `req_002_phase_2_affiner_1x2`

# AI Context
- Summary: Implement phase 2 - affiner le 1x2 (retrait score, ponderation temporelle, selection modele par backtest).
- Keywords: task, implementation, backlog, runtime, python
- Use when: You need a bounded implementation task for a backlog item.
- Skip when: The work is still at the request or backlog shaping stage.

# Links
- Request: `req_002_phase_2_affiner_1x2`
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)
