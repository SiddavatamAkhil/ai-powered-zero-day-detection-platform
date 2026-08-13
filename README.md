# AI-Powered Zero-Day Attack Detection Platform

Enterprise deep learning system for classification of known and unknown
(zero-day) network attacks using Open Set Recognition and Explainable AI.

> **Status**: All 11 phases implemented, plus a post-review hardening pass
> that fixed a real dispatch bug (autoencoder/isolation-forest training
> would have crashed), added rate limiting + upload validation, and closed
> two objectives that had no implementation at all (Explainability API,
> Live Packet Simulation) — see "Post-review hardening pass" at the end of
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full list and
> exactly what's been re-verified vs. still needs a first real run.

## Tech stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, Framer Motion, Recharts *(Phase 7)*
- **Backend**: FastAPI, Python 3.11, JWT auth, Repository + Service layered architecture
- **AI**: PyTorch, TensorFlow, CNN / BiLSTM / CNN-BiLSTM / Transformer / Autoencoder / Isolation Forest / OpenMax, SHAP, LIME *(Phase 3+)*
- **Data**: PostgreSQL (relational), MongoDB (semi-structured), Redis (cache/pub-sub)
- **Deployment**: Docker, Docker Compose, Kubernetes-ready, GitHub Actions CI

## Project structure

```
zeroday-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # auth, datasets, training, reports, system, users
│   │   ├── core/               # Config, security (JWT, hashing)
│   │   ├── db/                 # Postgres session, Mongo/Redis clients
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── repositories/       # Data-access abstraction (repository pattern)
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic (incl. TrainingService)
│   │   └── main.py
│   ├── alembic/versions/       # 0001 auth, 0002 datasets, 0003 ml_models, 0004 notifications
│   ├── tests/                   # Unit tests (in-memory fake repos + real pandas data)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # Next.js 14, TypeScript, Tailwind, dark enterprise theme
│   ├── app/                       # login, dashboard, datasets, training, models, reports, users, logs, settings
│   ├── components/                # Sidebar, Card/StatCard
│   ├── lib/api.ts                 # JWT-aware fetch client
│   └── Dockerfile
├── ml/                            # Framework-agnostic ML core
│   ├── models/                     # CNN, BiLSTM, CNN-BiLSTM, Transformer, Autoencoder, VAE, Isolation Forest
│   ├── openmax/                    # Open-set recognition (pure numpy/scipy)
│   ├── training/                   # Dataset wrapper + unified training loops
│   ├── evaluation/                 # Full metric suite
│   ├── explainability/             # SHAP + LIME wrapper
│   ├── reports/                    # PDF report generation
│   ├── tests/                      # Runnable without torch (OpenMax, metrics, Isolation Forest)
│   └── data/generate_sample_dataset.py
├── k8s/                            # Namespace, secrets template, stateful services, backend/frontend + Ingress
├── docker-compose.yml
├── docs/ARCHITECTURE.md
└── .github/workflows/               # backend-ci, frontend-ci, deploy
```

## Getting started (Phase 1 — backend + auth only)

```bash
cd zeroday-platform
cp backend/.env.example backend/.env   # edit SECRET_KEY before any real deployment

docker compose up --build postgres mongo redis backend

# Run migrations
docker compose exec backend alembic upgrade head
```

API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

Tests use an in-memory fake repository (`tests/test_auth_service.py`) so
they run without a live Postgres instance — see `docs/ARCHITECTURE.md` for
why the repository pattern makes this possible.

## Example: register + login

```bash
curl -X POST localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","full_name":"Admin","password":"changeme123"}'

curl -X POST localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme123"}'
```

## Example: dataset pipeline (Phase 2)

```bash
# Generate a synthetic sample dataset to test with (no need to wait on a real download)
python ml/data/generate_sample_dataset.py --rows 5000 --out sample.csv

TOKEN=<access_token from login>

curl -X POST localhost:8000/api/v1/datasets/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Sample IDS Dataset" \
  -F "label_column=label" \
  -F "file=@sample.csv"

# Discover columns/classes, clean, engineer features
curl -X POST localhost:8000/api/v1/datasets/{id}/profile -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/api/v1/datasets/{id}/clean -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/api/v1/datasets/{id}/feature-engineer -H "Authorization: Bearer $TOKEN"

# Mark rare classes as unknown (simulating zero-day attacks the model never trains on)
curl -X POST localhost:8000/api/v1/datasets/{id}/open-set-split \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"assignments":[{"class_name":"u2r","split":"unknown_holdout"},{"class_name":"worm","split":"unknown_holdout"}]}'
```

## Running the full stack

```bash
cp backend/.env.example backend/.env   # set a real SECRET_KEY first
docker compose up --build
docker compose exec backend alembic upgrade head
```

Backend: http://localhost:8000/docs · Frontend: http://localhost:3000

## Training a model end to end

```bash
# 1. Upload + process a dataset (see Phase 2 example above)
# 2. Configure the open-set split (hold out u2r, worm as "zero-day" classes)
# 3. Trigger training
curl -X POST localhost:8000/api/v1/training/runs \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"dataset_id":"<id>","architecture":"cnn_bilstm","epochs":20}'

# 4. Poll status
curl localhost:8000/api/v1/training/runs/<run_id> -H "Authorization: Bearer $TOKEN"

# 5. Compare models once a few architectures have completed
curl localhost:8000/api/v1/models/compare/<dataset_id> -H "Authorization: Bearer $TOKEN"

# 6. Download the PDF report
curl localhost:8000/api/v1/reports/dataset/<dataset_id>/pdf -H "Authorization: Bearer $TOKEN" -o report.pdf

# 7. Small hyperparameter grid search (blocks until all combos finish)
curl -X POST localhost:8000/api/v1/training/grid-search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"dataset_id":"<id>","architecture":"cnn","learning_rates":[0.001,0.0001],"batch_sizes":[64,128],"epochs":10}'

# 8. Multi-seed ablation for a statistically defensible result
curl -X POST localhost:8000/api/v1/training/ablation \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"dataset_id":"<id>","architecture":"cnn_bilstm","seeds":[1,2,3,4,5],"epochs":20}'

# 9. Explain a single prediction (model must have been trained after the explainability update)
curl -X POST localhost:8000/api/v1/explainability/explain \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model_id":"<model_id>","sample":[0.1,-0.4,1.2, ...],"method":"shap"}'

# 10. Live simulation feed (WebSocket, browser or wscat)
wscat -c "ws://localhost:8000/api/v1/simulation/ws/<model_id>?token=$TOKEN"
```

## Before you deploy this for real

1. `cd ml && pip install -r requirements.txt` and smoke-test each model
   architecture with a forward pass on random data — the PyTorch models
   were written and syntax-checked but never executed (no torch available
   while building this).
2. `cd frontend && npm install && npm run build` — fix whatever TypeScript
   errors surface; the frontend was never compiled while building this.
3. `docker compose config` to validate the compose file, then a real
   `docker compose up --build` end to end.
4. `kubectl apply --dry-run=client -f k8s/` before applying to a real
   cluster; replace the placeholder domain in `k8s/04-frontend.yaml` and
   generate real secrets instead of using `k8s/01-secrets.yaml` as-is.
5. Swap the synchronous `BackgroundTasks` training execution for a real
   worker queue (Celery/RQ) once training jobs get large enough to risk
   starving the API process.
