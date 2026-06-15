## req_000_phase_0_credibiliser_predictor - Phase 0 - Credibiliser le World Cup Predictor (donnees reelles, garde-fou, backtest)
> From version: 1.0.0
> Schema version: 1.0
> Status: Done
> Understanding: 90%
> Confidence: 85%
> Complexity: Medium
> Theme: Reliability
> Reminder: Update status/understanding/confidence and linked backlog/task references when you edit this doc.

# Needs
- Le predicteur tourne sur 12 matchs d'exemple (data/raw/international_results.csv identique a examples/), ce qui rend toute prediction non fiable mais presentee comme credible.
- Aucune mesure de fiabilite n'existe (pas de backtest, pas de log-loss/Brier/accuracy, aucun test).
- Phase 0 doit credibiliser le projet avant toute amelioration de modele : brancher les vraies donnees, empecher silencieusement de predire sur un dataset trop petit, et etablir une baseline chiffree de la precision actuelle.

# Context
- Diagnostic realise : code propre, architecture saine, mais deux defauts cumulatifs (donnees jouet + Elo/FIFA neutralises a l'entrainement).
- Phase 0 est le prerequis des phases 1-4 (Elo glissant, calibration, Dixon-Coles, simulation de tournoi). On ne touche PAS encore au modele ici - on mesure et on securise.
- Dataset cible public : martj42/international_results (~48k matchs depuis 1872).

# Scope (in / out)
- In :
  - Procedure/script documente de chargement et refresh du dataset martj42 dans data/raw/.
  - Garde-fou taille minimale du dataset (seuil configurable) expose au CLI et au dashboard.
  - Module de backtest temporel (split chronologique) : log-loss, Brier, accuracy vs baselines, artefact outputs/backtest_report.*.
  - Tests pytest pour le garde-fou et les metriques de backtest.
- Out :
  - Refonte du modele (Elo glissant, retrait de class_weight, calibration) -> Phase 1.
  - Dixon-Coles, simulation Monte-Carlo de tournoi -> Phases 2-3.

# Acceptance criteria
- AC1: Le dataset martj42 peut etre charge dans data/raw/international_results.csv via une procedure documentee, et le pipeline tourne dessus sans erreur.
- AC2: Sous un seuil configurable de matchs historiques, le CLI et le dashboard emettent un avertissement visible au lieu de predire silencieusement.
- AC3: Un backtest temporel reproductible produit log-loss, Brier, accuracy du modele et des baselines, ecrits dans outputs/backtest_report.*.
- AC4: Des tests pytest valident le garde-fou et le calcul des metriques de backtest.

# Definition of Ready (DoR)
- [x] Problem statement is explicit and user impact is clear.
- [x] Scope boundaries (in/out) are explicit.
- [x] Acceptance criteria are testable.
- [x] Dependencies and known risks are listed.

# Dependencies & risks
- Dependance : acces reseau pour telecharger le dataset martj42 (sinon procedure manuelle documentee).
- Risque : noms d'equipes du dataset complet a enrichir dans team_aliases.py.
- Risque : build_match_features est O(n^2) -> backtest plein dataset lent (borne par --max-test ; vectorisation = Phase 1).

# Companion docs
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)

# References
- `src/worldcup_predictor/cli.py`
- `src/worldcup_predictor/data.py`
- `src/worldcup_predictor/features.py`
- `src/worldcup_predictor/backtest.py`

# AI Context
- Summary: Credibiliser le World Cup Predictor - donnees reelles, garde-fou taille minimale, backtest de reference chiffre.
- Keywords: reliability, dataset martj42, backtest, log-loss, brier, guardrail
- Use when: Avant toute amelioration de precision du modele ; pour etablir la baseline.
- Skip when: La baseline et les vraies donnees sont deja en place.

# Backlog
- none
- `item_001_phase_0_credibiliser_le_world_cup_predictor_donnees_reelles_garde_fou_backtest`
