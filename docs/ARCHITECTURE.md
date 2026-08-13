# Architecture — Phase 1 (Foundation & Auth)

## Layering

```
┌─────────────────────────────────────────────┐
│  API layer (app/api)                         │  FastAPI routers + Pydantic schemas
│  - parses HTTP, calls services, no logic     │
├─────────────────────────────────────────────┤
│  Service layer (app/services)                │  Business rules
│  - AuthService: register/login/refresh rules │
├─────────────────────────────────────────────┤
│  Repository layer (app/repositories)         │  Data access abstraction
│  - AbstractUserRepository (interface)        │
│  - SqlAlchemyUserRepository (Postgres impl)  │
├─────────────────────────────────────────────┤
│  Model layer (app/models)                    │  SQLAlchemy ORM tables
│  - User, RefreshToken                        │
└─────────────────────────────────────────────┘
```

Dependency rule: an inner layer never imports an outer one. `AuthService`
depends on `AbstractUserRepository` (an interface), not on SQLAlchemy — this
is what let us unit test all auth business rules with an in-memory fake
repository in `tests/test_auth_service.py`, with no database required.

## Database schema (Phase 1)

**users**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| email | varchar(255) unique | login identifier |
| full_name | varchar(255) | |
| hashed_password | varchar(255) | bcrypt, never plaintext |
| role | enum(admin, analyst, viewer) | drives RBAC via `require_role()` |
| is_active | boolean | soft-disable without deleting |
| created_at / updated_at | timestamptz | |

**refresh_tokens**
| column | type | notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK -> users.id | |
| token_hash | varchar(255) unique | SHA-256 of the raw JWT, never stored raw |
| revoked | boolean | set true on rotation/logout |
| expires_at | timestamptz | |
| created_at | timestamptz | |

## Auth flow

1. `POST /api/v1/auth/register` — creates a user, defaults to `viewer` role.
2. `POST /api/v1/auth/login` — verifies password, issues an access token
   (15 min) + refresh token (7 days). Refresh token is hashed and stored so
   it can be revoked.
3. `POST /api/v1/auth/refresh` — validates the refresh token against the DB
   (not just JWT signature), **rotates** it: old one is revoked, new pair
   issued. Prevents replay of a stolen refresh token.
4. `POST /api/v1/auth/logout` — revokes the refresh token.
5. Protected routes use `Depends(get_current_user)`; role-gated routes use
   `Depends(require_role(UserRole.ADMIN))`.

## Sequence diagram — Login

```
Client            API (auth router)        AuthService           UserRepository        Postgres
  |--- POST /login -->|                         |                       |                  |
  |                    |--- authenticate() ----->|                      |                  |
  |                    |                         |--- get_by_email() -->|--- SELECT ------>|
  |                    |                         |<--------------------|<-----------------|
  |                    |                         | verify_password()    |                  |
  |                    |                         | create access+refresh JWT               |
  |                    |                         |--- store_refresh_token() -->|--- INSERT ->|
  |                    |<---- TokenPair ---------|                      |                  |
  |<--- 200 {tokens} --|                         |                      |                  |
```

## Why this scales to later phases

Every future module (dataset upload, training pipeline, OpenMax, SHAP/LIME,
reports) follows the identical four-layer shape:
`api/v1/endpoints/<module>.py` → `services/<module>_service.py` →
`repositories/<module>_repository.py` → `models/<module>.py`, registered in
`api/v1/router.py`. This is why `main.py` and `router.py` won't need
structural changes for the rest of the project — only new lines added.

---

# Phase 2 — Dataset Upload, Cleaning & Feature Engineering

## Schema additions

**datasets** — one row per uploaded file: raw/cleaned/features/scaler paths,
row/feature counts, `status` (uploaded → profiled → cleaned →
feature_engineered → split_configured).

**dataset_classes** — one row per class label discovered in a dataset:
`sample_count`, `is_benign`, and `split` (`known` | `unknown_holdout`).
This table is the structural enforcement point for open-set recognition —
Phase 3's training pipeline will query `get_known_classes()` and must never
see `unknown_holdout` rows. Benign/normal traffic is guarded (in both the
service and the repository) from ever being marked `unknown_holdout`,
because "unknown attack recall" is meaningless if normal traffic could be
withheld as "unknown."

## Where each piece of the pipeline lives

