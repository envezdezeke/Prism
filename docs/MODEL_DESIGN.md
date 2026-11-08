# Prism Fraud Model and Nemotron Design (decisions of record)

> Settled by Ezekiel in two grilling sessions, Sat 2026-11-07 18:00–19:00 CT. This file is the record; `.planning/PROJECT.md` Key Decisions points here. The math, written out, is in `docs/model/prism_model.tex` (PDF next to it).
> Change rule: after the H10 freeze, any change to a threshold, weight or feature needs both of us, a full-suite re-run and a line in `docs/AUDIT.md` (M19). After H18, no model changes at all.

## 1. Fraud model (M1–M21)

### Unit and structure

| # | Decision |
|---|---|
| M1 | Every signal family reports **bits of surprise**: `bits = −log2 P(observation | clean history)`, with +1 smoothing so nothing is ever zero. F3 and F4 take P from the empirical history frequency of the matched pattern. |
| M2 | **F1 (shared rare entity) is mandatory for a hold.** Bet: the hidden trick is still cross-deal. A ring that shares nothing visible lands on the watch tier at best. |
| M7 | F2–F5 fire above the **95th percentile** of their bits on clean calibration deals (interpolated ranks, +1 smoothing). F1 counts an entity only if fewer than **2%** of history deals use it and it links **≥ 2 deals**. |
| M8 | **Hold = F1 + ≥ 2 of F2–F5.** F6 (terms shape) is evidence for the reason and checklist and **never votes**. Watch = 1–2 families. OLD_TRICK → Fraud Ops (bank policy). |
| M13 | `config/fraud.yaml` stores **percentiles and fractions**, not bit values. Bit thresholds are recomputed at startup from whatever history ships with the dataset (drop, hidden set) and written into the run output for audit. |

### Families

| Family | Signal | Statistic |
|---|---|---|
| F1 shared rare entity | Preparer, phone, registered agent, remit account, producer, address, bank, guarantor shared across deals | Surprisal of the entity value; deal-pair similarity is **Adamic–Adar** `Σ 1/log(deg e)`; entity-type weights (account/preparer/agent strong, address/bank weak); outcome-aware (entities whose history deals mostly repaid count less) |
| F2 novelty / burst | Entity new to history, or used far above its long-run rate | Poisson surprise `−log10 P(X ≥ k | λ)` |
| F3 lookalike | Vendor matching a frequent history vendor's base name, but a different suffix or remit account | Token-set similarity ≥ 0.8 or edit distance ≤ 2; P from history frequency of that pattern |
| F4 document forensics | Producer rare **for that document class** (a statement not made by a statement system), date bursts, save markers | `−log2 P(producer | class)` |
| F5 deposit pattern | Round-number share, weekday concentration, regularity | Percentile vs history; weekday entropy `H = −Σ p log2 p`; **KL divergence** vs the history distribution; **beta-binomial shrinkage** for small samples (replaces a hard n ≥ 6 cutoff) |
| F6 terms shape | Just under an approval threshold from `stages.json`, young entity, no needed-by date, round amount | Evidence only |

Cluster = connected components over **strong F1 edges only**. Each cluster gets a **permutation-test p-value** (shuffle entities across history, about 1,000 times) as evidence. **PMI** between co-occurring rare entities ("the kit") is evidence for linking.

### Linking and timing

| # | Decision |
|---|---|
| M17 | Re-score on **every arrival**; hold the moment the rule is met (even at Intake). `flagged_at` = first arrival that met it. **Holds are sticky** until a human `fraud_release`; weaker later evidence adds a log note and never un-flags. |
| M18 | `history_flags` needs **≥ 2 independent links** with a held cluster: (a) one strong shared entity type, (b) a second strong type, (c) the same F3 pattern, (d) the same rare producer, (e) a matching deposit fingerprint (KL bound). Sample check: H-2511-010 and H-2601-022 share only the producer, so they're out; H-2608-002 and H-2609-008 are in. |
| M14 | Watch tier: `flagged: false`, shown in the UI with evidence. A verification `info_request` goes to the borrower **only when F3 is in the watch evidence** (payment-routing risk). |

## 2. Validation (M3–M6, M9, M15, M16, M20, M21)

