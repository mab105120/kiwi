# Phase Roadmap

This roadmap sequences the platform's two functional tracks — **exams** and
**assignments** — into phases small enough to spec, build, and ship
independently (constitution P-3, W-1). Exams go first and in the most detail,
since assignments reuse most of the same architecture (authoring → posting →
taking/submitting → AI grading → feedback) once it's proven out.

Each phase lists: goal, key deliverables, contracts touched, and exit
criteria. A phase is "done" when its exit criteria hold, its contracts +
contract tests are merged, and its spec under `specs/features/` reflects
what was actually built (W-1).

---

## Phase 0 — Scaffolding

**Goal:** a deployable skeleton with nothing functional yet, so every later
phase adds features instead of infrastructure.

- Repo layout (`backend/`, `frontend/`, `infra/`, `contracts/`) with CI
  running contract tests, lint, and type checks (Q-1, Q-2).
- `infra/`: CDK stacks for VPC, RDS (MySQL), S3 buckets, Secrets Manager,
  Fargate service shells for `identity`, `app-api`, `worker` (T-3, T-4).
- `platform_common`: shared auth/JWT verification, error format, logging
  (with PII redaction per S-5) used by all three services.
- `/healthz` on every service, deployed end-to-end once via CI/CD.

**Exit criteria:** empty services deploy to AWS via CDK; CI blocks on failing
contract tests; no secrets in repo.

**Feature breakdown** (build in this order; scaffold each `specs/features/`
folder when you start it, not before):

1. [x] `feat-01-repo-tooling` — real `Makefile` targets, `uv` workspace
   wiring, frontend install/lint/test scripts. No AWS. Do first —
   everything else needs a working local dev loop.
2. [ ] `feat-02-platform-common-lib` — JWT verification, shared error
   envelope, logging with PII redaction (S-5). Pure backend, can run in
   parallel with #1.
3. [ ] `feat-03-infra-network-data` — CDK `network_stack.py` +
   `data_stack.py` (VPC, ALB, RDS, S3, Secrets Manager, SQS). No compute
   yet; can also run in parallel with #1/#2.
4. [ ] `feat-04-ci-pipelines` — flesh out the three service CI workflows +
   add frontend CI: lint, test, contract tests, docker build. Depends on
   #1 and #2 existing so there's something real to check.
5. [ ] `feat-05-infra-service-shells` — CDK Fargate stacks for `identity`,
   `app-api`, `worker`, each exposing only `/healthz`. Depends on #3.
6. [ ] `feat-06-infra-frontend-shell` — minimal Vite scaffold + CDK
   `frontend_stack.py` (S3 + CloudFront) serving a blank deployed page.
   Depends on #3.
7. [ ] `feat-07-deploy-pipeline` — CD wiring (build+push images,
   `cdk deploy` on merge) tying #4 to #5/#6. Last — this is what actually
   satisfies the
   phase exit criteria end-to-end.

## Phase 1 — Identity & Access

**Goal:** instructors and students can authenticate and be scoped to courses.

- `identity` service: Cognito-backed auth, user profiles, roles
  (instructor/student/admin), courses, enrollments.
- Contracts: finish `identity.openapi.yaml` (currently TODO stubs).
- Frontend: login, course list/switcher, protected routes by role.

**Exit criteria:** an instructor and a student can log in, and each sees only
the courses they're enrolled in/teach. This unblocks everything else, since
every exam/assignment endpoint needs a course + role context.

---

## Exams track

### Phase 2 — Exam authoring (manual)

**Goal:** an instructor can build an exam by hand — no AI yet. Get the data
model and authoring UX right before adding AI on top of it.

- `app-api`: exams, sections, questions (MCQ, short-answer, free-text),
  rubrics/acceptable-answer keys, draft/versioning.
- Contracts: flesh out `contracts/app-api/paths/exams.yml` + question/rubric
  schemas — this is the shape the AI-authoring agent in Phase 3 will also
  have to produce, so get it reviewed carefully now.
- Frontend: exam builder UI (create/edit questions, attach rubric, save
  draft).
- S-3 groundwork: answer keys are a separate, more restricted read path from
  question text, even though nothing is posted to students yet.

**Exit criteria:** instructor can author a complete exam with rubric,
save/reload it as a draft. No publishing, no students involved yet.

### Phase 3 — AI-assisted exam authoring

**Goal:** an instructor can ask an agent to draft questions/rubrics from a
prompt (topic, difficulty, learning objectives), then review and edit before
the exam is usable.

- `worker` (or a synchronous authoring endpoint, TBD in spec): authoring
  agent that drafts questions + rubric into the Phase 2 data model as
  `ai_draft` status, never `published`.
- AI-2 audit record on every generated artifact: model id/version, prompt/
  rubric-template version, inputs, raw output, timestamp — immutable.
- Frontend: "generate with AI" flow inside the Phase 2 builder; diff/accept/
  edit UI so instructor edits are visibly distinct from AI output.
- AI-4: authoring prompts contain no student data at this stage, so this is
  the easiest place to first wire up the no-retention inference endpoint.

**Exit criteria:** instructor can generate a full draft exam from a prompt,
see the audit trail for each item, and edit/approve before it's usable
downstream. Nothing AI-drafted is ever auto-published (AI-1).

### Phase 4 — Exam publishing & scheduling

**Goal:** an approved exam can be posted to a course with a real time window.

- `app-api`: publish/version-lock an exam, assign to a course + cohort,
  exam window (open/close, duration), late-start policy.
