---
phase: 261107-qez-engine-skeleton-validator-determinism
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - config/fraud.yaml
  - prism/__main__.py
  - prism/cli.py
  - prism/engine/__init__.py
  - prism/engine/visibility.py
  - prism/engine/money.py
  - prism/engine/config.py
  - prism/engine/state.py
  - prism/engine/writer.py
  - prism/engine/run.py
  - prism/engine/validate.py
  - prism/engine/score.py
  - prism/read/__init__.py
  - prism/read/classify.py
  - prism/read/extract.py
  - prism/read/issues.py
  - prism/move/__init__.py
  - prism/move/stage.py
  - prism/move/routing.py
  - prism/move/sla.py
  - prism/fraud/__init__.py
  - prism/fraud/baseline.py
  - prism/fraud/graph.py
  - prism/fraud/signals.py
  - prism/fraud/decide.py
  - prism/contract.py
  - prism/api/app.py
  - docs/CONTRACT.md
  - tests/conftest.py
  - tests/test_visibility.py
  - tests/test_engine.py
  - tests/test_validate.py
  - tests/test_score.py
  - tests/test_contract.py
autonomous: true
requirements: [FND-01, FND-02, FND-03, FND-04, FND-05, FND-06, FND-08]

estimate:
  tokens: 140000
  raw_tokens: 140000
  tasks: 3
  confidence: low   # no calibration samples exist yet for this project (one prior quick task); factor 1.0

must_haves:
  truths:
    - "A file is invisible to the engine until the sim clock reaches its arrive_at: arrive_at == now is visible, one minute earlier is not, same-time arrivals come back sorted by path, and every time is read as a fixed -06:00 offset whatever the machine's timezone."
    - "python -m prism run --folder F --arrivals A writes out/submission.json for any folder and arrivals pair with no code change: one entry per deal folder (union of folders on disk and in arrivals; 13 on the sample), each with the six submission-format keys (extracted, issues, stage_log, human_requests, alerts, fraud), null facts, empty lists and fraud.flagged false while the read/move/fraud modules are stubs."
    - "Two runs on the same input give byte-identical submission JSON (sorted keys, stable ordering, no wall-clock, no randomness), and an AST test fails if engine code imports random/uuid/secrets or reads the wall clock."
    - "A crash inside one deal's pipeline step is recorded as a _error key on that deal and never stops the file being written; the other deals are unaffected and the file still validates (with a warning)."
    - "python -m prism validate FILE exits non-zero for a bad deal key set, a bad enum, a bad KIND:target issue or a misspelled field, and exits zero with WARNINGS only for the Q14 fraud inconsistencies (held without flagged; flagged without flagged_at or stage_at_flag)."
    - "python -m prism score SUBMISSION --gold eval/gold.json scores only draft/done deals per eval/README.md semantics (trim+casefold exact match with extracted_accept alternates, issue set with issues_optional ignored, first-request routing, furthest stage, fraud flagged/held/latest_ok_stage/linked_deals, history_flags and history_must_not_flag), prints a compact table and writes out/score_latest.json."
    - "Fraud parameters live in config/fraud.yaml as data (0.95 percentile for F2-F5, F1 rarity fraction 0.02, min_linked_deals 2, hold rule F1 plus at least 2 of F2-F5, F6 never votes, history min_links 2, calibration split) and the engine contains no sample folder names, ring ids or threshold literals."
    - "DealDetail and DealSummary reject inconsistent fraud/held/watch data while Submission, SubmissionDeal and Fraud stay lenient; POST /api/clock/advance with a 'to' earlier than now returns 422 and every existing field, endpoint and fixture key is unchanged."
  artifacts:
    - path: "prism/engine/visibility.py"
      provides: "ArrivalLog (from_jsonl, visible_files(now), times, folders, unattached, errors), Arrival, SIM_TZ, parse_time"
    - path: "prism/engine/config.py"
      provides: "ConfigError, Stages, Teams, Assignments, FraudConfig, Rules and the loaders for stages.json, teams.json, assignments.json, config/fraud.yaml"
    - path: "config/fraud.yaml"
      provides: "Settled fraud-model parameters as data (percentiles and fractions, never bit values)"
    - path: "prism/engine/state.py"
      provides: "Doc, EntityRef, DealState, PIPELINE: the shared types and the entry-point table the parallel workstreams build against"
    - path: "prism/engine/run.py"
      provides: "run_sim: steps the sim clock over arrival times, ingest -> fraud -> move per tick, per-deal crash isolation"
    - path: "prism/engine/writer.py"
      provides: "build_submission, dumps (canonical JSON), write_submission"
    - path: "prism/engine/validate.py"
      provides: "validate_submission_file / validate_submission_data returning errors and warnings"
    - path: "prism/engine/score.py"
      provides: "score_submission, format_table, run_score for eval/gold.json"
    - path: "prism/cli.py"
      provides: "python -m prism run | validate | score"
    - path: "prism/read"
      provides: "classify, extract, issues stubs (Phase 3 entry points)"
    - path: "prism/move"
      provides: "stage, routing, sla stubs (Phase 4 entry points)"
    - path: "prism/fraud"
      provides: "baseline, graph, signals, decide stubs (Phase 5 entry points)"
  key_links:
    - from: "prism/engine/run.py"
      to: "prism/read, prism/move, prism/fraud entry points"
      via: "calls through module attributes (not from-imports) so tests can monkeypatch one step to crash"
    - from: "prism/engine/writer.py"
      to: "prism/contract.py Submission models"
      via: "DealState.to_submission_deal() builds SubmissionDeal; the assembled dict is checked by validate.py"
    - from: "prism/engine/validate.py"
      to: "prism/contract.py Submission"
      via: "Submission.model_validate on the payload with underscore diagnostic keys stripped"
    - from: "prism/api/app.py"
      to: "prism/contract.py ClockAdvance"
      via: "advance_clock raises HTTPException 422 when 'to' is before the current now"
