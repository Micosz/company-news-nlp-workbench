# Benchmark overview design QA

final result: passed

## Target and scope

Selected first displayed design, compared with actual Full Mixed run `20261028T130309Z_d75ad0`, F1, reference toggle off. Existing Python application, no new scaffold or algorithm change. Target normalized from 1488×1058 to 1440×1024; actual IAB viewport 1440×1024, device pixel ratio 1. Mobile: 390×844, device pixel ratio 1.

Evidence: [selected reference](docs/design/selected-reference.png), [desktop](docs/design/overview-desktop.png), [side-by-side](docs/design/comparison.png), [chart and table detail](docs/design/comparison-detail.png), [mobile](docs/design/overview-mobile.png).

## Iterations

1. P2: title/navigation typography too small; plot origin too far right and chart too tall, pushing the main disclosures below the first viewport. Fixed with bundled Noto Sans Thai, a larger title, compact chart rows, a left-aligned plot and tighter section spacing.
2. Desktop repeat comparison: selected hierarchy, white/light-gray surfaces, violet metric control and teal/violet bars match the target. Main chart, table and first three disclosures fit the first viewport. Numeric values verified against saved run data. No remaining P0/P1/P2 desktop issues.
3. P2 mobile: scaling the desktop SVG made labels too small. Added a stacked compact chart at ≤600px that preserves the 0–100% range. Re-captured at 390×844: readable labels, working metric switches and no page-level horizontal overflow. Wide data tables scroll inside their containers.

## Fidelity surfaces

- Typography: bundled Noto Sans Thai regular/medium/semibold/bold; Latin brand uses native sans. No remote font request required at runtime.
- Spacing/layout: top navigation, heading, run/metric controls, full-width chart, compact table, then collapsed details.
- Colors: white and pale-gray surfaces, subtle violet active states, muted violet and teal model bars; saved numeric values never change with styling.
- Image quality: no decorative raster assets in the selected UI. Charts remain rendered from data and exportable as SVG. The generated reference is documentation only.
- Copy/content: short labels; provenance and exploratory status visible. Methods, warnings, missing-value limitations, B³, date strata and logs remain accessible.

Intentional differences: Macro F1 column retained; SVG export and all five existing workflows retained. Additional research disclosures appear below the three shown in the selected mock. No generated sample scores or fabricated gains in the product. P3: standard native disclosure triangles/text actions instead of decorative icons; no functional loss.

## Interaction verification in IAB

- Auto-open latest completed run; change to a different saved run.
- F1, Precision, Recall and Macro F1 update the graph and highlight the matching table column.
- Toggle reference models; open methodology, warnings and 20 error rows.
- Change confusion-matrix model; preserve actual/predicted orientation and counts.
- Download SVG and a complete Pilot ZIP through the UI.
- Load Pilot A, open editable Python section and execute an actual run: `20261028T162000Z_250922`, note `UI smoke test · Benchmark overview · Pilot A`; completed with test 171 pairs and text F1 65.50%. This is a UI smoke test, not new improvement evidence. The local record is retained.
- Open saved result through history; run the existing fictional claim-comparison example.
- Desktop and mobile checks: no observed browser console errors.
- History deletion safety is covered by isolated existing tests; real run history was not deleted during UI QA.

## Automated validation

15 Node chart/fact tests passed, including new wide/mobile chart scale, zero-versus-missing, model grouping and derived-insight checks. 43 Python integrity tests passed. JavaScript/Python syntax checks and `git diff --check` passed. Windows was not directly tested.
