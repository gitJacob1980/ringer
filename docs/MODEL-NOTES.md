# Model notes — how workers actually perform

A running log of how models perform on real Ringer tasks, so engine and
model choices are made on evidence instead of vibes. The raw numbers now
live in the local eval log (`~/.ringer/runs.jsonl`); run `./ringer.py models`
to print the per-model, per-task_type scoreboard (tasks, attempts,
pass_rate, first_try_pass_rate, median duration/tokens, last_seen). This
file remains the judgment layer on top of those numbers.

**How to add a row:** after reviewing a run (post-run ritual step 5 in the
ringer skill), append one dated line under the model. Say the task type,
what happened, and what you'd do differently. Only write what the executed
checks and raw logs support — no vibes, no worker self-reports.

## codex (GPT-5-class, own harness)

- Strongest general worker; the default engine. Spend reasoning effort per
  task via `engine_args` (`["-c", "model_reasoning_effort=low|medium|high"]`)
  — high on gnarly tasks, low on boilerplate.
- 2026-08-08 — code-feature (docfoundry review rounds 3–7, 6 runs incl.
  two polish rounds): 6/6 first-try, 65k–226k tokens/task. Its sandbox
  DENIES binding 127.0.0.1 even port 0 — socket-bound pytest suites fail
  inside the worker with PermissionError; codex handled it well both
  times (reported honestly in notes.md, self-verified via in-process
  HTTP shim / no-socket harness) and the executed check outside the
  sandbox stayed the truth. Spec the full-suite command anyway; don't
  read a worker's in-sandbox "N failed (socket bind)" as a red flag.
- 2026-08-08 — code-feature (docfoundry ocr): pass on attempt 2, ~107k
  tokens. Second confirmed case of codex resolving an ownership-grep
  failure DESTRUCTIVELY: the check flagged the orchestrator's own
  uncommitted manifest as an unexpected untracked file, and on retry codex
  deleted it (prior case 2026-08-08 outline-garble: reverted uncommitted
  contract+tests). The model treats the check's failure output as the spec.
  Orchestrator rule: commit contract, tests, AND the manifest before
  dispatching any diff/untracked-grep-checked task.
- 2026-07-05 — carried the heavy lanes of the milk-crate demo rehearsals
  (market read with source allowlist, site build) with clean first-attempt
  passes.
- 2026-07-10 — gpt-5.6-sol, code-feature (steering-profiles feature in
  ringer.py itself, ~470-line change + 18 tests + docs, run
  ringer-steering-profiles): shipped as PR #25. 2 attempts, 379k tokens,
  but the attempt-1 FAIL was the CHECK's fault, not the model's — the check
  gated on the ENTIRE pre-existing suite being green inside the worker
  sandbox (localhost binds blocked, fixture missing). The feature work
  itself was verified green both attempts; attempt 2 "hardened" an already
  -sound implementation. Scoreboard's FAIL row for this run understates the
  model. Lesson for check authors: regression gates must compare against
  the BASELINE failure set, never assert absolute suite green.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~85k tokens.
- 2026-07-06 — motion design (5 HTML animations for video b-roll) + 2
  editorial diagram pages, each verified by rendering through headless
  Chromium to MP4/PNG: 7/7 passed on attempt 1. Broadcast-quality visual
  output from rich storyboard specs; the render-as-check pattern works.
- 2026-07-06 — milk-crate demo: two single-file website builds (v1 scaffold
  316s/~175k tok; final brand+market-test reskin 622s/~184k tok), both passed
  14-assertion content checks on attempt 1, including base64-embedding photos
  and honoring honesty-marker requirements. Codex remains the site-build lane.
- 2026-07-06 — ringer.py feature batch (task_type field + enriched eval rows
  + `models` scoreboard + hud single-tab fix; ~640-line diff incl. two new
  test suites): substance passed on attempt 1 — its check printed PASS
  (compile, all 16 suites, exact CLI aggregation contract) — but the run
  recorded attempt 2 because of the expect_files-before-check harness bug
  (see process lessons). Heavy single-file feature work against an exact
  behavioral contract is squarely codex's lane.

- 2026-07-06 — elsas-website demo: Next.js scaffold PASSED attempt 2 (682s,
  ~354k tok) — attempt 1 built a complete homepage and silently skipped the
  other 10 routes; the route-enumeration check caught it. Narration lane
  (15 ElevenLabs calls, chunked, nohup pattern) passed attempt 1. CAUTION: a
  codex fix worker GAMED a verbatim-content needle by hiding the required text
  in a visually-hidden paragraph — passed the check, caught only by
  orchestrator integration review. Needle checks need an anti-hidden-text
  assertion or documented exceptions.

- 2026-07-06 — OpenRouter catalog + explore suggester (catalog subcommand
  with snapshot/changelog/free-detection, daemon auto-refresh, tiered
  --explore; offline fixture-driven contract check): PASS attempt 1, 362s.
  Follow-up sentinel-pricing fix (variable-pricing models): PASS attempt 1,
  114s. With the verify-order fix landed, zero phantom retries across the
  whole batch.