- S-3 enforcement: question content and answer keys are unreachable by any
  student-role principal before their window opens; answer keys never
  reachable by students at all — this needs authz tests, not just code.
- Frontend: instructor "post exam" flow; student-facing "upcoming exams"
  list (metadata only, no content) once posted.

**Exit criteria:** a student can see an exam is scheduled and when it opens,
but cannot fetch any question/answer content before the window starts.
Verified with a negative-path authz test.

### Phase 5 — Exam hosting (student-facing runtime)

**Goal:** a student can actually take a posted exam.

- `app-api`: start-attempt, server-authoritative timer (I-1), autosave per
  answer (I-3), auto-submit at window close, tab-focus/visibility event
  logging (I-2).
- Contracts: attempt/submission schemas; SQS or equivalent notification when
  a submission finalizes (feeds Phase 6).
- Frontend: exam-taking UI — timer, autosave indicator, lockout behavior on
  tab-blur, resume-after-disconnect.

**Exit criteria:** a student can start, answer, get disconnected/refresh
without losing work, and get auto-submitted at the deadline. Integrity
events are visible to instructors (even if the review UI comes later).

### Phase 6 — AI grading

**Goal:** submitted exams get a provisional AI grade, never auto-released.

- `worker`: consumes the grading-job queue (`contracts/messages/
  grading-job.schema.json`), grades strictly against the stored rubric
  (AI-6), attaches rationale referencing the rubric, writes AI-2 audit
  records.
- AI-5: confidence scoring; low-confidence or out-of-rubric submissions are
  flagged for mandatory human review instead of just queued normally.
- AI-4: grading path uses the no-retention inference endpoint exclusively —
  this is the one that actually touches student submissions/PII, so this is
  where that constraint is load-bearing, not optional.
- Frontend: instructor "review AI grades" queue — view rationale, accept,
  override, or re-run (AI-1, AI-3 reproducibility).

**Exit criteria:** every AI grade is provisional until an instructor acts on
it; overrides and re-runs are themselves audited; nothing reaches a student
yet (that's Phase 7).

### Phase 7 — Grade release & feedback

**Goal:** close the loop back to the student.

- `app-api`: release grades/feedback to students (only after instructor
  sign-off from Phase 6), per-question feedback comments, grade history.
- S-4 enforcement: grades/submissions visible only to owning instructor(s),
  authorized staff, and the student who owns the record.
- Frontend: student results view (score, per-question feedback, rationale
  if the instructor chooses to share it); instructor gradebook/export.

**Exit criteria:** the full exam lifecycle is closed — author → post → take
→ grade → review → release — with an audit trail at every AI-touched step.
This is the milestone to treat as "exams v1."

---

## Assignments track

Assignments reuse the exam pipeline's shape (author → post → submit → grade
→ feedback) but drop timed-proctoring concerns (no I-1/I-2 timer/lockout) and
add file-based submission. Because the pattern and most of the
`platform_common`/worker plumbing already exist after Phase 7, this track
should move faster than exams did.

### Phase 8 — Assignment authoring (manual + AI-assisted)

- `app-api`: assignments, prompts/instructions, rubrics, file/artifact
  requirements (vs. question-and-answer for exams).
- Reuse the Phase 3 AI-authoring agent pattern: draft assignment prompt +
  rubric from instructor input, same audit trail, same draft/approve gate.
- Combine what were two exam phases (2+3) into one here, since the
  authoring-review UX and audit plumbing are already built.

### Phase 9 — Assignment posting & submission

- `app-api`: due dates, late policy (vs. hard exam windows), file upload to
  S3, resubmission rules.
- No server-authoritative timer/lockout needed — this phase is materially
  simpler than exam hosting (Phase 5).

### Phase 10 — AI grading for assignments

- Reuse the Phase 6 worker/grading pipeline; extend rubric-grounding (AI-6)
  to handle file/artifact submissions (e.g. code, documents) instead of
  structured question answers.
- Same AI-5 escalation and AI-1 human-in-the-loop gate.

### Phase 11 — Feedback & grade release for assignments

- Reuse Phase 7 release/feedback machinery as-is; the main net-new work is
  UI (assignment gradebook) rather than backend.

**Exit criteria for the assignments track overall:** feature parity with the
exam lifecycle (author → post → submit → grade → review → release), reusing
shared services rather than forking them.

---

## Phase 12 — Cross-cutting hardening

Pulled to the end deliberately — do this once both tracks exist so it's
informed by real usage instead of guessed at.

- Instructor-facing audit log / AI-decision explorer (surfacing the AI-2
  records accumulated since Phase 3).
- Analytics/reporting (course performance, grade distributions).
- Load/scale pass on `worker` (grading queue depth, Fargate autoscaling).
- Security review across S-1..S-5 and a real pentest of exam confidentiality
  (S-3) and grade access (S-4) boundaries.

---

### Sequencing notes

- Phases 2–7 (exams) are intentionally serial — each depends on the data
  model or audit plumbing from the one before it.
- Phases 8–11 (assignments) can partially parallelize with late exam phases
  once Phase 3's AI-authoring pattern and Phase 6's grading worker exist,
  since assignments are consumers of that plumbing, not inventors of new
  plumbing.
- Any phase that changes a service boundary updates `contracts/` and its
  tests first (constitution P-1, P-3) — the contract stubs already in this
  repo (`exams.yml`, `identity.openapi.yaml`, `grading-job.schema.json`) are
  the starting shape for Phases 1–6, not final.