---

<objective>
Finish the engine half of Phase 1 in one pass: an arrival-gated, deterministic engine skeleton that always writes a valid submission file, the validator, the determinism harness, the CLI and the self-score script, plus the two small contract fixes from the audit (Q14, Q15).

Scope mapping from the locked decisions: D-01 visibility layer; D-02 config loaders and `config/fraud.yaml`; D-03 `DealState` plus thin typed stubs for `prism/read`, `prism/move`, `prism/fraud` (the contract between the two parallel workstreams that start next); D-04 `engine/run.py` plus CLI `run`; D-05 `validate`; D-06 `score`; D-07 Q14/Q15 contract fixes; D-08 tests that never need `data/`.

Purpose: Phases 3, 4 and 5 can each build against stable entry points while the file you hand the judges is always written, always valid, and always byte-reproducible. Covers FND-01 to FND-06 and the FND-08 script (golden labels were delivered by Jesse; FND-07 is already done).

Output: the files listed in `files_modified`; `.planning/quick/261107-qez-engine-skeleton-validator-determinism-se/261107-qez-SUMMARY.md`.

Time budget (hard stop: pushed by about 20:15 CT): Task 1 about 25 minutes, Task 2 about 20, Task 3 about 15. Commit after each task, staging only the files that task lists (never `git add -A`).
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@prism/contract.py
@docs/CONTRACT.md
@eval/README.md
@docs/MODEL_DESIGN.md

Confidential and gitignored, read for shapes only and never copy content into committed files: `data/participant/` (`sim/arrivals.jsonl` is one JSON object per line with `path` = `<folder>/<file>` and `arrive_at` like `2026-11-02T09:21-06:00`; `sim/assignments.json` maps folder to `{relationship_manager, credit_officer}`; `rules/stages.json` has `pipeline`, `stages`, `fraud_hold`, `stuck_deals`; `contacts/teams.json` has `people[]` with `id, team, backup, escalates_to, notes` plus `routing`; `history/` holds the CSVs). `eval/gold.json` (committed) has `_meta`, `deals{folder: {status, extracted, extracted_accept, issues, issues_optional, routing{4 gates}, final_stage, fraud{flagged, held, latest_ok_stage, linked_deals}}}`, `history_flags`, `history_must_not_flag`.

Baseline at HEAD: `py -3.13 -m pytest -q` gives 78 passed. Interpreter: use `${PY:-py -3.13}` (Windows launcher; the teammate on macOS sets PY=python3). Always set PYTHONUTF8=1. PyYAML 6.0.3 is already installed (verified); only declare it in pyproject, run no install.

Conventions the executor must follow:
- Times: aware datetimes in the fixed -06:00 zone inside the engine; emit with `format_sim_time` from `prism/contract.py` (minute resolution, always `-06:00`). Never read system local time.
- Money is integer cents inside the engine (`prism/engine/money.py`); the submission shows whole dollars as int.
- Rules as data: stage names come from `prism.contract.Stage` (via `typing.get_args`) or from `stages.json`; thresholds come from `config/fraud.yaml`. No folder names, company names, ring ids or numeric thresholds in code.
- Cross-platform: pathlib everywhere, arrivals paths treated as POSIX strings, files written as UTF-8 with LF newlines.
- Only `yaml.safe_load`. JSON/YAML files are read with `encoding="utf-8"`.
- Do NOT rename or remove any existing contract field, endpoint or fixture key (Jesse builds the UI against them). No file under `fixtures/` may change.

<interfaces>
Shared types (prism/engine/state.py) and the six entry points the engine calls. Parallel executors replace stub bodies, never these signatures.

