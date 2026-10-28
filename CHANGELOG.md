# Changelog

## 2026-10-28 — Manual claim comparison refinements

- Support comma-grouped amounts and an adjustable relative tolerance, defaulting to an illustrative 0.5% of the larger amount; different reporting dates alone do not establish an update.
- Compare chronological acquisition status changes without requiring amounts, including same-day times, and add dividend, reporting certainty and fictional worked examples.
- Require explicit confirmation before comparing a numeric fact and its effective period; different currencies are not converted. This remains a manual rule-based demonstration, not automatic extraction, NLI or fact verification.

## 2026-10-28 — Categorical Naive Bayes and Pilot evaluation

- Replace the default Logistic Regression pair experiment with Categorical Naive Bayes using train-only cosine bins and unknown-aware role categories. Historical runs retain their recorded method.
- Add evidence-backed 42-mention role annotation export/import, Pilot B³ clustering evaluation with complete-pair validation, and a conservative manual claim-comparison prototype.
- Add tests and documentation; real-data role improvement and automatic NLI/extraction remain unverified and unimplemented.

## 2026-10-26 — Visual experiment results

- Add selectable score bar charts and confusion matrices alongside numeric results.
- Read saved run metrics, keep a fixed 0–100% score scale, and distinguish missing results from zero.
- Export standalone SVG charts with the run ID; works with existing run history without rerunning models.
- Test chart values, confusion-matrix orientation, missing data and escaped custom model names in CI.

## 2026-10-26 — Initial workbench and team documentation

- Local Thai web workbench for Excel/CSV pair experiments and editable Python.
- Text baseline, majority/cosine references, and optional buyer/target role ablation.
- Bundled 42-document ECB+ pilot, grouped folds, blank-role Excel template and source notices.
- Saved run evidence, validation, metrics, error analysis and ZIP download.
- Team README, experimental methods, onboarding, contribution guidance and CI configuration.
- Real-data baseline results recorded; real-data role improvement remains pending annotation.
