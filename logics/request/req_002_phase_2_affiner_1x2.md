## req_002_phase_2_affiner_1x2 - Phase 2 - Affiner le 1X2 (retrait score, ponderation temporelle, selection modele par backtest)
> From version: 1.0.0
> Schema version: 1.0
> Status: Done
> Understanding: 90%
> Confidence: 80%
> Complexity: High
> Theme: Model quality
> Reminder: Update status/understanding/confidence and linked backlog/task references when you edit this doc.

# Needs
- L'utilisateur n'a besoin que du resultat (vainqueur ou nul, 1X2), pas du score exact. La colonne `most_likely_score` et le modele Poisson sont superflus et doivent etre retires.
- Apres Phase 1 (baseline mesuree : log-loss 0.865 / Brier 0.506 / accuracy 60.9% vs base-rate 1.046 / 48.6%), il faut affiner la PRECISION du classifieur 1X2, pas predire des scores.
- Les choix (ponderation temporelle, type de modele, hyperparametres Elo) doivent etre pilotes objectivement par le backtest, pas a l'intuition.

# Context
- Phase 1 a livre l'Elo glissant, la vectorisation, la calibration ; le backtest reproductible est l'arbitre.
- Le jeu de prono se joue sur le resultat -> tout l'effort va sur log-loss et accuracy du 1X2.
- Dataset complet martj42 (~48k matchs) deja en place dans data/raw/.

# Scope (in / out)
- In :
  - Retirer `most_likely_score` de toutes les sorties (CSV, Markdown, dashboard) et supprimer le code Poisson devenu inutile.
  - Ponderation temporelle (time-decay) des matchs d'entrainement, parametrable.
  - Selection pilotee par backtest : modele (logistique calibree vs gradient boosting) et hyperparametres Elo (K, avantage terrain).
  - Re-backtest et consignation du gain vs baseline Phase 1.
- Out :
  - Modelisation de score / Dixon-Coles (le besoin est 1X2 uniquement).
  - Simulation Monte-Carlo de tournoi -> Phase 3.
  - FIFA historique (indisponible).

# Acceptance criteria
- AC1: `most_likely_score` est absent des sorties (CSV, Markdown, dashboard) et le code Poisson inutilise est supprime ; le pipeline 1X2 reste fonctionnel.
- AC2: Une ponderation temporelle parametrable des echantillons d'entrainement est implementee et appliquee a l'entrainement.
- AC3: Le choix du modele et des hyperparametres Elo est determine par le backtest (procedure reproductible), et la meilleure configuration est retenue.
- AC4: Le backtest sur donnees reelles montre la configuration retenue au niveau ou au-dessus de la baseline Phase 1 (log-loss <= 0.865 et accuracy >= 60.9% sur un test comparable), chiffres consignes ; toute non-amelioration est documentee honnetement.
- AC5: La suite pytest reste verte (tests impactes par le retrait de la colonne mis a jour) avec, le cas echeant, de nouveaux tests (time-decay).

# Definition of Ready (DoR)
- [x] Problem statement is explicit and user impact is clear.
- [x] Scope boundaries (in/out) are explicit.
- [x] Acceptance criteria are testable.
- [x] Dependencies and known risks are listed.

# Dependencies & risks
- Depend de Phase 1 (req_001) : Elo glissant, vectorisation, backtest.
- Risque : routage de `sample_weight` a travers Pipeline + CalibratedClassifierCV peut etre delicat selon la version sklearn -> valider empiriquement, choisir une implementation robuste.
- Risque : les ameliorations peuvent ne pas battre la baseline -> AC4 autorise a documenter une non-amelioration plutot qu'a degrader.

# Companion docs
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)

# References
- `src/worldcup_predictor/output.py`
- `src/worldcup_predictor/cli.py`
- `src/worldcup_predictor/model.py`
- `src/worldcup_predictor/backtest.py`

# AI Context
- Summary: Affiner le classifieur 1X2 (retrait du score/Poisson, ponderation temporelle, selection modele/Elo par backtest), objectif >= baseline Phase 1.
- Keywords: 1x2, time-decay, model-selection, gradient-boosting, elo-tuning, backtest
- Use when: Apres Phase 1, pour gagner en precision sur le resultat sans modeliser le score.
- Skip when: Le besoin redevient la prediction de score, ou la precision est jugee suffisante.

# Backlog
- none
- `item_003_phase_2_affiner_le_1x2_retrait_score_ponderation_temporelle_selection_modele_par_backtest`