```
DatasetService (orchestrator: disk + both repos + pure processing)
 ├── upload()                    → raw CSV to disk, metadata row in Postgres
 ├── profile_and_register_classes() → DataProcessingService.profile()
 │                                    → written to MongoDB (dataset_profiles)
 │                                    → class rows written to Postgres
 ├── clean()                     → DataProcessingService.clean() (pure)
 ├── engineer_features()         → DataProcessingService.engineer_features() (pure)
 └── configure_open_set_split()  → assigns known/unknown_holdout per class
```

`DataProcessingService` has no DB or filesystem dependency — verified in
`tests/test_data_processing_service.py`, which ran successfully against
real generated traffic data (see `ml/data/generate_sample_dataset.py`):
cleaning correctly dropped duplicate rows, `inf`/`NaN` rows, and constant
columns; feature engineering correctly one-hot encoded `protocol_type` and
z-scored numeric columns to zero mean; and reusing a fitted scaler on
unseen data produced numerically consistent results — the property Phase 4
depends on when scoring held-out unknown classes.

## API surface added

| Endpoint | Role required | Purpose |
|---|---|---|
| `POST /datasets/upload` | analyst, admin | multipart upload, stores raw file + metadata |
| `GET /datasets` | any authenticated | list all datasets |
| `GET /datasets/{id}` | any authenticated | metadata + per-class breakdown |
| `POST /datasets/{id}/profile` | analyst, admin | discover columns/classes, write Mongo profile |
| `POST /datasets/{id}/clean` | analyst, admin | dedupe, drop inf/NaN, drop constant columns |
| `POST /datasets/{id}/feature-engineer` | analyst, admin | one-hot encode + z-score scale, persist scaler |
| `POST /datasets/{id}/open-set-split` | analyst, admin | assign known / unknown_holdout per class |

## Known limitation

Cleaning and feature engineering currently run synchronously inside the
request. Fine for the sample dataset (5K rows, sub-second); for a full
CIC-IDS2017-scale file (multi-GB) this should move to a background task
(FastAPI `BackgroundTasks` or a Celery worker) with a polling/websocket
status update — planned as a follow-up once Phase 8's live dashboard
needs the same progress-streaming infrastructure anyway.

---

# Phases 3-11 — ML Core, Backend Integration, Frontend, Deployment

## `ml/` package — framework-agnostic by design

```
ml/
├── models/          CNN, BiLSTM, CNN-BiLSTM hybrid, Transformer (PyTorch);
│                    Autoencoder + VAE (PyTorch); Isolation Forest (sklearn)
├── openmax/         OpenMax open-set recalibration (pure numpy/scipy)
├── training/        LabelEncoder + Dataset wrapper, unified train_classifier()
│                    and train_autoencoder() loops
├── evaluation/      Accuracy/Precision/Recall/F1/MCC/ROC-AUC/FPR/
│                    Unknown-Attack-Recall + timing utilities (pure numpy/sklearn)
├── explainability/  SHAP + LIME wrapper behind one common interface
├── reports/         reportlab PDF generation
└── data/            synthetic dataset generator for local testing
```

Every supervised model (`CNNClassifier`, `BiLSTMClassifier`,
`CNNBiLSTMHybrid`, `TransformerClassifier`) exposes an identical
`forward(x, return_embedding=True) -> (logits, embedding)` interface. This
uniformity is what lets `train_classifier()` in `ml/training/trainer.py`
train ANY of them with the same function, and what lets
`OpenMaxRecalibrator` operate on any of them without model-specific code —
OpenMax only needs activation vectors + logits, not architecture internals.

**What was actually executed and verified in this sandbox** (no torch/
tensorflow available, no network to install them):
- `IsolationForestDetector` — ran against synthetic normal/anomaly data;
  anomaly scores correctly separate the two populations, false positive
  rate on true normals was 4%.
- `OpenMaxRecalibrator` — ran against synthetic 3-class embeddings; a
  known-class sample was correctly classified, a far out-of-distribution
  sample was correctly flagged unknown with the unknown class carrying the
  most probability mass.
- `ml/evaluation/metrics.py` — all metric functions (accuracy/F1/MCC/FPR/
  unknown-attack-recall) verified against hand-computed expected values.