| Set | Size | Role | Tune on it? |
|---|---|---|---|
| History Nov 2025 – Jun 2026 | 164 | Baselines + threshold calibration | **Yes (only set)** |
| History Jul – Oct 2026, replayed forward | 93 | Held-out: false flags on good deals; position in the scheme | No |
| 12 old-trick fraud deals | 12 | Blind check without the 5 rules (bonus number) | No |
| 13 sample deals | 13 | Regression + trap suite; `gold.json` scores READ/MOVE | **No** (contaminated) |
| Synthetic (Jesse's trick menu + benign twins) | 100s | Leave one trick family out | Sanity checks only |
| Nemotron-invented tricks | — | **Final exam**, never used for any decision | Never |
| Weekend drop | ? | Blind; first run recorded before anyone opens the files | Never |

Real runs use all 257 history deals as the baseline; the split applies only to measurement.

**Success, in priority order (M6).** A lower item never breaks a higher one:
1. zero false holds on the 13 deals and zero history false flags
2. the sample ring held before Closed, with `history_flags` = H-2608-002 and H-2609-008
3. held-out history: **≤ 1 flag** among ~85 good deals, each reviewed in writing by Jesse
4. synthetic held-out family: **≥ 70%** of ring deals held, **≤ 5%** of benign twins flagged
5. earliness

**Synthetic data (M5, M15, M16).** Built from features (history-schema rows), seeded, never used to learn weights. Jesse's `eval/trick_menu.yaml` (6–8 families, strength ranges, 1–2 benign twins each) is **committed before the first calibration run**. One end-to-end PDF case is kept for the dry run.

**Scorecard (M21).** `prism eval` → `eval/scorecard.{json,md}`: READ/MOVE self-score, trap suite, held-out flags (listed), synthetic per family, the Nemotron final exam, earliness, computed thresholds, commit hash. Every pitch number comes from a committed scorecard.

**Weekend drop (M20).** Tag → run frozen → record the scorecard → Jesse labels `eval/gold_drop.json` → generic fixes only. The headline is the first blind run.

## 3. Playbooks

| If… | Do (in order) | Never |
|---|---|---|
| **Ring missed** (M10) | 1. fix the extraction bug; 2. generic feature fix + full re-run; 3. threshold change only if held-out still passes, logged in AUDIT. **Time box 60 minutes**; at the freeze, ship it on watch and say so honestly | Sample literals, per-deal exceptions, F1 + 1 |
| **False hold on a trap** (M11) | Inspect the families; lower the type weight / add the outcome adjustment / fix the feature; if still failing at the freeze, **tighten to F1 + 3** and re-check the ring | Whitelisting by name |
| **Phase 5 runs late** (M12) | Build order F1 → F3 → F5 → F4 → F2 → PMI/permutation. **Minimum shippable: F1 + F3 + F5** | — |

## 4. Nemotron (N1–N13)

| # | Decision |
|---|---|
| N1 | Nemotron only does what code can't (reasoning over messy text, adversarial creativity, weighing evidence) and **never decides a hold**. Rewording alone isn't value. |
| N2 | **A VL read may fill a scored `extracted` field** only when the parser left it null, it passes a format check and cross-document agreement where available, it's cached, it's tagged `source: "nemotron_vl"`, and it never creates an issue, mismatch or hold. Holds and fraud stay purely deterministic. |
| N3 | **Headline: an adaptive red-team.** Nemotron invents tricks, sees only which were caught (never the thresholds), and evolves new ones over 2–3 generations. Runs **after** the H10 freeze. |
| N4 | **A prosecutor/defender pair** on every held or watched cluster: one agent loop, two system prompts, the same read-only tools. Fraud Ops sees both briefs; the rule decides. |
| N5 | Agent tools are **real HTTP calls** to our FastAPI and the sim-clock API; every call goes in the trace. |
| N6 | Replies: buttons first; a free-text parser only if Vijay confirms free text (J20). |
| N7 | Models: super-vl-120b (agents, red-team, VL); nano-omni reasoning (VL fallback); lightning-30b (parsing, memo wording); bolt unused. Two keys, split by job. |
| N8 | Record/replay cache keyed by hash(model, messages, tools, params); modes `live | replay | off`. The demo and scorecards run on `replay`. |
| N9 | Hidden set: `live` if `NVIDIA_API_KEY` is present, else silently `off`; API failure → `off` for that call. **Never crash.** (Ask Vijay who runs the hidden set.) |
| N10 | **The VL fallback moves into Phase 3** (≤ 30 calls per run), frozen with the engine at H10. |
| N11 | Every agent claim cites an evidence ID or tool result; a deterministic post-check marks uncited claims; the scorecard reports the uncited rate. |
| N12 | Measured value per agent: VL fill accuracy vs gold on ~10 masked documents; red-team catch rate per generation + novelty; prosecutor citation accuracy + defender finding the benign explanation; parser accuracy on ~20 replies. |
| N13 | Cut order: prose polish → reply parser → red-team generations 2–3 → defender → investigator → red-team generation 1 → **VL last** (score value). The memo is template-first. |

## 5. Contract decisions from the audit

- **Q14:** fraud consistency rules (held ⇒ flagged; flagged ⇒ `flagged_at`, `stage_at_flag`) live in the UI models only. The submission validator *warns*; the file is always written.
- **Q15:** `POST /api/clock/advance` to an earlier time returns 422; going back in time is only possible via `/api/clock/replay`.
