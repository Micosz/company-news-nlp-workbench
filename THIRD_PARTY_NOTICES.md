# External data and software

## ECB+ pilot data

The prepared pilot derives from the ECB+ corpus maintained by its original authors: https://github.com/cltl/ecbPlus

Reference: Agata Cybulska and Piek Vossen. 2014. *Using a sledgehammer to crack a nut? Lexical diversity and event coreference resolution.* Proceedings of LREC 2014.

The source annotation notice names Agata Cybulska, Piek Vossen and VU University Amsterdam and distributes the annotation under Creative Commons Attribution 3.0 Unported. Original notices are retained unchanged in `data/pilot/licenses/ecbplus/`.

The article text has its original publishers' rights. The annotation notice is not a blanket license for every news article. This research repo preserves provenance and does not assert ownership over those texts.

The preparation selects focal event mentions, joins token contexts, derives pair labels from original event IDs and adds topic-based pilot assignments. Buyer/target annotations have not been supplied. These are our prepared subsets, not an official ECB+ split or a new gold corpus created by the original authors.

## Python dependencies

Dependencies are installed through `requirements.txt`; their own licenses and notices apply. They are not vendored into this repository. See each distribution's metadata/license for numpy, pandas, scipy, scikit-learn, openpyxl and transitive dependencies.

## Project code

No open-source license has been selected for this project's original code. Access for team collaboration does not change the licenses or ownership of the external data above.
