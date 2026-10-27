# SkillWeave

Intelligent Volunteer Team Formation and Coordination Platform. A local, database-backed final-year project with React/TypeScript, FastAPI, SQLAlchemy, explicit Mamdani fuzzy inference, and a seeded genetic algorithm.

## Problem and objectives

Manual volunteer allocation can leave responsibilities unfilled, create scheduling conflicts, and concentrate work on a few people. SkillWeave makes eligibility, team skill coverage, workload, preferences, and algorithm tradeoffs inspectable. Recommendations require human publication and volunteer acceptance. Research validity and community impact must be evaluated separately; this project does not claim measured real-world improvements.

## Run locally (PowerShell, from this directory)

Python 3.12+ and Node 22.12+ are recommended. No paid services are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
python -m backend.seed
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open [SkillWeave](http://127.0.0.1:5173). API and interactive schemas: [Swagger UI](http://127.0.0.1:8000/docs). Health: `/api/v1/health`. Vite proxies `/api` to port 8000; keep the browser on the same hostname for cookies.

## Fictional development demo

The seed command is explicit and non-destructive; repeated execution preserves existing data. All accounts below use **`WeaveDemo!2026`**, or `DEMO_PASSWORD` set before seeding.

| Role | Email |
|---|---|
| Super Admin |   |
| Coordinator | coordinator@demo.skillweave.test |
| Team Leader | leader@demo.skillweave.test |
| Second Team Leader | leader2@demo.skillweave.test |
| Volunteer | volunteer@demo.skillweave.test |
| Seven additional volunteers | volunteer2@demo.skillweave.test through volunteer8@demo.skillweave.test |

Eight volunteers, two leaders, nine projects, nineteen tasks, and eight skills are seeded. The expanded fictional history adds four completed projects, one ongoing project, 44 assignment records, 102 approved hours, one pending 2-hour record, attendance, private feedback, achievements, and a replacement request. Every volunteer has four completed past projects; their profile and directory details show project contribution history. Running the seed again backfills this versioned history into existing demo databases without resetting edited projects or duplicating records. Overlapping tasks compete for hours. Accessible information requires a skill absent from the pool, leaving a truthful infeasible task. Dates are November 2–8, 2026. Public registration creates a volunteer and a separate personal organization, or consumes a coordinator-created, email-bound, single-use invitation. Only the invitation record controls membership and invited volunteer/leader role.

Never seed these accounts in production. To obtain a clean **separate** demo database without deleting data:

```powershell
$env:DATABASE_URL = 'sqlite:///./skillweave-demo-fresh.db'
python -m alembic upgrade head
python -m backend.seed
```

Choose a new filename each reset. There is deliberately no unattended command that deletes your current database.

## Implemented workflows

- Session-cookie login, signup, logout/invalidation, local password reset, Argon2 hashes, role checks, tenant checks, account deactivation, and audit history.
- Shared and role-specific navigation for admin, coordinator, assigned team leader, and volunteer.
- Organization details, projects, tasks, required/verified skills, priorities, capacity, dates, dependencies, cancel operations, search, and status filters.
- Profile skill proficiency, verification preservation rules, learning goals, interests, weekly hours, and concrete availability windows.
- Fuzzy suitability, seeded GA with tournament selection/crossover/mutation/elitism/repair, greedy/random baselines, explanations, gaps, utilization, and stored input/config/result snapshots.
- Snapshot-based withdrawal, availability, capacity, deadline, mandatory-skill, and cancellation scenarios. An urgent-task scenario is available through the API. Preview does not change assignments. Publication rejects stale snapshots and protects accepted/confirmed/locked allocations.
- Assignment publication, in-app invitations, acceptance/decline/withdrawal, locks, replacement requests, progress, prerequisite checks, attendance, submitted/approved hours, private feedback, and first verified contribution badge.
- Database-derived analytics, authorized formula-safe CSV exports, atomic validated task CSV import with row errors, notifications, global skill creation, user role/status administration, organization listing, and health checks.
- Responsive landing/auth/dashboard views, application-wide theme settings, lazy 3D visuals, 2D fallback, reduced motion, accessible chart tables, keyboard forms and modal focus trapping.

## Architecture and repository

```text
backend/
  database.py          engine/session configuration
  models.py            relational tables and constraints
  schemas.py           request validation
  main.py              versioned API, authorization, workflow services
  optimizer.py         fuzzy inference, GA, repair, evaluation and baselines
  seed.py              repeatable fictional demo
  migrations/          Alembic initial schema
  tests/               authentication, permissions, workflow and optimizer tests
frontend/
  src/api.ts           typed API contract and cookie-aware requests
  src/App.tsx          routing, landing/auth and role-aware layout
  src/pages.tsx        workspace CRUD, profile and dashboards
  src/workflows.tsx    optimization, assignments, hours, reports and admin
  src/Network.tsx      lazy React Three Fiber scene
  src/theme.tsx        centralized theme preference
  src/styles.css       tokens, responsive components and reduced motion
docs/                  architecture, API, methodology and submission material
```

SQLite is the default. Set `DATABASE_URL=postgresql+psycopg2://...` for PostgreSQL and run Alembic. Migration revision 0001 creates the current schema from SQLAlchemy metadata; future schema changes should use explicit new revisions rather than editing 0001. Database dates are naive wall-clock datetimes; the UI and demo use local India-time schedules. Audit timestamps are UTC. Multi-timezone scheduling is not implemented.

## Tests and evaluation

```powershell
python -m pytest backend/tests -q
npm --prefix frontend test
npm --prefix frontend run build
python -m backend.evaluate --seeds 5 --output docs/evaluation-results.json
cd frontend
npx playwright test
```

Backend tests use a temporary database and never the live demo database. E2E tests require running backend/frontend and an installed Playwright Chromium browser (`npx playwright install chromium`). See `docs/testing-and-evaluation.md` for the recorded verification status. Evaluation writes actual repeated-seed measurements; do not describe fictional sample records as empirical NGO outcomes.

## 3D, themes, accessibility, and performance

`ThemeProvider` stores only appearance in localStorage; auth credentials are never persisted there. A small head script applies preference before React mounts. System preference follows OS changes. CSS variables control every application surface, form, status and chart. 3D colors use the same mint/blue palette with lit geometry readable in both themes.

`Network.tsx` is dynamically imported. Up to 24 procedural nodes, a DPR cap of 1.5, shared simple materials/geometries, and React Three Fiber disposal keep the graph bounded. Orbit controls never capture scroll zoom. A WebGL capability check, rendering error boundary, and manual 2D switch provide SVG alternatives. Reduced motion disables decorative scene movement and chart animations. Each graph has a text node list. The landing preview is explicitly illustrative; authenticated scenes derive their nodes from API data and recorded allocations. There is no invented live algorithm progress: the UI shows computing status and then recorded generation history. The graph is a central-purpose network, not a geographically meaningful globe or a detailed skill-edge map.

## Deployment

`docker compose up --build` starts PostgreSQL, the API, and nginx serving the built frontend. The API entrypoint migrates but **does not seed**. To deliberately add development data: `docker compose exec api python -m backend.seed`. Use HTTPS, set `ENVIRONMENT=production` for Secure cookies, set exact CORS origins, use strong database credentials through environment variables, and configure your reverse proxy. Local compose defaults are development-only. Nginx routes `/api/` to FastAPI and supports SPA deep links.

## Current limitations and remaining master-prompt scope

This is a functional prototype, not the complete production release specified in the master prompt. The following are intentionally documented as remaining work:

- Registration approval queues, multi-membership selection, transfers out of active organizations, admin organization creation/deactivation, and account creation by administrators. Invitations support new registrations and unused personal accounts, with manual code delivery only.
- Dedicated Event, Team/TeamMembership, assignment-invitation, lock, preference, and learning-goal tables are consolidated into projects, assignments, and profile JSON. There are no separate event calendars, team communications, uploads/evidence, issue explorer, or configurable badge rules.
- No manual allocation editor, baseline publication UI, supervised stretch-role modeling, historical retention analytics, deadline reminder scheduler, or geographical impact data.
- Resource-loss scenarios need a resource model; urgent tasks are API-only. Scenario comparisons report assignment pair changes and new metrics but do not yet display a full side-by-side old/new allocation diff.
- No volunteer CSV import; task CSV import does not import skills/dependencies. Several lists have API pagination but the UI only displays the first page (projects 50, volunteers 50, runs 25, audit 200, notifications 100).
- The optimizer is a synchronous CPU calculation inside a FastAPI background task, not a durable distributed worker. Status polling reports queued/running/completed, not per-generation streaming. Process restarts can strand running records. Large inputs need bounded queues, cancellation and durable jobs. Publication has snapshot validation but needs serializable transaction/advisory locking for concurrent production writers.
- Fuzzy inputs, fairness, and fitness are research design choices. No empirical validation is claimed. Mandatory qualifications are hard per-candidate gates, and skill coverage/minimum staffing are soft objectives so infeasible cases return gaps. Learning score rewards declared goals only where minimum proficiency already exists.
- Password-reset delivery is local backend-terminal output in development; in production no delivery is configured, so an email provider must be implemented before offering reset to users. No MFA, OAuth, distributed rate limiter, or self-service account erasure.
- User dates lack timezone storage; preferences/learning goals are JSON arrays; feedback marked non-private is currently still visible only to its author and coordinators. Public feedback sharing and notification delivery preference enforcement remain to be implemented.
- 3D scenes cap displayed nodes and do not draw a full skill constellation, task dependency graph, or impact globe. There are accessible tables/lists for the underlying workflow data.

## Troubleshooting

Use `127.0.0.1` consistently. A 401 means the session expired or the API is not reachable. A 403 means the role, tenant, assigned-project scope, or request protection header is invalid. A stale-run 409 requires a fresh optimization. A locked scenario conflict requires resolving the underlying accepted assignment/lock first, never ignoring qualification constraints. npm download failures require access to the npm registry. A missing schema requires `python -m alembic upgrade head`. If PostgreSQL is unavailable, leave `DATABASE_URL` at SQLite. Optional email and file storage are not required for the implemented local workflows.