```python
# prism/engine/state.py
PIPELINE: tuple[str, ...]            # typing.get_args(prism.contract.Stage); order = pipeline order

@dataclass
class Doc:
    path: str                        # arrivals path, POSIX, "<folder>/<file>"
    name: str                        # last component, display only, NEVER used to classify
    arrive_at: datetime              # aware, -06:00
    abs_path: Path                   # file on disk (may not exist)
    doc_class: Optional[str] = None  # set by read.classify
    period: Optional[str] = None     # "YYYY-MM" for bank statements
    meta: dict[str, Any] = field(default_factory=dict)   # producer, creator, page markers, ...

@dataclass(frozen=True)
class EntityRef:
    kind: str                        # one of prism.contract.EntityKind
    value: str                       # canonicalized
    source_doc: str                  # Doc.path

@dataclass
class DealState:
    folder: str
    docs: list[Doc]                  # visible docs, arrival order
    facts: dict[str, Fact]           # keys = Extracted field names; Fact = contract.Fact (value, source_doc, confidence)
    entities: list[EntityRef]        # graph attributes, filled by read
    features: dict[str, Any]         # deposit/terms features for F4-F6, filled by read
    issues: list[str]                # open KIND:target strings, sorted
    resolved_issues: list[str]
    stage: str                       # default PIPELINE[0]
    stage_entered_at: Optional[datetime]
    stage_log: list[StageLogEntry]
    human_requests: list[HumanRequest]
    alerts: list[Alert]
    fraud: Fraud
    last_arrival_at: Optional[datetime]
    error: Optional[str]             # first crash in this deal's pipeline; freezes the deal
    def to_submission_deal(self) -> SubmissionDeal: ...

# prism/read/classify.py
DOC_CLASSES: tuple[str, ...]         # READ-01 classes + "other"
def classify(doc: Doc) -> Doc        # fills doc_class, period, meta from CONTENT; never raises

# prism/read/extract.py
FACT_FIELDS: tuple[str, ...]         # tuple(prism.contract.Extracted.model_fields)
def extract_facts(state: DealState, rules: Rules) -> dict[str, Fact]        # full recompute; caller replaces state.facts
def extract_entities(state: DealState, rules: Rules) -> list[EntityRef]     # READ-03; caller replaces state.entities

# prism/read/issues.py
def detect_issues(state: DealState, rules: Rules, now: datetime) -> list[str]   # full open set, sorted; 30-sim-minute quiet rule

# prism/move/stage.py
def step_deal(state: DealState, rules: Rules, now: datetime) -> None            # mutates stage, stage_log, human_requests, alerts; a fraud hold blocks any advance

# prism/move/routing.py
def route_gate(gate_type: str, state: DealState, rules: Rules, now: datetime) -> Optional[str]   # teams.json id or None

# prism/move/sla.py
def sla_pct(state: DealState, rules: Rules, now: datetime) -> float
def sla_alerts(state: DealState, rules: Rules, now: datetime) -> list[Alert]    # newly due at `now`, each exactly once

# prism/fraud/baseline.py
@dataclass
class Baseline: n_history_deals: int = 0
def build_baseline(history_dir: Optional[Path], cfg: FraudConfig) -> Baseline

# prism/fraud/graph.py
@dataclass
class EntityGraph: deal_entities: dict[str, list[EntityRef]]
def build_graph(states: Mapping[str, DealState], baseline: Baseline) -> EntityGraph

# prism/fraud/signals.py
@dataclass(frozen=True)
class FamilySignal: family: str; deals: tuple[str, ...]; bits: float; fired: bool; evidence: str
def compute_signals(graph, states, baseline, cfg: FraudConfig, now: datetime) -> list[FamilySignal]

# prism/fraud/decide.py
@dataclass
class FraudOutcome: per_deal: dict[str, Fraud]; history_flags: list[str]; clusters: list[Cluster]
def decide(signals, graph, states, baseline, cfg: FraudConfig, now: datetime) -> FraudOutcome   # sticky: never un-flag
def evaluate(states, baseline, cfg: FraudConfig, now: datetime) -> FraudOutcome                 # build_graph -> compute_signals -> decide; the ONLY call run.py makes

# prism/engine/config.py
class ConfigError(ValueError)
Rules(stages: Stages, teams: Teams, assignments: Assignments, fraud: FraudConfig, data_root, history_dir, warnings)
def load_stages(path) -> Stages; load_teams(path) -> Teams; load_assignments(path) -> Assignments
def load_fraud_config(path=None) -> FraudConfig; load_rules(data_root, *, fraud_path=None) -> Rules

# prism/engine/run.py
def run_sim(folder: Path, arrivals_path: Path, *, data_root=None, fraud_path=None, end=None) -> RunResult
# per tick: ingest new docs (classify -> extract_facts -> extract_entities -> detect_issues) -> fraud.evaluate -> move.step_deal for every live deal
```
</interfaces>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tracer, arrivals through the gate, DealState and stubs to a written, contract-valid submission</name>
  <files>pyproject.toml, config/fraud.yaml, prism/engine/__init__.py, prism/engine/visibility.py, prism/engine/money.py, prism/engine/config.py, prism/engine/state.py, prism/engine/writer.py, prism/engine/run.py, prism/read/__init__.py, prism/read/classify.py, prism/read/extract.py, prism/read/issues.py, prism/move/__init__.py, prism/move/stage.py, prism/move/routing.py, prism/move/sla.py, prism/fraud/__init__.py, prism/fraud/baseline.py, prism/fraud/graph.py, prism/fraud/signals.py, prism/fraud/decide.py, tests/conftest.py, tests/test_visibility.py, tests/test_engine.py</files>
  <read_first>prism/contract.py (Stage, Extracted, Fact, Fraud, StageLogEntry, HumanRequest, Alert, SubmissionDeal, Submission, EntityKind, Cluster, parse_sim_time, format_sim_time); docs/MODEL_DESIGN.md section 1 (M7, M8, M13, M18); tests/test_contract.py (ROOT constant and the skip-if-no-data pattern); data/participant/sim/arrivals.jsonl first lines, sim/assignments.json, rules/stages.json, contacts/teams.json (shapes only)</read_first>
  <action>
One path through every layer, written for keeps: ArrivalLog -> tick loop -> DealState -> step entry points (stubs) -> writer -> Submission models. Stubs may be thin only because they fill in later without changing a signature (D-03).

1. `pyproject.toml`: add `pyyaml` to `dependencies` (D-02). Nothing else.

2. `prism/engine/visibility.py` (D-01). Export `SIM_TZ` (fixed UTC minus 6 hours, never a named zone, never system local time), `parse_time(s)` (use `datetime.fromisoformat`; a naive value is attached to SIM_TZ; an aware value is converted with astimezone to SIM_TZ; a trailing Z is accepted), a frozen `Arrival` dataclass (`path`, `arrive_at`, plus `folder` = first path component and `name` = last, both derived from the POSIX path), and class `ArrivalLog` built from a list of Arrival with classmethod `from_jsonl(path)`. `from_jsonl` reads UTF-8, one JSON object per line, skips blank lines, and never aborts: a bad JSON line, a missing `path` or `arrive_at`, an unparseable time, an absolute path or any path containing a `..` component is skipped and appended to `.errors` as `line N: reason` (T-qez-01: arrivals paths are untrusted). Backslashes in `path` are normalised to `/`. Methods: `visible_files(now)` returns every Arrival with `arrive_at <= now` (inclusive) sorted by `(arrive_at, path)`, so ties sort by path whatever the file order; a naive `now` is read as SIM_TZ; `times()` returns the sorted unique arrive_at values; `folders()` returns the sorted unique first components of paths that have at least two components; `unattached()` returns sorted single-component paths (a notice dropped at the root is never a deal).

