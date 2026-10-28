# Changelog

## 2026-10-28 — Benchmark overview interface

- Replace the long scrolling sidebar layout with top navigation and focused views.
- Show saved-run selection, metric buttons, a full-width comparison chart and a compact score table first.
- Keep reference models, methodology/provenance/warnings, errors, confusion matrices, B³, date strata and logs accessible through disclosures.
- Open the latest completed local run without retraining. Keep imports, editable code, exports, history deletion and manual claim comparison.
- Bundle open-license Noto Sans Thai for consistent offline typography. Algorithms, datasets and recorded scores are unchanged.

## 2026-10-28 — Exploratory temporal and cross-domain datasets

- Add reproducible ECB+ / Event StoryLine annotation join and separate CDEC-WN positive-only inspection, source hashes, counts, and label limitations.
- Add optional oracle/predicted event-date inputs and time-only / text-plus-time Naive Bayes ablations; date mismatch is never a hard rule for event identity.
- Document source access, the actual preliminary run, test-split limitations, and the uncombined sources.

## 2026-10-28 — Provisional AI-assisted role data

- Add pilot buyer/target metadata from same-source full articles, with source offsets and provenance; the 42 annotations need human review.
- Make the role-enabled snippet Pilot A/B directly selectable, with AI provenance and experimental limitations explained. Do not redistribute newly prepared full articles in this public repository.

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