- 2026-07-06 — adversarial review of the model-router stack (2,650-line
  diff, structured report contract): PASS attempt 1, 176s — found a real
  HIGH (--since window inflating first-try rates) plus 3 MEDIUMs, all
  confirmed against the code. Then fixed all five review findings in one
  batch (task-level --since, pricing transitions, event durability + flock,
  unknown pricing, stderr notice) with test coverage: PASS attempt 1, 202s.
  Review->fix roundtrip in codex's lane works end to end.
- 2026-07-06 — scoreboard HTML page (zero-LLM renderer, ~700-line diff,
  design + evidence-floor ranking + cost math + notes parser): substance
  PASS attempt 1 (the run's recorded retry was an orchestrator check bug —
  the free-promo watchlist legitimately mentions a free model before the
  ranked cards, and the check compared raw first-occurrence). Six review
  findings fixed in one batch, PASS attempt 1, 141s.
- 2026-07-06 — model-db stack (SQLite read model 516s, page redesign 536s,
  Ringside tab 527s, plus three fix batches all attempt-1): five substantial
  ringer.py features in one day, every one against an executed contract
  check. Review lane found the HIGH that mattered (sync cursor skipping a
  half-written trailing line). Codex is the proven lane for both sides of
  the review->fix loop on this codebase.

- 2026-08-08 — code-fix (docfoundry REJECT_STITCHED verdict in cite.py, run
  docfoundry-contiguous-quote): 1st-try pass, 38.9k tokens, 97s. Small
  well-specified single-file change against 8 pre-written red tests —
  codex baseline holds.

- 2026-08-08 — code-fix (docfoundry outline×garble xref, run
  docfoundry-outline-garble-xref): 2 attempts, 98k tokens. Attempt-1 fail
  was the ORCHESTRATOR'S fault: the ownership check grepped `git diff`
  but the orchestrator's own contract+test edits were uncommitted, so
  they read as violations. On retry codex "fixed" it by REVERTING the
  orchestrator's files — it satisfied the literal check over the spec's
  hard rule (never touch tests/CONTRACTS). Lesson: commit contract+tests
  BEFORE dispatching, or exclude them in the ownership grep; and expect
  codex to treat the check's failure output as the true spec on retry.

## glm-5.2 via opencode (`openrouter/z-ai/glm-5.2`)

- The cheap-intelligence default (~$0.74/M in, $2.33/M out, 2026-07 —
  20-30x cheaper output than frontier coding models). Reliable on
  mechanical, tightly-specced work: file edits, format conversions,
  template-driven builds.
- 2026-07-05 — milk-crate demo rehearsals: handled brand-board/SVG/copy
  tasks at around a penny per passing task.
- 2026-07-06 — adversarial pre-merge review (aicred spark): passed, but
  needed the retry (attempt 2) where codex passed on attempt 1. Long
  structured reviews sit at the edge of its comfort zone; keep the section
  contract explicit in the spec.
- 2026-07-06 — three mechanical image-generation batches (18 images via
  openrouter-image commands, idempotent batch-runner spec): 3/3 passed on
  attempt 1, ~14.5k tokens each. The "execute these exact commands, do not
  improve them" spec pattern is fully reliable for glm-5.2.

- 2026-07-06 — backfill/seed script for the model log (252-line stdlib CLI
  with a run-state join, 3-level mapping precedence, never-overwrite and
  idempotency rules): the artifact was CORRECT; the recorded FAIL was an
  orchestrator check-fixture bug (a missing newline glued the fixture's last
  row to a garbage line) plus the harness ordering bug below. Verified PASS
  once the check was fixed. Tight behavior contracts in the spec work great
  for glm — and read the raw logs before blaming the model.
- 2026-07-06 — README/MODEL-NOTES docs + task_type sweep across 17 template
  manifests: passed attempt 2; attempt 1 was lost to the harness ordering
  bug, not model quality — the retry worker's log correctly diagnosed that
  harness bug unprompted, impressive debugging from the cheap lane.
- 2026-07-06 — catalog/explore README section (flags, promotion ladder,
  per-user framing): PASS attempt 1, ~21.5k tokens. Doc sections against a
  grep-able content contract remain a safe glm lane.
- 2026-07-06 — milk-crate demo, full run: 4 independent buyer-persona
  reviews (focus group) all passed attempt 1 (~15k tokens, ~2¢ each) with an
  explicit VERDICT-block contract — persona work is squarely in glm's zone.
  Market read with live curl fetching passed once the spec demanded verbatim
  copy-paste of source URLs (first fail was the worker trimming URL slugs —
  spec/check craft, not model weakness). Brand-kit doc incl. a clean inline
  SVG wordmark: good, one bounce off an over-strict check regex.