3. `prism/engine/money.py` (FND-02, money half). `to_cents(value)` converts int, float, Decimal or a string such as a dollar sign with thousands separators into integer cents using Decimal with half-up rounding, and raises ValueError for bool, NaN, infinity or anything non-numeric. `cents_to_number(cents)` returns an int when divisible by 100, else a float of cents/100 (the submission shows plain numbers such as 246000).

4. `prism/engine/config.py` (D-02, FND-03). `ConfigError(ValueError)`. Frozen dataclasses, each keeping the parsed JSON in `raw`: `Stages` (`pipeline` tuple, `stages` mapping, `fraud_hold`, `stuck_deals`, accessors `sla_hours(stage)` and `gate(stage)` returning None when absent), `Teams` (`people` mapping keyed by person id, `routing`, accessors `person`, `backup_of`, `escalates_to`), `Assignments` (`by_folder`, accessors `rm(folder)`, `credit_officer(folder)`). `FraudConfig` fields: `percentiles` (dict F2..F5 to float), `f1_rarity_fraction`, `f1_min_linked_deals`, `hold_required` (tuple), `hold_additional_from` (tuple), `hold_min_additional`, `non_voting` (tuple), `history_min_links`, `train_end`, `test_start`, `test_end` (datetime.date). Loaders `load_stages`, `load_teams`, `load_assignments`, `load_fraud_config(path=None)` are strict (FileNotFoundError or ConfigError with a plain message); the default fraud path is `config/fraud.yaml` resolved from the repo root via `Path(__file__).resolve().parents[2]`. `load_fraud_config` uses `yaml.safe_load` only (T-qez-02) and validates: percentiles strictly between 0 and 1; rarity fraction in (0, 1]; min_linked_deals an int >= 2; F6 present and not voting; hold_required and hold_additional_from are subsets of the declared families and hold_additional_from contains no non-voting family; hold_min_additional between 1 and len(hold_additional_from); history_min_links >= 1; the three calibration dates parse from ISO strings with train_end < test_start <= test_end. `load_rules(data_root, *, fraud_path=None)` reads `<data_root>/rules/stages.json`, `<data_root>/contacts/teams.json`, `<data_root>/sim/assignments.json` and sets `history_dir` to `<data_root>/history` when it exists; each missing optional file yields an empty object plus a string in `Rules.warnings` instead of raising; `data_root=None` yields all-empty rules.

5. `config/fraud.yaml` (D-02). Create it with the settled parameters as data and a short header comment saying it stores percentiles and fractions, never bit values (M13). Layout: `version: 1`; a `families` map with F1 (`votes: true`, `rarity_fraction: 0.02`, `min_linked_deals: 2`), F2 to F5 (`votes: true`, `percentile: 0.95` each), F6 (`votes: false`); `hold_rule` with `required: [F1]`, `additional_from: [F2, F3, F4, F5]`, `min_additional: 2`; `history_flags: {min_links: 2}`; `calibration` with `train_end`, `test_start`, `test_end` written as quoted strings 2026-06-30, 2026-07-01, 2026-10-31.

6. `prism/engine/state.py` (D-03). Implement exactly the shared types in the interfaces block. `PIPELINE = typing.get_args(Stage)`; `DealState.stage` defaults to `PIPELINE[0]`. `to_submission_deal()` builds `Extracted` with `None` for any missing fact and the fact value otherwise, `issues` sorted and de-duplicated, `stage_log`, `human_requests` and `alerts` stable-sorted by their parsed time (stable, so ties keep insertion order), and `fraud` with `linked_deals` sorted and de-duplicated. The module docstring carries the entry-point table (which module owns which function, and the per-tick order ingest, then fraud, then move) because it is the hand-off contract for the next two workstreams.

7. Stub packages (D-03): `prism/read/{__init__,classify,extract,issues}.py`, `prism/move/{__init__,stage,routing,sla}.py`, `prism/fraud/{__init__,baseline,graph,signals,decide}.py`. Each function has the exact signature from the interfaces block, a docstring stating the contract (inputs, what the caller does with the return, the invariants such as never raises, sticky holds, content-not-filename), and a body that returns an empty result (classify returns the doc unchanged, extract_facts returns an empty dict, extract_entities and detect_issues return empty lists, step_deal returns None, route_gate returns None, sla_pct returns 0.0, sla_alerts returns an empty list, build_baseline returns `Baseline()`, build_graph returns an empty `EntityGraph`, compute_signals returns an empty list, decide and evaluate return an empty `FraudOutcome`). Each module docstring names its owner phase (Phase 3, 4 or 5). `DOC_CLASSES` lists the READ-01 classes plus `other`; `FACT_FIELDS` is derived from the contract, not retyped.

8. `prism/engine/writer.py` (D-04). `build_submission(states, history_flags, errors, *, team, set_name)` returns a plain dict: every folder in `sorted(states)` mapped to `to_submission_deal().model_dump(mode="json")`; if that call raises, use an empty `SubmissionDeal` dump and set the deal's `_error` to `serialize: <ExcType>: <message>`; if `state.error` is set, `_error` carries it. `history_flags` is sorted and unique. A top-level `_errors` list appears only when non-empty. `dumps(payload)` is `json.dumps` with `sort_keys=True`, `indent=2`, `ensure_ascii=False` plus a trailing newline. `write_submission(payload, out)` creates parent directories and writes UTF-8 with `newline="\n"`.

