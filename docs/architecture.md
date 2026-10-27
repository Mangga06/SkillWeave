# Architecture

The browser runs a React/TypeScript SPA. React Router controls screens, TanStack Query controls server-state caching and invalidation, and an HttpOnly cookie identifies a database-backed session. Vite forwards same-origin API calls during development; nginx performs the same function in Docker.

FastAPI validates Pydantic schemas, resolves the authenticated user from the session hash, checks role and tenant/assigned-project scope, then performs SQLAlchemy operations. The PostgreSQL-compatible schema defaults to SQLite for offline local use. Alembic creates the initial schema. Explicit seeding never overwrites existing accounts.

Coordinator optimization captures task/volunteer/assignment snapshots plus all algorithm parameters. A background task performs CPU work and persists a completed result or failure. Polling retrieves status. Generation traces are actual recorded values and only appear after calculation. This job abstraction is local-process only; production requires a durable queue.

Publication validates that the live snapshot still matches its input. Hypothetical changes are separate until publication. Invitations and notifications are persisted together. Accepted/confirmed/in-progress/completed and explicitly locked assignments cannot be silently replaced. Production concurrency requires stronger serializable locking around snapshot validation/publication.

Themes use shared CSS variables and one preference provider. The HTML head applies persisted appearance before React. 3D uses a lazy React Three Fiber component, bounded procedural nodes, DPR 1–1.5, reduced-motion detection and automatic disposal. WebGL failure or user selection falls back to SVG; lists/tables preserve access to important data.

Deployment: browser → nginx → FastAPI → PostgreSQL. Development: browser → Vite proxy → FastAPI → SQLite. No external AI, maps, email or paid APIs are required.
