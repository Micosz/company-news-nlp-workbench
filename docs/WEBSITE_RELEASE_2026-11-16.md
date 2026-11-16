# Research workbench website · 16 November 2026

The main website is a responsive research workbench for running fixed, original experimental implementations. The editorial grid, warm gray palette, large typography and sparse navigation take visual direction from https://crl-2026.webflow.io/ without copying its branding or content.

## Routes and preservation

- `/`: new workbench; no scores are preloaded. Dataset and method selection, real Run, scoring, changed-pair inspection, browser history and ZIP / CSV / JSON downloads.
- `/paper`: the exact temporal-lab HTML from local `main` commit `2c17372`, with the original cloud adapter inserted when served by FastAPI.
- `/legacy`: existing paper-era Pair Workbench archive, byte-for-byte unchanged.
- `/demo`: existing demo, unchanged.
- Local launcher and complete Pair Workbench UI remain unchanged. Public endpoints do not execute arbitrary Python.

Production remains the existing Vercel Git integration: `main`, Root Directory `xamr_lab`, Python 3.12 / FastAPI `app.py`, Fluid Compute, maxDuration 300. No new paid services.

## Methods and protocol

`research_runner.py` imports the actual `tfidf_only.py`, `or_nb_hybrid.py`, `tfidf_nb.py` and existing X-AMR scorer/graph code. Source experiments: `e454783`, `d180c92`, `745d2fa`. Only these relevant experiments and their helper dependencies were brought from the research branch; the company-news collection task remains stopped and its corpus was not integrated.

| Menu | Actual computation |
|---|---|
| Original OR | Original EID_N + EID_lt edges, connected components, syn_map disabled |
| TF-IDF only | Original word 1–2 gram TF-IDF cosine; cross-document candidates within topic; threshold 0.50 selected by train CV |
| OR + TF-IDF | Original one-round unique mutual-best cluster links; cosine ≥ 0.50, equal nonempty roleset, matching nonempty ARG0 or ARG1; policy `add_0.50` selected by train CV |
| OR + TF-IDF + Naive Bayes | Familiar menu label for the original **OR + NB edge guard using TF-IDF cosine**. Decile bins, CategoricalNB alpha 1, balanced prior, only weak cross-document EID_lt-only edges eligible. It is not TF-IDF additions followed by NB. CV selected fraction **0** for both versions, so this preset preserves OR exactly. |

Each selection includes OR as the control. Compare runs all four on identical mentions. Ann1/Ann2 are semantic annotation input versions of the same ECB+ corpus, not independent gold answer sets. Gold is `(topic, gold_cluster)` for every method. Development has been explored; `test_common` was previously viewed and is only a partial test subset. The UI and API require acknowledgement before a test_common run. No new test_common evaluation was used to select these presets.

## Model artifacts and reproducibility

`models/ann1.json` and `models/ann2.json` contain TF-IDF vocabulary/IDF, NB sufficient statistics, bins, exact original train-CV folds/scores and selections, train checksum, source hashes and training environment. `models/checksums.json` verifies these non-executable artifacts before inference. No pickle loading.

Models were rebuilt with the original training runtime: Python 3.12.15, numpy 2.3.5, scipy 1.18.1 and scikit-learn 1.9.1. **GroupKFold tie handling differs across sklearn versions**: reselecting under 1.6.1 changes topic-fold assignment and can change the selected NB policy. `prepare_models.py` therefore requires original sklearn 1.9.1, with a separate `requirements-training.txt`. The online runner never reselects presets or fits models from evaluation data. Its pinned runtime is numpy 1.26.4, scipy 1.12.0 and sklearn 1.6.1; numerical parity with the original outputs is tested.

Rebuild in a separate Python 3.12 environment with `requirements-training.txt`, prepare the checksum-verified upstream datasets using `setup_data.py`, then run `python prepare_models.py`. The website itself needs only `requirements.txt` and the checked-in JSON artifacts.

## Evidence package

ZIP includes full metric values, MUC/B³/CEAF_e, CoNLL, pair precision/recall/F1, confusion counts, per-topic scores, predictions, all changed links/pairs, capped error examples, LaTeX table, input snapshot, request configuration, model and CV evidence, source snapshot, source/data/model hashes, actual runtime versions and checkout/deployment commit. Scores are percentages in CSV and fractions in report JSON. Timing covers inference and scoring, excluding dataset download and ZIP generation.

Run ID and timestamps are unique; numerical outputs are deterministic. Replay:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r source/requirements.txt
.venv/bin/python source/replay_research.py --input input.json --config config.json --output replay
```

Replay checks the exported input checksum and model checksum. `metrics.csv`, `predictions.csv`, `topics.csv`, `edge_changes.csv` and `pair_changes.csv` must be byte-identical; run IDs, host metadata and timings vary. Executable source is inspectable and only run locally by the researcher.

## Verified dev parity

| Version | Method | CoNLL F1 % | Pair F1 % | FP | FN |
|---|---|---:|---:|---:|---:|
| Ann1 | OR = selected NB guard | 79.7689303090 | 71.8908748824 | 926 | 2062 |
| Ann1 | OR + TF-IDF | 79.0749839597 | 68.0049742405 | 1547 | 2055 |
| Ann2 | OR = selected NB guard | 77.1198177186 | 68.4361824454 | 982 | 2312 |
| Ann2 | OR + TF-IDF | 77.4297756203 | 65.0696864111 | 1862 | 2148 |
| Both | TF-IDF only | 52.7775258503 | 13.5404045967 | 19510 | 4039 |

Cluster partitions also match the original local artifacts. TF-IDF additions: 8 / 16 edges; recovered FN pairs 7 / 164; new FP pairs 621 / 880. These are tradeoffs, not evidence of consistent superiority. Raw-news extraction and statistical significance have not been validated.

## Checks

`test_research.py` verifies original numeric outputs and partition hashes, restored model statistics/ranking, train-fold isolation, repeated runs, dataset/method switches, archive hashes, source-snapshot replay, tamper rejection, API validation, access-key/origin protections, body limits, concurrency, failures and unchanged legacy HTML hashes. Existing X-AMR and Pair Workbench checks also apply.

```sh
python -m pip install -r xamr_lab/requirements-test.txt
(cd xamr_lab && python -m unittest test_engine test_cloud test_tfidf_nb test_or_nb_hybrid test_tfidf_only test_research -v)
node --check xamr_lab/static/research.js
```

Desktop and 390×844 mobile screenshots are saved locally under `artifacts/website-verification/`. Browser verification covered actual Ann1 compare and Ann2 NB runs, loading/disabled controls, stale results after switches, previous-test acknowledgement, persisted history after navigation, and a downloaded browser ZIP inspected for actual report content. Deployment verification uses `/api/workbench/catalog` source/model hashes and a fresh live run, not just a successful build status.

## Operational limits

Fixed allowlist: Ann1/Ann2 dev, dev_small and acknowledged previously-viewed test_common. 2,000 mentions; 4 KB request; 4 MB response. Two concurrent computations per process; this is a local resource bound, not a distributed rate limit. Optional `XAMR_ACCESS_KEY` remains supported. No queue/resume; the client must stay connected. History is browser-local IndexedDB, with a download fallback if storage is unavailable. Public internet access is needed on cold runs to fetch pinned upstream data. Performance in local tests does not guarantee Vercel latency.
