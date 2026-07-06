# Project Constitution

## 1. Purpose

The Platform is a teaching-and-assessment tool for **instructors** and
**students**. Instructors author and host exams and assignments, and grade
submissions with the assistance of AI agents. Students take exams and receive
feedback on their grades.

Because AI agents assign grades that affect real students, the entire system is
built around three non-negotiable commitments: **auditability**, **human
oversight**, and **data protection**. Every principle below serves at least one
of those.

## 2. Architecture principles

- **P-1 — Contract-first.** The OpenAPI documents under `/contracts` are the
  single source of truth for every service boundary. Backend and frontend are
  both **generated from / validated against** the contract. Code never defines a
  boundary the contract doesn't describe.
- **P-2 — Microservices with clear ownership.** Each backend service owns its
  data and exposes it only through its documented API. Services SHALL NOT read
  another service's database tables directly.
- **P-3 — Spec before code.** For any new feature or change, the relevant spec
  (and, if a boundary changes, the contract) is updated and reviewed **before**
  implementation begins. Code serves the spec, not the reverse.
- **P-4 — Stateless services.** Application services hold no session state in
  memory; all durable state lives in MySQL (RDS) or S3. This is required for
  Fargate horizontal scaling.

## 3. Technology constraints

- **T-1** — Backend services are **Python + Flask**. Persistence is **MySQL**
  (AWS RDS).
- **T-2** — Frontend is a **Vite + React** single-page application.
- **T-3** — Deployment targets **AWS**: Fargate (compute), RDS (MySQL), S3
  (object storage, e.g. submissions and assets), Secrets Manager (all
  credentials and API keys). Infrastructure is defined as a **Python AWS CDK**
  project in the `infra` module.
- **T-4** — No credential, API key, connection string, or other secret is ever
  committed to any repo or baked into an image. Secrets are resolved at runtime
  from Secrets Manager only.

## 4. AI agent principles

These govern every AI-assisted capability (exam authoring, exam grading,
assignment authoring, assignment grading).

- **AI-1 — Human in the loop for anything that affects a grade.** AI-produced
  grades and feedback are **provisional** until an instructor can review them.
  An instructor SHALL always be able to view, override, and re-run any AI grade
  before it is released to a student.
- **AI-2 — Every AI decision is auditable.** For each AI-generated artifact
  (drafted question, grade, feedback comment) the system SHALL persist: the
  model identifier and version, the rubric/prompt version used, the exact inputs
  provided, the raw output, and a timestamp. This record is immutable.
- **AI-3 — Reproducibility.** Model versions and rubric versions are pinned and
  recorded per run so a grade can be explained and, where the provider allows,
  reproduced.
- **AI-4 — Data boundary.** Student submissions, PII, and grades SHALL NOT be
  used to train third-party models. Only no-retention / enterprise inference
  endpoints are permitted for student data.
- **AI-5 — Confidence and escalation.** When an agent's confidence is low, or a
  submission falls outside the rubric, the item SHALL be flagged for mandatory
  human review rather than auto-released.
- **AI-6 — Rubric-grounded grading.** A grading agent SHALL grade only against
  the stored acceptable-answer / rubric for the item. Grades include a rationale
  that references the rubric.

## 5. Security, privacy & data handling

- **S-1** — Student PII and grades are **sensitive data**. Encrypt at rest (RDS
  and S3) and in transit (TLS everywhere, including service-to-service).
- **S-2** — **Least privilege.** Every IAM role, DB grant, and service token
  grants the minimum access required. Cross-service access is via documented
  APIs, not shared credentials.
- **S-3** — **Exam confidentiality.** Exam content and answer keys SHALL NOT be
  retrievable by any student-role principal before that student's exam window
  opens, and answer keys never.
- **S-4** — Access to grades and submissions is restricted to the owning
  instructor(s), authorized course staff, and the student the record belongs to.
- **S-5** — Personal data and secrets never appear in URLs, query strings, logs,
  or client-visible error messages.

## 6. Exam integrity

- **I-1** — Exam timing is **server-authoritative**. The client clock is never
  trusted for start, remaining time, or auto-submit.
- **I-2** — Integrity rules (e.g. tab-focus enforcement and lockout on leaving
  the exam tab) are enforced and their triggering events are recorded
  server-side for instructor review.
- **I-3** — Student answers are autosaved so a lockout, refresh, or disconnect
  does not lose work.

## 7. Quality gates

- **Q-1** — Every service ships **contract tests** verifying its implementation
  conforms to its OpenAPI document. A boundary change is not "done" until the
  contract and its tests are updated.
- **Q-2** — CI SHALL block merges that fail contract tests, lower test coverage
  below the agreed threshold, or introduce a secret into the repo.
- **Q-3** — Database schema changes go through versioned migrations; no manual
  production schema edits.

## 8. Spec-driven workflow rules

- **W-1** — Specs are living documents. When behavior changes, the spec changes
  in the same change set as the code — never after.
- **W-2** — Changes are versioned. This constitution and each contract use
  semantic versioning; breaking a published contract is a **major** bump and
  requires a migration note.

---

### Change log

| Version | Date | Change |
| --- | --- | --- |
| 0.1.0 | (init) | Initial draft |
