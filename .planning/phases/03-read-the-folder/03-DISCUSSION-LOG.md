# Phase 3 Discussion Log (2026-11-07, ~20:50 CT)

Human reference only. Decisions live in 03-CONTEXT.md.

| Area | Options presented | Selected |
|---|---|---|
| Parser generality | Label-anchored generic / Layout-tuned / Generic + VL safety net | Label-anchored generic (D-01) |
| Holdout | Tune on 10, check on 3 / Tune on all 13 | Tune on 10, check on 3 (D-02) |
| Unsure classification | Best guess + min score / Strict: unsure = other | Best guess, low confidence (D-03) |
| VL + OCR timing | OCR now, VL last / Both now / Defer VL to Phase 6 | OCR now, VL last in phase (D-05, D-06) |
| OCR dependency | Core / Optional extra | Core dependency (D-05) |
| Build order | Tracer then 2 parallel / One sequential / 3 parallel | Tracer, then 2 parallel (D-07) |

Holdout deals chosen by Claude to match the user's criteria ("a messy one and a scanned one"): LSFD_docs, Harbor Tea Co, Summit Peak Flooring.
