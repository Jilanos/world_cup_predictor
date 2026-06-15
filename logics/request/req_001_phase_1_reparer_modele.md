## req_001_phase_1_reparer_modele - Phase 1 - Reparer le modele (vectorisation, Elo glissant, calibration, battre la base-rate)
> From version: 1.0.0
> Schema version: 1.0
> Status: Done
> Understanding: 90%
> Confidence: 80%
> Complexity: High
> Theme: Model quality
> Reminder: Update status/understanding/confidence and linked backlog/task references when you edit this doc.

# Needs
- Le backtest Phase 0 sur donnees reelles (3600 train -> 400 test) prouve que le modele actuel DETRUIT de la valeur : accuracy 41.3% < base-rate 48.5%, log-loss 1.094 > base-rate 1.055, quasi identique au tirage uniforme.
- Causes identifiees : (a) Elo/FIFA neutralises a l'entrainement (signal fort inutilise), (b) class_weight=balanced sur-predit les nuls, (c) pas de calibration, (d) build_match_features O(n^2) empeche tout backtest a grande echelle (534s pour 4000 matchs).
- Phase 1 doit reparer le coeur du modele pour qu'il batte enfin la base-rate, mesure par backtest.

# Context
- Phase 0 a livre le garde-fou, le fetch des vraies donnees et le backtest reproductible. La baseline chiffree est etablie.
- On NE touche PAS a Dixon-Coles ni a la simulation de tournoi ici (Phases 2-3).
- Le seuil de succes est objectif et mesurable via worldcup-backtest.

# Scope (in / out)
- In :
  - Vectoriser build_match_features (stats de forme/buts en rolling trie, sans groupby par match) -> backtest plein dataset possible.
  - Elo glissant historique recalcule chronologiquement (pre-match, sans fuite), utilise comme feature elo_diff a l'entrainement ET pour les fixtures.
  - Retirer class_weight=balanced et ajouter une calibration des probabilites (robuste aux petits echantillons).
  - Re-backtester et documenter le gain vs base-rate.
- Out :
  - FIFA historique (indisponible) : fifa_rank_diff/fifa_points_diff restent neutres a l'entrainement.
  - Dixon-Coles / Poisson bivarie -> Phase 2.
  - Simulation Monte-Carlo de tournoi -> Phase 3.

# Acceptance criteria
- AC1: build_match_features est vectorise et produit des features equivalentes en O(n log n) ; un backtest sur >= 10000 matchs s'execute en un temps raisonnable (objectif < 60s).
- AC2: Un Elo glissant pre-match est calcule sans fuite et alimente elo_diff a l'entrainement (plus de neutralisation de l'Elo) comme pour les fixtures ; l'Elo manuel reste prioritaire s'il est fourni.
- AC3: class_weight=balanced est retire et les probabilites sont calibrees ; la chaine reste robuste sur petit echantillon (tests existants verts).
- AC4: Le backtest sur donnees reelles montre le modele au niveau ou au-dessus de la base-rate sur log-loss ET accuracy, chiffres consignes.
- AC5: La suite pytest existante reste verte et de nouveaux tests couvrent l'Elo glissant (absence de fuite) et la vectorisation (equivalence des features).

# Definition of Ready (DoR)
- [x] Problem statement is explicit and user impact is clear.
- [x] Scope boundaries (in/out) are explicit.
- [x] Acceptance criteria are testable.
- [x] Dependencies and known risks are listed.

# Dependencies & risks
- Depend de Phase 0 (req_000) : fetch, backtest, garde-fou en place.
- Risque : la calibration (CalibratedClassifierCV) peut echouer sur de tres petits echantillons -> prevoir un fallback non calibre.
- Risque : l'equivalence stricte des features vectorisees vs boucle peut differer sur les bords (fenetres incompletes) -> documenter et tester la tolerance.

# Companion docs
- Product brief(s): (none yet)
- Architecture decision(s): (none yet)

# References
- `src/worldcup_predictor/features.py`
- `src/worldcup_predictor/model.py`
- `src/worldcup_predictor/backtest.py`
- `src/worldcup_predictor/cli.py`

# AI Context
- Summary: Reparer le coeur du modele - vectorisation O(n log n), Elo glissant sans fuite, retrait class_weight + calibration, objectif battre la base-rate.
- Keywords: rolling-elo, vectorization, calibration, class-weight, backtest, log-loss
- Use when: Apres Phase 0, pour rendre le modele reellement predictif.
- Skip when: Le modele bat deja la base-rate de facon stable.

# Backlog
- none
- `item_002_phase_1_reparer_le_modele_vectorisation_elo_glissant_calibration_battre_la_base_rate`
