# Changelog

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