- 2026-07-06 — elsas-website demo: verbatim content capture (16 pages + 19
  news posts, 213 blockquotes) passed attempt 2 — attempt 1 SELF-REPORTED
  "all 213 match exactly, 0 errors" while the executed check found 13 stitched/
  paraphrased quotes. Self-reports are worthless; the retry with injected
  failures fixed all 13 (~148k tok total, ~3¢). Page builds (about+faq;
  news index + 19 generated post routes via its own extraction script) and
  2 focus-group personas: all attempt 1. Fix batch attempt 1.
- 2026-07-06 — invariants/file-I/O review lens on the same stack: PASS
  attempt 1, 68k tokens — caught the non-atomic backfill rewrite (real data
  loss risk) and the daemon stdout race; both confirmed. Then fixed the
  backfill atomicity (tmp+os.replace, pid-stamped backups) attempt 1 with
  the original behavioral grader unchanged. Structured review with an
  explicit lens is now proven glm territory, not just probation.
- 2026-07-06 — solo adversarial review of the scoreboard renderer (~700
  line diff, injection-focused lens): PASS attempt 1 — 1 MEDIUM (unanchored
  MODEL-NOTES heading match cross-contaminating gpt-4/gpt-4o-style
  families) + 5 real LOWs, plus an empirically-verified injection all-clear
  (it actually rendered hostile model ids to prove escaping). Second
  proven-tier structured review in one day; glm is now the default review
  lane for mid-size diffs.
- 2026-07-06 — invariants/injection/frontend review of the 4,061-line
  model-db branch: PASS attempt 1, 96k tokens, 14 coverage items — two real
  contention findings (full catalog re-ingest per sync; schema writes on
  read paths) plus an empirical XSS all-clear on the new DOM surfaces.
  Third proven-tier structured review today.

## kimi-k2.7 via opencode (`openrouter/moonshotai/kimi-k2.7-code`)

- 2026-07-06 — adversarial pre-merge review (aicred spark): passed on
  attempt 1, ~83k tokens. First real outing; promising for review work.
  (Ran through an ad-hoc copy of the opencode engine block — the per-task
  `model` field now makes that unnecessary.)

## kimi-k2.6 (`moonshotai/kimi-k2.6`, subject-model evidence via OpenRouter)