9. `prism/engine/run.py` (D-04). `RunResult` dataclass (`states`, `history_flags`, `errors`, `unattached`, `n_files`, `n_ticks`). `run_sim` loads rules, loads the ArrivalLog (its `.errors` seed `RunResult.errors`; a missing arrivals file raises FileNotFoundError, it is a usage error), builds the deal set as the sorted union of `ArrivalLog.folders()` and the immediate subdirectory names under `folder` (when it exists), creates one DealState per deal, builds the baseline once from `rules.history_dir`, then steps the clock over `ArrivalLog.times()` (restricted to times <= `end` when given, with `end` appended as a final tick). Per tick: (a) for each deal with newly visible docs, in sorted deal order, create `Doc` objects (`abs_path` = folder joined with the POSIX parts of the arrival path), append them, set `last_arrival_at`, then run the ingest steps classify, extract_facts, extract_entities, detect_issues (replace `facts` and `entities`; move any previously open issue that no longer appears into `resolved_issues`); (b) one fraud pass via `evaluate`, applying `per_deal` Fraud blocks to states and taking the latest `history_flags`; (c) `step_deal` and `sla_alerts` for every deal that has no error. Call every entry point through its module (for example `read_classify.classify(...)` after `from prism.read import classify as read_classify`), never `from x import fn`, so a test can monkeypatch a single step. A `_guard` helper wraps each step: NotImplementedError means the step is not built yet and is skipped silently; any other exception sets `state.error` to `<step>: <ExcType>: <message>` truncated to 300 characters with no traceback and no paths in the file (T-qez-03; the full traceback goes to the `prism` logger, which writes to stderr), and a deal with an error is skipped on every later tick. The fraud pass has its own guard that appends `fraud: <ExcType>: <message>` to `RunResult.errors` and carries on. No wall-clock reads, no randomness, no iteration over sets without sorting (FND-04).

10. Tests. `tests/conftest.py` gets a fixture `tiny_set(tmp_path)` that creates a synthetic shared folder with two deal folders (invented names such as "Alpha Trading" and "Beta & Sons"; never sample names), empty files, and an arrivals.jsonl that includes a same-minute tie and one root-level notice file; it returns `(folder, arrivals_path)`. `tests/test_visibility.py`: inclusive cutoff (arrive_at == now visible, one minute earlier not), ties sorted by path regardless of file order, naive/Z/offset parsing all land on -06:00, a `time.tzset` variant skipped where tzset does not exist, malformed lines collected with line numbers while good lines survive, `..` and absolute paths rejected, backslashes normalised, `folders()` excludes the root-level file which appears in `unattached()`. `tests/test_engine.py` (first half): fraud.yaml values (0.95 for F2 to F5, 0.02, 2, hold rule, F6 non-voting, history 2, the three dates), bad configs raise ConfigError (percentile 1.5, F6 voting, unknown hold family), loaders on minimal JSON written to tmp_path, `load_rules` warns on missing files, a loaders-on-`data/participant` test skipped when absent, money cases (`$1,234.50` gives 123450, half-up, bool and NaN rejected, `cents_to_number`), an interface-surface test that imports every module in the interfaces block and asserts each named callable exists (guards the hand-off against silent renames), and the tracer test: run the tiny set through `run_sim` and `build_submission`, assert one entry per deal folder, null facts, empty lists, `fraud.flagged` false, and that the payload passes `Submission.model_validate`.
  </action>
  <verify>
    <automated>PYTHONUTF8=1 ${PY:-py -3.13} -m pytest -q tests/test_visibility.py tests/test_engine.py</automated>
  </verify>
  <done>The tiny synthetic set runs end to end: arrivals gate visibility, one DealState per deal reaches the writer through every stub, and the output validates against the contract Submission models. config/fraud.yaml loads with the settled values, the interface-surface test pins every stub signature, and the Phase 3/4/5 workstreams can start from state.py and the stubs. Implements D-01, D-02, D-03 and the run/writer half of D-04.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CLI run and validate, determinism harness, crash isolation, validator tests</name>
  <files>prism/__main__.py, prism/cli.py, prism/engine/validate.py, tests/test_engine.py, tests/test_validate.py</files>
  <read_first>prism/engine/run.py, prism/engine/writer.py, prism/contract.py (Submission, SubmissionDeal, Fraud, ISSUE_RE), data/participant/SUBMISSION_FORMAT.md (extra keys are ignored by the organizers; shapes only), fixtures/submission.json, tests/conftest.py</read_first>
  <behavior>
    - fixtures/submission.json validates with zero errors.
    - A deal key not in the supplied folder set gives error `unexpected deal: <key>`; a folder with no key gives `missing deal: <name>`.
    - A stage_log entry with stage "Review" gives an error whose location contains `stage_log`; the issue `MISSING_DOC:passport` gives an error whose location contains `issues`; a misspelled field name (`stagelog`) gives an error.
    - A deal-level `_error` key and a top-level `_errors` key are stripped before model validation, the file stays valid, and each yields a warning containing `engine error`.
    - held true with flagged false gives a WARNING containing `held`, not an error; flagged true without flagged_at or stage_at_flag gives a WARNING containing `flagged_at`; CLI exit code stays 0.
    - Unreadable JSON or a non-object top level gives an error and exit 1; a missing file gives exit 2.
    - Two CLI runs on the same input write byte-identical files; with one deal's step forced to crash the file is still written, the other deal is clean, and the file validates.
  </behavior>
  <action>
Expand the proven slice into the command surface and the safety net (D-04, D-05, D-08).

1. `prism/engine/validate.py` (D-05). `ValidationResult` dataclass with `errors`, `warnings` and an `ok` property (no errors). `validate_submission_data(data, folders=None)`: the top level must be an object. Strip any top-level key and any per-deal key that starts with an underscore before model validation, turning each stripped `_error` or `_errors` into a warning `deal <name>: engine error recorded: <text>` or `run: engine error recorded: <text>`. Validate the rest with `Submission.model_validate`; map each pydantic error to `<dotted loc>: <message>` and sort them so output is stable (this makes the strict contract models reject bad enums, bad `KIND:target` issues, bad times and unknown or misspelled keys). When `folders` is given, add `missing deal: <name>` for each folder with no key and `unexpected deal: <key>` for each key with no folder. Always error on an empty deal key or a key containing a path separator. Then the Q14 consistency rules from the raw payload, as WARNINGS only (they live in the UI models, never in the Submission models): `fraud.held` true without `fraud.flagged` gives `deal <name>: held but not flagged`; `fraud.flagged` true without `flagged_at` or without `stage_at_flag` gives `deal <name>: flagged without flagged_at/stage_at_flag`. `validate_submission_file(path, folders=None)` reads UTF-8 and returns an error instead of raising for unreadable or invalid JSON. Use json only, never eval (T-qez-05).

