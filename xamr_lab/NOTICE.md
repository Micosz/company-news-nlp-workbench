# Source and data provenance

Paper: Ahmed et al. (2024), Linear Cross-document Event Coreference Resolution with X-AMR.
https://aclanthology.org/2024.lrec-main.920/
Upstream: https://github.com/ahmeshaf/gpt_coref
Commit: 5639eb84f9cd32c360ff2ee715eb937ed2cc3c8e

vendor/coreference.py and vendor/utils.py are unmodified copies of the author's scripts. Apache-2.0 license copied to vendor/LICENSE. Our engine imports their identifier generation, sparse edge construction and connected-components clustering. No VerbNet in this experiment.

Data are not committed or relicensed here. setup_data.py retrieves the published annotation files directly at the pinned commit and verifies dataset_checksums.json. Consult the original repository, ECB+ and paper for permitted uses of news text/annotations. Downloaded source stays in ignored xamr_lab/data; uploads and export bundles stay local. Export ZIPs can contain copyrighted news text and are for reproducibility, not an assertion of redistribution permission.

The local engine adds temporal interval parsing, greedy constrained cluster merges, validation, reporting and a separate web server. It does not claim to implement CohTP, automatic extraction or a previously established novel state of the art.