- `ml/reports/report_generator.py` — generated a real PDF with reportlab
  and confirmed the file exists and is non-empty.
- 8 formal unit tests in `ml/tests/test_openmax_and_metrics.py` covering
  all of the above, executed successfully.

**What was written but only syntax-checked, not executed** (requires
torch/tensorflow, unavailable in this sandbox): the four supervised model
architectures, the Autoencoder/VAE, `ml/training/trainer.py`, and
`ml/training/dataset.py`. Before relying on these, run them once in an
environment with `pip install -r ml/requirements.txt` — a smoke test
(forward pass on random data of the right shape, confirm output shape
matches `num_classes`) is the minimum bar before trusting the training
loop end to end.

## Backend integration

New tables: `training_runs`, `ml_models` (flattened metric columns for
SQL-sortable model comparison), `notifications`, `audit_logs` (migrations
`0003`, `0004`).

`TrainingService` is the bridge between persistence and `ml/`:
1. `queue_training_run()` validates the dataset is feature-engineered and
   creates a `QUEUED` row — returns immediately.
2. The router hands `execute_training_run()` to a FastAPI
   `BackgroundTask`, so the HTTP response doesn't block on training.
3. `_run_pipeline()` loads the engineered parquet, filters to
   `known`-split classes only, trains via `ml/training/trainer.py`, fits
   OpenMax on training embeddings, evaluates closed-set metrics on a
   validation split AND unknown-attack recall against the `unknown_holdout`
   rows, persists the model weights + OpenMax state to disk, and writes
   the metrics row.
4. Any exception is caught and recorded on the run as `FAILED` with the
   error message — never silently swallowed, never crashes the worker.

New endpoints: `POST /training/runs`, `GET /training/runs/{id}`,
`GET /models/compare/{dataset_id}`, `GET /reports/dataset/{id}/pdf`,
`GET /notifications`, `GET /logs` (admin), `GET/PATCH /users` (admin).

**Known limitation**: training via `BackgroundTasks` runs in-process with
the API server — acceptable for a capstone deployment, but a real
production system should move this to a dedicated worker (Celery/RQ) so a
long training job can't starve API request handling on the same process.

## Frontend (Next.js)

Dark enterprise theme (deep navy base, glassmorphism panels, blue/cyan/
purple accents) defined once in `tailwind.config.ts` + `globals.css`, used
consistently across all 9 pages: login, dashboard (stat cards + area
chart + dataset table), datasets (upload + pipeline stage triggers +
open-set split toggle table), training (run trigger form), models (bar
chart + full metrics table), reports (PDF download), users (admin role/
status management), logs (admin audit trail), settings (profile +
notification preferences).

`lib/api.ts` centralizes the JWT-aware fetch wrapper with one-shot
automatic refresh-and-retry on a 401 — every page calls through this, no
page manages tokens directly.

**Known limitation**: written but **not built** in this sandbox — no
network access for `npm install`. Before relying on this, run
`npm install && npm run build` in an environment with network access and
fix whatever TypeScript errors surface; nothing here has been through a
compiler yet, only manual review and JSON/JS syntax checks.

## Deployment

- `docker-compose.yml` — full stack: Postgres, MongoDB, Redis, backend,
  frontend, with healthchecks and named volumes for data + model artifacts.
- `k8s/` — namespace/configmap, a secrets template (placeholder values,
  intentionally not meant to be committed with real values), StatefulSets
  for Postgres/MongoDB with PVCs, a Redis Deployment, a backend Deployment
  with an HPA (2-6 replicas, scales on CPU), a frontend Deployment, and an
  Ingress routing `/api` to the backend and everything else to the frontend.
- `.github/workflows/backend-ci.yml` / `frontend-ci.yml` — lint + test +
  Docker build on every push to the respective directory.
- `.github/workflows/deploy.yml` — on push to `main`: builds and pushes
  both images to GHCR, then applies the k8s manifests and rolls out the
  new image tags.

**Known limitation**: none of the Docker builds, k8s manifests, or CI
workflows have been executed against a real cluster or registry in this
sandbox (no Docker daemon, no cluster, no network). They're written to
the current best-practice shape for each tool, but validate with
`docker compose config`, `kubectl apply --dry-run=client -f k8s/`, and a
real CI run before trusting them in production.

---

# Post-review hardening pass