2. `prism/cli.py` and `prism/__main__.py` (D-04, D-05, FND-05). `main(argv=None) -> int` with argparse subcommands; no subcommand prints help and returns 2; `__main__.py` is `raise SystemExit(main())`. `run`: required `--folder` and `--arrivals`; optional `--out` (default `out/submission.json`), `--set` (dest `set_name`, default `sample`), `--team` (default `Prism`), `--data-root` (default: the parent of `--folder`, which is where `rules/`, `contacts/`, `sim/` and `history/` live), `--fraud-config`, `--end` (parsed with `parse_time`). It calls `run_sim`, `build_submission`, `write_submission`, then self-validates the written payload with `folders=set(result.states)` and prints one summary line (deal count, file count, tick count, error count, output path) plus any validation errors and warnings. Exit 0 when the file was written and valid, 1 when the written file fails validation (the file is still written), 2 when the arrivals file is missing. Per-deal errors alone never change the exit code. `validate`: positional `file`, optional `--folder` (deal keys must equal its immediate subdirectory names) and optional `--arrivals` (keys must equal the folders in that arrivals file); prints `ERROR:` and `WARN:` lines then `valid` or `INVALID (n errors)`; exit 0 valid (warnings allowed), 1 invalid, 2 for a missing or unreadable file. When neither `--folder` nor `--arrivals` is given, state that the key check was skipped.

3. Tests (D-08), none needing `data/` except the marked smoke test. In `tests/test_validate.py` implement every line of the behavior block above, calling `main([...])` for exit codes (use `capsys`), and hand-break a copy of `fixtures/submission.json` in tmp_path for the bad key, bad enum, bad issue and misspelled-field cases. In `tests/test_engine.py` add: `test_run_is_deterministic` (two `main(["run", ...])` calls on the tiny set into two different out paths, assert the bytes are equal, assert keys equal the folder names, assert all emitted times end `-06:00`); `test_crash_isolation` (monkeypatch `prism.read.extract.extract_facts` to raise `RuntimeError("boom")` for one folder; assert the file exists, that deal has `_error` containing `boom`, the other deal has no `_error`, validation is ok with an `engine error` warning); `test_writer_falls_back_on_unserializable_state` (a fact whose value is the wrong type makes `to_submission_deal` raise; the deal becomes empty with `_error` starting `serialize:`); `test_engine_has_no_wall_clock_or_randomness` (parse every `.py` under `prism/engine`, `prism/read`, `prism/move`, `prism/fraud` with `ast` and fail on imports of `random`, `uuid` or `secrets` and on attribute calls that read the clock, such as `now`, `utcnow`, `today`, `time`, `monotonic`, `perf_counter` on datetime/date/time objects); `test_no_sample_literals_in_code` (read the folder names under `data/participant/shared_folder` at runtime and skip when absent, assert none appears in any `.py` under `prism/` or in `config/fraud.yaml`; separately, with no data needed, assert no `.py` under the engine, read, move or fraud packages matches the regex for a history id of the form `H-` plus four digits); `test_cli_smoke_on_participant_data` (skip when `data/participant` is absent; run `main(["run", ...])` into tmp_path and assert exit 0 and that `main(["validate", out, "--folder", ...])` exits 0).
  </action>
  <verify>
    <automated>PYTHONUTF8=1 ${PY:-py -3.13} -m pytest -q tests/test_engine.py tests/test_validate.py && PYTHONUTF8=1 ${PY:-py -3.13} -m prism validate fixtures/submission.json</automated>
  </verify>
  <done>`python -m prism run` writes a valid, byte-reproducible submission for any folder and arrivals pair; a forced crash in one deal leaves a valid file with that deal marked `_error`; `python -m prism validate` exits non-zero on key, enum, grammar and typo violations and only warns on Q14; the AST and sample-literal guards fail the build if wall-clock, randomness or sample names slip into engine code. Implements D-04, D-05, D-08 (FND-04, FND-05, FND-06).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Self-score against eval/gold.json, plus the Q14 and Q15 contract fixes</name>
  <files>prism/engine/score.py, prism/cli.py, prism/contract.py, prism/api/app.py, docs/CONTRACT.md, tests/test_score.py, tests/test_contract.py</files>
  <read_first>eval/README.md, eval/gold.json (top-level keys and one deal), prism/contract.py (DealSummary, DealDetail, Fraud, Stage), prism/api/app.py (advance_clock), tests/test_contract.py (test_advance_clock, the held/watch fixture tests), docs/CONTRACT.md, docs/MODEL_DESIGN.md section 5 (Q14, Q15)</read_first>
  <behavior>
    - A submission identical to a deal's gold scores every check ok for that deal.
    - Strings compare after trim and casefold ("ACME LLC " equals "acme llc"); numbers compare exactly; null equals null only; an `extracted_accept` alternate counts as a match.
    - Issues: gold-only items are `missed`, submission-only items outside `issues_optional` are `false_alarms`; optional items on either side are ignored.
    - Routing uses the first human request of each gate type by time (ignoring requests to the borrower); a gold null gate passes only when the submission has no request of that type.
    - final_stage is the furthest pipeline stage present in stage_log (None for an empty log).
    - Fraud: flagged and held compare as bools; latest_ok_stage passes only when stage_at_flag exists and is at or before it in pipeline order (checked only when gold is flagged); linked_deals compares as a set.
    - Deals whose status is not draft or done are skipped; a gold deal absent from the submission scores as all-miss.
    - history_flags compares as a set (missed, extra) and any flag listed in `history_must_not_flag` is reported as a violation.
    - Q14: DealDetail rejects fraud.held without fraud.flagged, fraud.flagged without flagged_at or stage_at_flag, top-level held without fraud.flagged, and watch with fraud.flagged; DealSummary rejects held together with watch; Submission, SubmissionDeal and Fraud still accept the same inconsistent data.
    - Q15: POST /api/clock/advance with `to` earlier than now returns 422 and the clock is unchanged; `to` equal to now returns 200; `to` after end clamps to end; hours behaviour is unchanged.
  </behavior>
  <action>
