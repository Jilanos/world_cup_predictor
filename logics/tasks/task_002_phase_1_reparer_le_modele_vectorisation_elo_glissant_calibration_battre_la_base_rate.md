## task_002_phase_1_reparer_le_modele_vectorisation_elo_glissant_calibration_battre_la_base_rate - Phase 1 - Reparer le modele (vectorisation, Elo glissant, calibration, battre la base-rate)
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
- [x] AC1 - `features.py` vectorise (`_per_match_trailing_stats` via groupby+shift+rolling, un seul passage) ; backtest plein dataset 49 417 matchs en ~3.3s (objectif < 60s largement tenu).
- [x] AC2 - `elo.py` `rolling_elo` : Elo pre-match par match (sans fuite, teste) + final par equipe ; `elo_diff` reel a l'entrainement ; Elo manuel prioritaire pour les fixtures ; FIFA/marche restent neutres.
- [x] AC3 - `model.py` : `class_weight="balanced"` retire + `CalibratedClassifierCV(method=sigmoid)` avec fallback non calibre si echantillon trop petit.
- [x] AC4 - backtest reel : modele log-loss 0.865 / Brier 0.506 / accuracy 60.9% vs base-rate 1.046 / 0.630 / 48.6%. Modele > base-rate sur les trois metriques.
- [x] AC5 - 21 tests verts dont `test_elo.py` (anti-fuite) et `test_features_vectorized.py` (equivalence vs brute-force) + test de non-regression d'alignement.
- [x] Validation : pytest 21 passed ; lint + audit OK.

# Implementation plan
1. `elo.py` : Elo standard chronologique (K, avantage terrain, MOV), pre-match par match + snapshot final. Tests anti-fuite.
2. `features.py` : `rolling_team_table(results)` (shift d'1 match) -> form_5/10, gf/ga pg, clean_sheet, win_rate ; `build_match_features` vectorise + branchement Elo ; `add_backfilled_rating_features` ne touche plus elo_diff.
3. `model.py` : retrait class_weight, calibration robuste.
4. Tests : `tests/test_elo.py`, `tests/test_features_vectorized.py` ; relancer la suite.
5. Backtest reel borne (fenetre >=10k si le temps le permet) -> consigner log-loss/accuracy vs base-rate.

# Backlog
- `item_002_phase_1_reparer_le_modele_vectorisation_elo_glissant_calibration_battre_la_base_rate`

# Acceptance criteria
- AC1: build_match_features est vectorise et produit des features equivalentes en O(n log n) ; un backtest sur >= 10000 matchs s'execute en un temps raisonnable (objectif < 60s).
- AC2: Un Elo glissant pre-match est calcule sans fuite et alimente elo_diff a l'entrainement (plus de neutralisation de l'Elo) comme pour les fixtures ; l'Elo manuel reste prioritaire s'il est fourni.
- AC3: class_weight=balanced est retire et les probabilites sont calibrees ; la chaine reste robuste sur petit echantillon (tests existants verts).
- AC4: Le backtest sur donnees reelles montre le modele au niveau ou au-dessus de la base-rate sur log-loss ET accuracy, chiffres consignes.
- AC5: La suite pytest existante reste verte et de nouveaux tests couvrent l'Elo glissant (absence de fuite) et la vectorisation (equivalence des features).

# AC Traceability
- request-AC1 -> This task. Proof: vectorisation dans `features.py` + mesure de temps backtest >= 10k matchs.
- request-AC2 -> This task. Proof: `elo.py` rolling_elo pre-match + test anti-fuite ; `add_backfilled_rating_features` ne neutralise plus elo_diff.
- request-AC3 -> This task. Proof: `model.py` sans class_weight + calibration ; tests existants verts.
- request-AC4 -> This task. Proof: rapport de backtest reel consigne (log-loss/accuracy vs base-rate).
- request-AC5 -> This task. Proof: `tests/test_elo.py` + `tests/test_features_vectorized.py` ; suite verte.

# Validation
- Run `python3 -m logics_manager lint --require-status`.
- Run `python3 -m logics_manager flow finish task task_002_phase_1_reparer_le_modele_vectorisation_elo_glissant_calibration_battre_la_base_rate.md` after implementation.
- Finish workflow executed on 2026-06-15.
- Linked backlog/request close verification passed.

# Report
- Livraison Phase 1 complete. Ajoutes : `src/worldcup_predictor/elo.py`, `tests/test_elo.py`, `tests/test_features_vectorized.py`. Reecrits : `features.py` (vectorisation + Elo glissant, nouvelles API `build_features_for_results` / `build_fixture_features`), `model.py` (retrait class_weight + calibration), `cli.py` et `backtest.py` (nouvelle API + Elo). README mis a jour.
- Resultat mesure (full dataset, train 48417 -> test 1000 recents) : modele log-loss 0.865 / Brier 0.506 / acc 60.9% ; base-rate 1.046 / 0.630 / 48.6% ; uniforme 1.099 / 0.667 / 48.6%. Le modele bat les baselines sur toutes les metriques.
- Perf : backtest plein dataset ~3.3s (vs 534s en Phase 0 pour seulement 4000 matchs).
- BUG MAJEUR trouve et corrige pendant le backtest : `temporal_split` refaisait un `sort_values("date")` instable sur des donnees deja triees ; avec les nombreux matchs a dates egales, l'ordre des ex aequo divergeait de celui de `build_features_for_results`, desalignant features et resultats (le modele paraissait pire que l'aleatoire : log-loss 1.25). Corrige en `kind="stable"` + test de non-regression. Ce bug corrompait aussi la baseline Phase 0.
- Hors scope (Phases suivantes) : coherence Poisson<->resultat (le score le plus probable peut contredire le pick), Dixon-Coles (Phase 2), simulation de tournoi (Phase 3), FIFA historique indisponible.
- Finished on 2026-06-15.
- Linked backlog item(s): `item_002_phase_1_reparer_le_modele_vectorisation_elo_glissant_calibration_battre_la_base_rate`
- Related request(s): `req_001_phase_1_reparer_modele`

# AI Context
- Summary: Implement phase 1 - reparer le modele (vectorisation, elo glissant, calibration, battre la base-rate).
- Keywords: task, implementation, backlog, runtime, python
- Use when: You need a bounded implementation task for a backlog item.
- Skip when: The work is still at the request or backlog shaping stage.

# Links
- Request: `req_001_phase_1_reparer_modele`
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)