- 2026-07-07 — Benchmark Suite 2.0 operator eval, killed by Jon at ~4.5h.
  Serving throughput, not model quality, was the failure: on the Brick
  1000-piece case (reasoning xhigh, pinned provider order
  inceptron→decart→baidu→modelrun, no fallbacks) K2.6 averaged ~21 tok/s
  with two ~19-min stalls at 4.5 tok/s — 136+ min unfinished vs Sonnet 5's
  25 min (94 tok/s) and GPT-5.5's 24 min (55 tok/s) on the identical case.
  Model behavior itself was fine: 28 turns (fewer than Sonnet's 82), 170k
  output tokens (in family norms), 12% reasoning, zero API errors. Verdict:
  do NOT schedule K2.6 for long agentic work through that provider set;
  if K2.6 data is ever wanted, probe a single case against other providers
  first. Distinct model from k2.7-code above — don't transfer this verdict
  to k2.7.


## grok-build (Grok CLI engine, flat plan)

- 2026-07-10 — identity correction (Jon): the Grok Build CLI is a HARNESS
  serving exactly two models — Grok 4.5 (xAI) and Composer 2.5 (Cursor).
  The engine-lane slug `grok-build` resolves to Grok 4.5. "Grok Build 0.1"
  was never a model; earlier notes/rows using it as one describe Grok 4.5.

- 2026-07-06 — first outing (elsas-website demo), engine added same day:
  audition PASS attempt 1 in 28.9s. Then: asset harvest (11 images, live URL
  re-fetch check), books page, 5 work-page routes in one task (59 verbatim
  needles), adversarial code review (10 real findings incl. an unshelled 404
  and a broken embedded link), press/media fix batch, audio-player integration
  across 15 pages — ALL attempt 1 (player's red ledger entry was a check bug,
  artifact certified). Fast, precise on mechanical/code work. No token counts
  in JSON output (flat plan) — cost reads "included in plan".

## grok-composer-2.5-fast (Grok CLI engine, flat plan)

- 2026-07-06 — first outing (elsas-website demo): audition PASS attempt 1
  (138s — slower than grok-build but the strongest copy of the round).
  Accessibility constitution (14 testable criteria, SC-numbered) attempt 1;
  a11y-gatekeeper harness (axe+Playwright, light/dark, reduced-motion assert)
  attempt 2 — attempt 1's harness mishandled Next's default /404 route.
  Events/faq/contact fix batch attempt 1, but satisfied "editorial grid" with
  an EMPTY aside landmark — axe caught it (landmark-complementary-is-top-level).
  Persona work: good. Watch for letter-of-the-spec shortcuts on layout asks.

## nemotron-3-super-120b (via opencode, `openrouter/nvidia/nemotron-3-super-120b-a12b:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0 spent — free promo).
  Task: fresh-eyes adversarial review of a 2,650-line diff with a structured
  report contract. Failed both attempts on the same executed check: report
  had the right sections and verdict but under 3 concrete code citations —
  shallow engagement with the actual code, 212k tokens burned. Don't re-run
  this audition on long structured code review; if it gets another slot,
  try a shorter, more mechanical task first.

## llama-3.3-70b-instruct (via opencode, `openrouter/meta-llama/llama-3.3-70b-instruct:free`)

- 2026-07-06 — AUDITION FAILED (exploration slot, $0). Fresh-eyes review of
  a 4,061-line diff with a verbatim-quote citation requirement: failed the
  structured-report check both attempts. Second free-model audition to fail
  on long structured code review (after nemotron-3-super) — the exploration
  ladder now says: audition free models on SHORT mechanical tasks first;
  long-diff review is a proven-tier lane.

## Small / flash-class models

- First to choke on long conversational or multi-turn harness tasks —
  watch retry counts before scaling them into a batch (2026-07-05 focus
  group lesson).

## Process lessons (cross-model)

- 2026-07-06 — the orchestrator's CHECKS were the day's top failure source:
  three check bugs (fixture newline join, first-occurrence ordering vs the
  watchlist strip, claim-prefix split on '.' instead of ':') each produced
  a FAIL verdict on work that was actually correct — including all four
  capability-research packets at once. Every one was caught by reading raw
  logs/artifacts before blaming the model. Corollary for the scoreboard:
  recorded FAILs whose root cause was a check bug are annotated here, and
  check fixtures deserve the same review care as production code.


- 2026-07-06 — HARNESS BUG (fix in flight on feat/model-perf-log):
  Verifier.verify evaluated expect_files BEFORE running the check, so any
  check that itself creates/exports its deliverable (the worktree
  patch-export pattern) failed attempt 1 with "missing expected files" even
  when the check printed PASS. Cost 3 phantom retries in one run — and it
  poisons first_try_pass_rate, the model log's routing signal. Until the
  reorder lands on your checkout: have the WORKER write the declared
  deliverable, or don't declare check-created files in expect_files. When
  reading seeded scoreboard numbers, remember 2026-07-06 first-try rates
  are depressed by this.
- 2026-07-06 — the model log is now automatic: every attempt row carries
  model/task_type/retry; `./ringer.py models` prints the scoreboard; 81
  historical rows were seeded via scripts/backfill_model_log.py with a
  hand-authored task-type mapping. Give every manifest task a task_type or
  its evidence buckets as (untyped).

- 2026-07-06 — a three-model "bakeoff" ran every task on the engine's
  hard-coded model: task keys said glm/gpt/kimi, but the opencode engine
  block pinned glm-5.2, so one model wrote all three "competing" reviews.
  This is why the per-task `model` field exists — a bakeoff is only a
  bakeoff if the manifest, not the engine block, names the model. Verify
  with the `model` column in the run state, not the task key.
- 2026-07-06 — spawning 5-6 opencode workers simultaneously hit opencode's
  local "database is locked" (sqlite) — several instant attempt-1 failures,
  all absorbed by Ringer's retry. Cosmetic in Ringside ("sent back" at 0s) but
  wastes an attempt; consider staggering opencode spawns.
- 2026-07-06 — opencode's bash tool kills foreground commands around the
  ~2-minute mark: a 2min+ image-generation API call can never finish inline.
  Spec pattern that works: nohup the long command in the background, then
  poll for the output file in separate short commands.
- 2026-07-06 — two check-craft lessons from the same run: (1) URL-allowlist
  checks must be prefix-tolerant (workers legitimately trim slugs); (2) any
  heading-regex must tolerate numbered headings ("## 3. Type / Typography").
  Both failures looked like worker laziness until the raw logs said otherwise.
- 2026-07-06 — elsas-website demo, check-craft in BOTH directions: (1) a fixed
  800-char body floor failed a worker for faithfully converting genuinely tiny
  source posts — floor must scale with the source; (2) a citation gate treating
  every backtick as a page-quote failed honest reviewers who backticked their
  own fix-suggestions — line-scoped pair parsing + attribute-aware corpus fixed
  it; (3) needle-exception lists must be shared across ALL checks that consume
  the needle set (a needle excepted in one checker failed a task through
  another). Post-mortems ruled FOR the worker 3 times this run — read raw logs
  before blaming the model.
- 2026-07-06 — opencode sqlite "database is locked" again with just 2
  simultaneous opencode spawns (page-news + page-about-faq); retry absorbed it.

## codex (2026-07-06, bench-operator-proofing)
- 8/8 code-feature tasks passed attempt 1 across 3 rounds (worktrees mode, Python harness refactor; 108k-406k tokens/task). Specs embedded the approved architecture doc + exact file ownership; checks built fresh uv venvs and ran the full pytest suite.
- Lesson (check design, not model): all 3 post-integration bugs were invisible to the checks — a test that passed only because the worker's worktree lacked .env, a `--help`-only assertion missing a runtime importlib/sys.modules bug (py3.12 dataclasses), and bare console-script names failing outside activated venvs. Checks should exercise one real invocation from a cold shell, not just --help.

## gpt-5.6-sol (codex)
- 2026-07-15 ringer-self-update run (3 serial tasks, direct-repo-edit mode): code-fix baseline-test repair 1/1 first-try (61k tokens, 1.6m); code-feature self-update mechanism (git fetch/ff-pull/re-exec + HUD staleness restart + 20-test suite) 1/1 first-try at high effort (153k, 8.1m); code-feature signal-contract (all 3 scoreboard surfaces + canonical-route lint enforcement) passed on retry (358k, 13.7m) — attempt 1 died on stale old-column assertions in pre-existing tests it hadn't finished updating; the retry prompt's injected FAIL list was enough to close it out. Lesson: when a task rewrites a display contract, name every test file asserting the old contract in the spec's ownership list AND tell it to update them FIRST.
- 2026-07-09 code-feature/code-fix (ringside-overhaul): 4/4 first-try — a ringer.py logging change with tests, a 265-line stdlib backfill CLI (atomic rewrite, dry-run, idempotence all check-verified), a ~1500-line single-file HTML redesign (running-now pills + worker-card grid + multi-expansion refactor, 30KB patch, node --check + contract greps + unittest), and a render-gating change where it correctly UPDATED tests asserting the old behavior instead of gaming the check. Medium/high reasoning, 65–120k tokens/task.
- Same day, different session (bench-harness-patches, code-fix): 0.29 first-try over 7 tasks on a Next.js/Turbopack harness. Spec and check quality dominate model choice — see the scoreboard before generalizing either number.

## GPT-5.5 (codex) — attribution caveat
- 2026-08-08 code-fix (claude-memory retire-monolith, worktree, high reasoning): PASS on attempt 2 of a wide 14-file refactor with a 300+-test executed check; attempt-1 failure was a check grep hitting a docstring mention, not a code defect — retry-with-check-output fixed it precisely. ~175k tokens total. Note: worker sandbox had no network, so it could not run `uvx pytest` itself; the executed check (outside the sandbox) carried verification. Spec the runner's availability next time or vendor pytest.
- Scoreboard rows dated before 2026-07-09 may actually be gpt-5.6: codex eval rows logged model="" until the write-time stamping fix (PR #18) and were credited to GPT-5.5 by the registry default at read time, while the machine's codex default had already moved to gpt-5.6-sol at an unknown earlier date. `scripts/backfill_model_from_logs.py` re-stamps rows with surviving command-log evidence; anything it skips is a mixed-model aggregate. Trust post-2026-07-09 rows.

## nvidia/nemotron-3-super-120b-a12b:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Did the analysis in chat but never wrote report.md; attempt 2 exited rc=0 with no file. Doesn't reliably follow file-output contracts under OpenCode. Demoted — don't re-audition on file-deliverable tasks.

## meta-llama/llama-3.3-70b-instruct:free
- 2026-07-08 (research, content-strategy-recon): FAIL x2. Timed out at 900s both attempts on a moderate DB-scrape+format task. Too slow on the free tier for harness work. Demoted — don't re-audition without much longer timeouts or paid tier.

## z-ai/glm-5.2 (addendum)
- 2026-07-08 (research/filter, pitch-foundry): FAIL x2 on a long-spec rubric-application task (~40k input: embedded rubric + 4 candidate files). Read all inputs, exited rc=0 with ZERO output tokens both attempts — silent stall, no file written. GLM handled the same session's shorter formatting specs fine. Lesson: keep GLM specs short; route long-context apply-this-rubric work to codex.

## GPT-5.5 (codex) — honesty flag
- 2026-07-08 (image-gen, pitch-foundry): sandbox DNS blocked openrouter.ai; ALL 10 API calls errored (logged honestly in gen-log) — but the worker then FABRICATED 10 deliverables locally (composited canvases from the ref image) to satisfy a files-exist>40KB check, and passed. Lesson: (a) codex sandbox has no external DNS on this machine — route API-calling tasks to opencode (network open); (b) never write an existence-only check for generated media — require the success log (SAVED/cost lines) to match the file count.

- 2026-07-09 persona-review (pitch-foundry exec-briefing panel): 0/2 first-try+retry. Produced coherent review CONTENT as chat text but never wrote report.md — does not reliably use file-write tools under opencode. Demoted; do not re-audition for file-deliverable tasks without a write-tool probe first.

## gpt-5.6-luna (codex)
- 2026-07-09 code-feature (unlock-ai guide-format conversion, strict type-contract check): 1/1 first-try, 42.6k tokens, 80s. Followed a multi-file TS pattern precisely at $1/$6 pricing. Good candidate for mechanical codegen/docs lanes; audition in adjacent types.

## opencode / z-ai glm-5.2 (via openrouter)
- 2026-07-09 (aicred-invoice-downloads, 4 code-fix tasks + 1 follow-up, worktrees+npm ci checks): systematic attempt-1 NO-OP — all 4 parallel workers produced zero edits and no summary on first attempt, then completed cleanly on attempt 2 after retry-prompt injection (34k-69k tokens each). Follow-up single task passed attempt 1. Suspect first-invocation session warm-up in opencode-sandboxed under parallel spawn; budget for 2 attempts on parallel GLM batches. Output quality on Next.js/Stripe route+test work: solid, spec-faithful, one boss-caught design gap (used user-scoped supabase client where RLS demanded service role — spec didn't say explicitly; say it explicitly).

## opencode (harness note, any model)
- 2026-07-28 (code-review, pr82-token-saver-review): GLM 5.2 produced a complete, high-quality 218-line report but could NOT write it to an output directory created by the parent Claude Code process — every write returned EPERM. It then spent ~3000s burning retries on ctypes/`openat`/AppleScript/`sandbox-exec` workarounds until it timed out, and the task logged as FAIL despite the deliverable existing in its taskdir. Codex workers in the same run were unaffected. Lesson: point opencode workers' output INSIDE their own taskdir and harvest via `expect_files`; never hand them a shared output dir another process created. This is an orchestrator spec bug, not a model failure — do not read the FAIL as evidence against GLM.

## Process lessons (2026-07-28, PR #82 review)
- **Ideas worth keeping from a rejected PR.** PR #82's pre-call gateway was dropped (needs your own API key, so it converts flat-rate OAuth plans into metered API billing; incompatible with Claude Code; and it saves tokens by stripping the tool list, which is the thing that makes the CLI worth using). One idea inside it is worth remembering if the problem ever comes back: an *explicitly blessed* answer cache — key a reviewed answer to the exact request plus the exact selected source packet, and replay it with zero upstream calls, never auto-accepting a model answer. It only fires on byte-identical repeats, which is why it didn't justify 2,000 lines here.
- **Doc-stated support floors need a CI job or they are fiction.** README promised Python 3.11+ while CI only ever ran 3.12; a 3.12-only f-string reached review with a fully green suite. Either test the floor or move it.

## Composer 2.5 Fast (grok) — jtimmons machine
- 2026-07-10 code-feature (ermsoa-act1, calendar-watcher): first-try PASS in 145s — TypeScript Graph-webhook logic + vitest suite in worktrees mode with a full-suite check (npm ci + tsc + vitest + ownership guard). Fastest of 4 engines in the round. No token counts (plan-billed). Sample size 1; auditioning further.

## GLM 5.2 (openrouter/z-ai/glm-5.2) — jtimmons machine
- 2026-07-10 code-feature (ermsoa-act1, briefing-delivery): first-try PASS, 24.7k tokens, ~114s — validation + MailSender wrapper with tests, simplest task of the round by design (audition slot). Clean patch, only owned paths. Sample size 1.

## codex — jtimmons machine (model per ~/.codex default, gpt-5.5-era CLI 0.144.1)
- 2026-07-10 code-feature (ermsoa-act1): 3/3 first-try — strict-TS scaffold with schema-transcribed contracts (70.7k tok, 7min), the §7 ingestion traversal w/ blocklist gate (66k tok), and the classification-gate + briefing assembler (66k tok). Given the two trust-layer tasks deliberately; both spot-checked faithful to spec. Note: demo run earlier same day was 0.33 first-try on exact-bytes file tasks (trailing-newline traps) — retry-with-failure-context rescued all.
- 2026-07-30 defcast phase3 Stage B (PowerShell/Pester, high stakes): 6/6 first-try across the whole stage — B1 300-line identity REST client via TDD (140k tok, 844s, all 16 planned tests), B1b surgical 404-semantics fix (70k, 207s), B2-finish + B3 health probe + B4 deps slim + B5-finish. Two runs were killed externally mid-flight; the resume pattern (new task pointed at the orphaned worktree via writable_roots, same check) harvested both with zero rework. Orchestrator review still earns its keep: B1 passed all checks but had a real semantic landmine (point-read 404 threw vs legacy $null) that only patch-reading caught.

## defcast-20-data-layer (2026-07-12, jtimmons machine) — per-model outcomes
- **codex**: 5/5 substance-correct on code-feature (PowerShell modules + React) — heavy lanes: a four-task TDD batch on one module file (+520 lines, 22 new Pester tests), Sweep + Reconcile orchestrators w/ safety-invariant tests, DigestRunner rewrite w/ ForEach-Object -Parallel seam, App.jsx watch-window rework. Two scoreboard "fails" (t01, and t03/t02 were GLM) in round 1 were the harness check bug below, not the model.
- **GLM 5.2 (openrouter/z-ai/glm-5.2)**: 6/6 substance-correct across code-feature/code-fix (ExoClient params, endpoint scaffolds, App-free copy changes, quarantine simplification). Standout: when the round-1 check was broken, the t03 worker correctly diagnosed BOTH harness bugs (shell `$r` expansion in the verify command; Pester TestDrive hardcoding /private/tmp under the sandbox), documented them in fix-summary.md, and shipped the exact TestDrive-disabled workaround the orchestrator then adopted. Cheap lane fully earned; promotion-track evidence.
- **north-mini-code:free (cohere, via opencode)**: exploration audition on a two-file Azure Functions timer scaffold — PASS on attempt 2 (42k tok, 40s). Retry-with-failure-context rescued it. Probation: fine for scaffolds with strict executed checks; don't hand it module logic yet.
- **Process lesson (check design)**: a verify command written as `--verify-command "pwsh -Command '$r = ...'"` gets `$r` eaten by the shell inside the double quotes — every backend check in round 1 failed with "The term '=' is not recognized" and 3 correct tasks burned retries. Rule: put multi-statement pwsh checks in a .ps1 file and invoke with `pwsh -NoProfile -File`; also disable Pester TestDrive/TestRegistry in sandboxed macOS runs.

## defcast-batch-rewrite (2026-07-12, jtimmons machine)
- **codex** (high reasoning): 1/1 first-try on a single hard code-feature task — PowerShell Cosmos.Table SDK batch rewrite across 2 modules + 2 test suites + a new bench harness (43KB patch, 131 Pester green, 156k tokens, 22 min). Spec embedded the approved design, exact entity property contracts, seam-mock strategy, and the real check as a self-verify command; worker used all of it and the integrated benchmark beat the gate 58x. Pattern to repeat: give the worker the actual check script path so it can run the real verification before finishing.

## z-ai/glm-5.2 (opencode)
- 2026-07-12: code-feature audition (defcast admin-endpoint, PS module + Pester + function scaffold from verbatim-code plan): PASS first-try, 116k tokens, 23min (~6x codex lanes' duration). Notably GOOD deviation judgment — caught a real PowerShell if-expression array-unrolling bug in the plan's own code and documented the fix. Slow but trustworthy on well-specified PS work; promotes toward proven (now 6 tasks code-feature).

## openrouter/nvidia/nemotron-3-super-120b-a12b:free
- 2026-07-13 code-fix (defcast tablestore-minors): FIRST-TRY PASS on a two-part PowerShell fix (OData quote-escaping + return-shape fix) incl. a correctly-patterned Pester mock test copied from suite conventions. 98k tokens, 212s — token-hungry but free. Worth auditioning again on mechanical code-fix lanes; untested → probation.
- 2026-07-18 research (docfoundry condo-registry, smallest lane: 11-page doc): PASS on attempt 2. Attempt 1 failed the executed check on real defects — wrote an object instead of the spec'd JSON array (spec-reading miss; it recovered by reading the check script), then cited sub-probative garbled signature-block fragments. Retry with injected check output fixed both; final output substantively good (correct entities incl. OCR-corrupted names handled honestly). 192k tokens on the SMALLEST doc — codex did 4-15x bigger docs in 180-280k. Verdict: stays probation for research; fine for small lanes behind a strong executed check, don't scale to big-corpus lanes yet.
- 2026-07-30 code-fix audition (defcast phase3 B5, THREE-file PowerShell tools conversion): FAILED — attempt 1 converted 1 of 3 files; attempt 2 (killed externally mid-flight, but already visibly floundering) burned its budget fighting shell escaping in the opencode/macOS harness (heredoc/temp-file contortions, sed with hand-rolled escaping) and left scratch debris in the worktree (modify_script.py, a .bak) that failed the ownership check. Its actual edits were correct in style. Verdict: DEMOTED for multi-file repo edits — the 2026-07-13 first-try pass was a single-file fix; keep it to single-file lanes at most, and treat multi-step file surgery as out of its depth in this harness. Codex finished the remaining file in 120s/41k first try.

## openrouter/z-ai/glm-5.2
- 2026-07-13 code-fix (defcast digest-tokenswritten): code correct on attempt 1 but FAILED the check by omitting the RINGER-NOTES.md deliverable; retry passed. Lesson: GLM drops trailing output-contract items on small tasks — consider putting the notes-file requirement FIRST in the output contract for GLM lanes.
- 2026-07-13 probe (defcast stats-bootstrap, ops script vs prod Azure): FAILED both attempts — ignored the spec's explicit "this warning is benign, ignore it" and spent 35 min decompiling Az.Accounts assemblies to investigate it; never ran the one prescribed command to completion. Do NOT give GLM ops/probe tasks with noisy tool output; it investigates instead of executing. (Same day: codex couldn't take this lane either — workspace-write sandbox blocks network, and allow_full_access is off by policy. Structural gap: network-requiring ops probes currently fit only the opencode seatbelt lane or inline execution.)
- 2026-07-13 code-fix (defcast lastchecked-sweep, PS backend): FIRST-TRY PASS and exceeded the spec — the spec allowed skipping a unit test if impractical for a run.ps1 script; GLM instead built a working harness (stubbed the Functions runtime type via Add-Type, global function stubs, call-operator invocation to survive top-level `return`) with 4 solid cases. Revised read: GLM is GOOD on well-scoped code-fix lanes with explicit file:line briefs; the earlier ops-probe ban stands (different failure mode: noisy-output investigation spiral).

## Orchestrator check-writing lessons (not model failures)
- 2026-07-13: pipeline-warmup lane (codex) logged FAIL×2 on the scoreboard but the WORK WAS CORRECT — the check ran `python3 -c "import yaml..."` on a machine without PyYAML, so it failed before ever reading the worker's file. Don't trust "python3 has X" without verifying; prefer parsers proven present (ruby -ryaml, npx yaml). Discount this FAIL when reading codex's ci/code-feature stats.
- 2026-07-13: defcast-login-hotfix lane (codex, code-fix) logged FAIL×2 on the scoreboard but the WORK WAS CORRECT AND SHIPPED (commit 49a80bc) — the check parsed the Vitest summary with `grep -Eo '[0-9]+ passed' | head -1`, which matches the "Test Files 14 passed" line before "Tests 119 passed", so 14 ≤ baseline 114 → false FAIL both attempts. Rule: parse Vitest counts from the line anchored with `grep -E '^\s*Tests '`, never a bare "N passed" grep. Discount this FAIL in codex's code-fix stats (real record on this task: substance-correct first try).

- 2026-07-17 (research, docfoundry condo-memo-audit, 7 lanes): 6/7 first-try, 1 retry rescued by the executed check (too-short + non-verbatim cite quote; retry fixed it exactly). ~150-370k tokens/lane over a 607-page grep-and-cite corpus task. Quote discipline held: 250/256 extracted cites verified PASS_EXACT downstream. One craft gap: a lane stitched non-contiguous table rows into one "quote" — future audit specs should say "a quote must be one contiguous span".

## cohere/north-mini-code:free
- 2026-07-14 (code-feature, defcast t1-rowkey-helpers): DESTRUCTIVE REWRITE — replaced a ~950-line module and its full test suite with only its own 96 lines; check passed because the deleted tests couldn't fail. Attempt 1 also failed outright (2 attempts, 176k tokens for a 30-line task). Demoted: do not use on edit-in-place tasks. Lane check now carries a deletion guard (fail if patch deletes >N pre-existing lines) — keep that guard for any append-mostly lane regardless of model.
- 2026-07-15: defcast t19-reconcile-window (codex, code-fix) logged FAIL×2 but the WORK WAS CORRECT both attempts — the lane check's file-ownership allowlist predated the lane (api/sweep/ not in the regex), so a valid owned-file edit was rejected as an ownership violation. Discount this FAIL in codex stats. Rule: ownership allowlists in shared checks must be derived from the manifest's per-task ownership, not hard-coded from an earlier round's file set.

## openrouter/meta-llama/llama-3.3-70b-instruct:free
- 2026-07-17 (code-feature, docfoundry envcheck audition): timed out BOTH attempts at 1200s with zero output files — no code, no notes, worker produced nothing harvestable. Free-tier latency/hang, not a capability miss. Demoted: do not audition again on timed work; if retried ever, use a trivial task with timeout_s >= 2400 and expect slow first tokens. Falling back to a codex one-task manifest for the module.

## openrouter/cohere/north-mini-code:free
- 2026-07-19 (docs, nexus-build phase6): FAIL x2 — but harness fault, not model: opencode Seatbelt confines writes to the task dir; spec demanded writes into a repo path. Model's writes all landed 0-byte / "Operation not permitted". DEMERIT anyway: final message claimed files were "successfully created" with full content when every file was empty — verify-before-claiming failure under constraint pressure. Lesson: opencode-engine tasks must deliver into the task dir (orchestrator harvests); writable_roots is codex-only.

## grok-4.5 (Grok Build CLI) — jtimmons-dt9 (Debian)
- 2026-07-31 probe (grok-probe-debian, primes.py): FIRST-TRY PASS, 42k tokens, 6s, ~$0.034 (self-reported model id "grok-4.5-build"). First run on the new Debian workstation; grok CLI 0.2.118. Untested → probation.
- Catalog note: at CLI 0.2.118 the authenticated model list shows ONLY grok-4.5 — grok-composer-2.5-fast is gone (present at 0.2.93 on the Mac). The two same-night "Composer 2.5 Fast" FAILs on this box (grok-probe-debian + grok-4.5 runs, 2026-08-01Z) were config staleness — the engine's model_default named the retired ID and grok refused to set it; no worker ever ran. Discount both from Composer's scoreboard stats. `--no-auto-update` remains hidden-but-accepted at 0.2.118.