Self-score script (D-06) and the audit fixes (D-07).

1. `prism/engine/score.py` (D-06). `score_submission(sub, gold)` returns a dict with these keys so tests and the printer agree: `deals` (folder to `extracted` {field: {ok, got, want}}, `issues` {ok, missed, false_alarms}, `routing` {gate: {ok, got, want}}, `final_stage` {ok, got, want}, `fraud` {flagged, held, latest_ok_stage (omitted when gold is not flagged), linked_deals {ok, missed, extra}}), `history` ({ok, missed, extra, must_not_flagged}), `totals` (per section ok/total counts; issues as tp, fn, fp), `unscored` (folders skipped for status). Semantics follow `eval/README.md` and the behavior block above. Stage order comes from `prism.engine.state.PIPELINE`. `format_table(result)` returns a compact ASCII-only table, one row per scored deal with columns for extracted (n/9), issues (extra and missed counts), routing (n/4), final stage, fraud verdict (ok, FALSE FLAG, MISSED, LATE) and links, then a totals row and a history line; folder names longer than 28 characters are truncated for display only. `run_score(submission_path, gold_path, out_path)` loads both files as UTF-8 JSON, writes `out_path` with `sort_keys=True` and `indent=2` (no timestamps, so the file is reproducible), and returns the result. In `prism/cli.py` add the `score` subcommand: positional `submission`, `--gold` (default `eval/gold.json`), `--out` (default `out/score_latest.json`); print the table; exit 0 on success and 2 when either input is missing or has no scored deal.

2. Q14 (D-07), `prism/contract.py`. Add `model_validator(mode="after")` methods only; add or rename no field. On `DealSummary`: a held deal cannot also be on watch. On `DealDetail`: `fraud.held` requires `fraud.flagged`; `fraud.flagged` requires non-null `flagged_at` and `stage_at_flag`; top-level `held` requires `fraud.flagged`; `watch` forbids `fraud.flagged`. Do not touch `Fraud`, `SubmissionDeal` or `Submission`, and keep `DealDetail.to_submission_deal` unchanged. The five committed fixture deals already satisfy these rules, so `fixtures/` stays untouched.

3. Q15 (D-07), `prism/api/app.py` `advance_clock`: when `body.to` is given and its parsed time is earlier than the fixture clock's `now`, raise `HTTPException(status_code=422, detail=...)` with a message that names `/api/clock/replay` as the way back; a `to` equal to now is a no-op 200; a `to` after `end` still clamps to `end`; leave the hours path and the existing overflow clamp (F-01) alone. Because any earlier `to` is now rejected, the old assertion that `to` of 2020-01-01 returns `start` (from F-02) no longer holds: replace it in `tests/test_contract.py` `test_advance_clock` with a 422 assertion.

4. `docs/CONTRACT.md` (D-07): change the `/api/clock/advance` row to say it clamps to `end` and returns 422 when `to` is earlier than now (use `/api/clock/replay` to go back); add one Conventions bullet each for the 422 rule and for the DealDetail/DealSummary fraud consistency rules, noting the submission file only warns (the validator treats Q14 as warnings and the Submission models stay lenient).

5. Tests (D-08). `tests/test_score.py`: build toy gold dicts and toy submissions in the test (invented deal names, never sample data) covering every line of the behavior block, including the skipped-status deal and the absent-deal all-miss case, and one CLI test through `main(["score", ...])` with tmp_path files asserting exit 0 and that the out file exists. `tests/test_contract.py`: Q14 rejection tests that mutate a copy of the held fixture detail (and a summary), a test that `SubmissionDeal` and `Fraud` accept the same inconsistent data, Q15 tests (earlier is 422 with the clock unchanged, equal is 200, after end clamps), and `test_ui_contract_field_names_unchanged` pinning the exact field-name sets: DealSummary = folder, legal_name, stage, stage_entered_at, sla_hours, sla_pct, needed_by, needed_by_badge, amount_requested, held, watch, rm; DealDetail = DealSummary plus facts, issues, resolved_issues, stage_log, human_requests, alerts, fraud; SubmissionDeal = extracted, issues, stage_log, human_requests, alerts, fraud; Fraud = flagged, held, flagged_at, stage_at_flag, reason, linked_deals; Submission = team, set, deals, history_flags; Clock = now, start, end; ClockAdvance = hours, to.
  </action>
  <verify>
    <automated>PYTHONUTF8=1 ${PY:-py -3.13} -m pytest -q && PYTHONUTF8=1 ${PY:-py -3.13} -m prism score fixtures/submission.json --gold eval/gold.json && test -s out/score_latest.json</automated>
  </verify>
  <done>The scorer follows eval/README.md semantics and prints a compact table plus out/score_latest.json; DealDetail and DealSummary enforce the Q14 rules while the Submission models stay lenient; `/api/clock/advance` returns 422 for a past `to`; docs/CONTRACT.md matches; the full suite is green and the field-name pin test proves nothing was renamed or removed. Implements D-06, D-07, D-08 (FND-08 script).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| organizer data to engine | `arrivals.jsonl` paths, shared-folder files and history CSVs are untrusted input (hidden set and weekend drop arrive unseen) |
