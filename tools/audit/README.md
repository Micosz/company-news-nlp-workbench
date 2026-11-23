# Reproducible ECB+ audit metadata

Run with the workbench's Python dependencies installed (including its pinned CoVal and typer 0.9.0):

```sh
python tools/audit/generate.py --repo . --output /tmp/audit-data.json
```

The script imports the existing workbench inference functions without editing them. It verifies upstream dev data against `dataset_checksums.json`, verifies frozen models, restores the train-fitted TF-IDF vocabulary/IDF, runs OR and the frozen OR+TF-IDF policy on complete dev graphs, and derives comparison labels from connected components. It does not fit or tune on dev. Published aggregate FP/FN and added-edge totals are asserted for both annotations; output fails if they disagree.

Outputs:
- `audit-data.json`: 64+ deterministic cross-document audit pairs and all 16 annotation/topic score rows. `orF1` and `hybridF1` are **Pair F1 percentages**, NOT CoNLL F1. `count` is mentions.
- `article-catalog.json`: documents deduplicated across annotation versions, each containing a representative mention and supplied metadata. Metadata are **not original headlines**, and annotation dates are not verified event dates. Sources provide upstream URLs and checksums.
- `cluster-memberships.json`: all dev mention IDs and gold/OR/hybrid cluster labels. Labels must be scoped to annotation + topic; gold is for evaluation, not prediction.

Sampling covers topics and available error/control categories, plus the documented Topic 35 bridge. It is deliberately illustrative, not uniformly random and not representative of error prevalence. Aggregate scores use the entire dev set, not the sample. The input order picks representative document mentions; one document can discuss several events. An article comparison therefore must show the specific mention used, not label an entire article as one event.

No article prose, marked sentence, marked document, or full headline is included in public JSON. Do not publish `.local-data` or `.deps`. The script downloads source text only into a temporary directory for local inference. For reading original news use an explicit local import or authorized source view; annotations' CC BY license is not a blanket license for original article text. Retain upstream/workbench attribution and NOTICE.

Deterministic outputs record source hashes, model hashes, data hashes, source commit, and installed sklearn version. Current test environment differs from the original sklearn version; matching the original aggregate results is checked, not assumed. Prefer the repository-pinned dependency versions for archival reproduction.

Deployed routes: /audit (newsroom, search and comparison) and /audit-analysis (research tables and plots). The newsroom reads pinned article text directly in the browser with checksum verification. Reviewer choices stay local unless the reader explicitly exports a file. No prior slide files are changed.


### Inspecting the published counts and news evidence

In [the analysis view](https://xamrlab-nlp.vercel.app/audit-analysis#pair-inspector), click a topic, a TP/FP/FN count, or a segment legend for newly co-clustered pairs. The view enumerates distinct mention pairs from the saved partitions within the selected topic, including mentions in one document. It checks the counts and Pair F1 against the frozen topic table. The hand-count worksheet is an illustrative subset.

[Random review](https://xamrlab-nlp.vercel.app/audit-review) samples only **different-document, same-topic mention pairs**. The default draws uniformly across eligible pairs from the selected annotation, without replacement within the session, excluding previously stored decisions and revealed cases in this browser. A one-based rank identifies the exact pair in the unmodified frame ordered by numeric topic then ASCII mention ID. The narrower sampling frames disclose whether the hybrid merged, separated, or newly merged a pair. Click-throughs from a known score are diagnostic and do not create a blind review record.

The reviewer reads the marked English sentence, surrounding context and source article, then saves a judgement and reason before labels are displayed. The browser checks the source file hash. Local export records the frame, annotation, sample size, original rank, selection method, two mention IDs, source hash, human decision and system/gold labels. Unknown judgements remain separate. These are completed reviews of explored dev data. A claim about generalization requires an independently labelled, previously unseen news set.

Regenerate the published index by copying the generator's `cluster-memberships.json` to `xamr_lab/static/`. Run `node --test tools/audit/evidence.test.mjs` to check every topic against its saved run and verify the sampling frames.
