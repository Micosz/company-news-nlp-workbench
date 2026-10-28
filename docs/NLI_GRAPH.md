# NLI + GNN pilot

Install `.venv/bin/python -m pip install -r requirements-graph.txt`.
Restart the server after updating. Select Pilot A or B, load data, open Experiment,
click **NLI + GNN (Pilot)**, then Start experiment. First run downloads the English
model https://huggingface.co/cross-encoder/nli-deberta-v3-small .
The current button replaces the editable algorithm. Restore default code to run the original baseline.

Two matched models: frozen bidirectional NLI + TF-IDF node encoder and pair MLP,
and the same model with one weighted mean graph-message layer. NLI entailment
probability weights edges; three NLI probabilities remain pair features.
No automatic resolution of factual conflicts is claimed. NLI labels are not event identities.

Fixed settings: seed from UI, 80 epochs, Adam .01, 32 hidden units, max 256 TF-IDF
features fit on train only, NLI 256-token truncation, decision threshold .5.
Max 1000 pairs; dev threshold selection is unsupported. No tuning on test.
Train and test graphs are disjoint; test inference jointly sees unlabeled test
contexts. Graph candidate edges come from supplied pairs; texts with identical
context merge to one node. This is not an unrestricted mention-level graph.

Compare pairwise Precision/Recall/F1/Macro F1 on identical splits. Existing verified
Pilot clustering evaluation may also run. Small Pilot, one seed and pretrained
NLI overlap uncertainty do not establish improvement. Run both folds and multiple
seeds before reporting comparative conclusions.

Results include a draggable graph: node = context, green edge = GNN score >= .5,
gray = other candidate pair. Click nodes/edges; wheel zoom. Layout has no semantic
meaning. Graph is prediction visualization, not an explanation of causal reasoning.
`graph.json`, two trained weight files, algorithm snapshot and metrics are saved.