| config files to engine | `config/fraud.yaml` and the data pack JSON are parsed into rules the engine trusts afterwards |
| engine to judged output | `out/submission.json` is what judges replay and read; its content must be deterministic and free of local paths or secrets |
| repo to public | everything committed is visible; the data pack is confidential and must stay out |
| UI client to mock API | `/api/clock/advance` mutates the replay position the UI shows |

## STRIDE Threat Register

Threat IDs are unique within this quick task (`T-qez-NN`); `T-qez-SC` is the reserved supply-chain row.

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qez-01 | Tampering | `ArrivalLog.from_jsonl` path handling | medium | mitigate | reject absolute paths and any `..` component, normalise backslashes, record the line in `.errors` instead of building an `abs_path` outside the folder root; covered by a visibility test |
| T-qez-02 | Tampering | `load_fraud_config` YAML parsing | high | mitigate | `yaml.safe_load` only (no object construction), strict schema checks raise ConfigError; covered by bad-config tests |
| T-qez-03 | Information disclosure | `_error` text and logs in the submission | medium | mitigate | store only `<step>: <ExcType>: <message>` truncated to 300 chars, never a traceback or path; full traceback goes to stderr logging only |
| T-qez-04 | Information disclosure | committed tests and code | medium | mitigate | tests build synthetic folders in tmp_path with invented names; runtime guard test asserts no sample folder name or history-id literal appears in engine code or config; `data/` and `out/` stay gitignored |
| T-qez-05 | Denial of service | `validate` and `score` reading arbitrary JSON | low | accept | local operator CLI, `json.load` only, no eval, no network; failure is a non-zero exit |
| T-qez-06 | Repudiation | nondeterministic submission output | medium | mitigate | sorted keys, stable ordering, no wall-clock or randomness (AST test), two-run byte-identity test |
| T-qez-07 | Tampering | `/api/clock/advance` rewinding the replay | low | mitigate | 422 when `to` is earlier than now; going back only through `/api/clock/replay` (Q15) |
| T-qez-SC | Tampering | package installs (npm/pip/cargo) | high | mitigate | the only dependency change is declaring PyYAML in `pyproject.toml`; no install step runs. PyYAML 6.0.3 is verified on pypi.org (PyYAML by Kirill Simonov, pyyaml.org) and already importable in the dev interpreter, so no `[ASSUMED]` or `[SUS]` package and no blocking checkpoint is needed |
</threat_model>

<verification>
Run from the checkout root, in order:
- `PYTHONUTF8=1 ${PY:-py -3.13} -m pytest -q` is fully green (baseline 78 passed; the new tests add to that and none are skipped except the ones marked as needing `data/`).
- `PYTHONUTF8=1 ${PY:-py -3.13} -m prism validate fixtures/submission.json` exits 0.
- `PYTHONUTF8=1 ${PY:-py -3.13} -m prism score fixtures/submission.json --gold eval/gold.json` exits 0 and `out/score_latest.json` exists and is non-empty.
- If `data/participant` is present: `PYTHONUTF8=1 ${PY:-py -3.13} -m prism run --folder data/participant/shared_folder --arrivals data/participant/sim/arrivals.jsonl --out out/submission.json` exits 0, writes one key per folder, and `python -m prism validate out/submission.json --folder data/participant/shared_folder` exits 0.
- Invariant guard (unchanged files, not a deliverable gate): `test -z "$(git status --porcelain fixtures)"`.
</verification>

<success_criteria>
- All eight locked decisions (D-01 to D-08) are implemented and the full test suite passes without needing `data/`.
- `python -m prism run | validate | score` all work from the repo root; the written submission is always present, valid and byte-reproducible.
- `prism/read`, `prism/move` and `prism/fraud` expose the pinned entry points so the Phase 3 and Phase 4/5 workstreams can start in parallel without touching `state.py` signatures.
- No existing contract field, endpoint or fixture key changed; Jesse's UI mock keeps working; docs/CONTRACT.md documents the 422.
</success_criteria>

<source_audit>
| Source | Item | Covered by |
|--------|------|------------|
| GOAL | Rest of Phase 1: arrival-gated deterministic engine skeleton that always writes a valid submission | Tasks 1 and 2 |
| REQ | FND-01 visible_files(now), ties by path | Task 1 (visibility.py), test_visibility.py |
| REQ | FND-02 -06:00 times, integer cents | Task 1 (SIM_TZ, format_sim_time, money.py), Task 2 (times-end-with--06:00 assertion) |
| REQ | FND-03 rules as data, no literals | Task 1 (config.py, fraud.yaml), Task 2 (sample-literal guard) |
| REQ | FND-04 byte-identical runs | Task 2 (determinism test, AST guard) |
| REQ | FND-05 CLI on any folder and arrivals | Task 2 (cli.py run) |
| REQ | FND-06 validator, per-deal crash isolation | Task 1 (run.py guard), Task 2 (validate.py, crash test) |
| REQ | FND-08 self-score script | Task 3 (score.py, CLI score) |
| RESEARCH | no research phase; fraud parameters M7, M8, M13, M18 and audit items Q14, Q15 from docs/MODEL_DESIGN.md | Task 1 (fraud.yaml), Task 3 (Q14, Q15) |
| CONTEXT | D-01 to D-08 | Tasks 1 to 3 as mapped in the objective |
| Excluded | FND-07 (already delivered), READ/MOVE/FRD behaviour (stubs only, later phases), `prism eval` scorecard (Phase 5/M21), Nemotron | not in scope |
</source_audit>

<output>
After completion, create `.planning/quick/261107-qez-engine-skeleton-validator-determinism-se/261107-qez-SUMMARY.md`
</output>