A review of the first complete draft surfaced a real bug and several
gaps against the original 25 objectives. This pass fixes them:

**Bug fix — architecture dispatch.** `TrainingService` originally called
`train_classifier()` unconditionally for every architecture, including
`autoencoder`, `vae`, and `isolation_forest` — selecting any of those
would have crashed, since they aren't supervised classifiers and don't
produce logits/embeddings for OpenMax. Fixed by branching into three
pipelines: `_run_supervised_pipeline` (OpenMax-based, for CNN/BiLSTM/
CNN-BiLSTM/Transformer), `_run_anomaly_pipeline` (reconstruction-error
threshold at the 99th percentile of known-traffic error, for Autoencoder/
VAE), and `_run_isolation_forest_pipeline` (sklearn's own anomaly score).
All three compute the same `unknown_attack_recall` metric so they remain
comparable on the model comparison dashboard despite using different
open-set mechanisms internally.

**Security — rate limiting.** `/auth/login` (10 req/min) and
`/auth/register` (5 req/5min) now go through a Redis-backed fixed-window
limiter (`app/core/rate_limit.py`), keyed by client IP. Verified the
window/reset/per-IP-isolation logic against a fake in-memory Redis stand-in
— correctly allows up to the limit, blocks the next request, and tracks
different IPs independently.

**Security — upload hardening.** Dataset upload previously trusted the
client-supplied filename directly (a path-traversal risk) and only
sample-checked 5 rows before accepting the file. Now: extension allowlist
(`.csv` only), `os.path.basename()` strips any directory components from
the filename before it touches a path, minimum-row and maximum-column
sanity limits, and a check that the label column has at least 2 classes
before the file is persisted. Verified against crafted inputs including a
`../../etc/passwd.csv`-style filename.

**Feature gap — Explainability had no API.** `ml/explainability/
explainer.py` existed but nothing could reach it over HTTP, and there was
no reference/background data for SHAP or LIME to perturb around. Fixed
properly (not stubbed): supervised training now persists a 100-row
background sample plus feature/class names alongside the model artifact
(`ml_models.background_data_path/feature_names/class_names`, migration
`0005`). `POST /explainability/explain` loads the trained model and this
background sample and returns real per-feature contributions. The
frontend `/explainability` page renders them as a horizontal bar chart.

**Feature gap — Live Packet Simulation didn't exist.** Objective #11 had
no implementation at all in the first draft. Added `WS /simulation/ws/
{model_id}`: streams one synthetic flow record per second through the
actual trained model + OpenMax, correctly flagging ~10% out-of-distribution
bursts as unknown. The frontend `/simulation` page connects, shows a live
feed, and disconnects cleanly. Synthetic rather than a real packet capture
by design — raw traffic capture raises consent/legality scope questions
well beyond a capstone platform's needs, and the detection logic exercised
is the real trained model either way.

**Rigor gap — no hyperparameter tuning, no statistical repeatability.**
Objective #7 (hyperparameter tuning) had no implementation. Added
`HyperparameterTuningService` with `grid_search()` (small LR × batch-size
grid, ranked by a chosen metric) and `multi_seed_ablation()` (same
architecture/hyperparameters across N seeds, reporting mean ± std per
metric) — both exposed via `POST /training/grid-search` and `POST
/training/ablation`. This is what turns "CNN-BiLSTM got 0.72 unknown
recall" into a defensible claim instead of one noisy sample.

**Observability gap — dashboard chart was hardcoded fake data.** The
original dashboard's activity chart was literally a hardcoded array, not
wired to anything real — flagged at the time but left unfixed. Fixed with
`AuditLogMiddleware` (records every successful state-changing request
automatically, so no endpoint has to remember to log itself) plus `GET
/activity-summary` (hourly bucket counts from real audit_logs). The
dashboard now shows genuine platform activity or an honest empty state,
never a mock.

**What's still unverified** (same root cause as before — no network
access to install torch/tensorflow/npm in this sandbox): the anomaly and
isolation-forest training branches, the explainability endpoint's SHAP/
LIME calls, the simulation WebSocket, and the two new frontend pages are
written and syntax-checked but not executed end-to-end. What COULD run
without those dependencies — the rate limiter algorithm, upload validation
against crafted filenames, and all previously-passing OpenMax/metrics/
Isolation Forest tests — was re-verified after this pass and still passes.
