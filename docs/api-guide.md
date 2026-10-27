# API guide

Base path `/api/v1`. Authoritative request/response documentation: `http://127.0.0.1:8000/docs`. All private endpoints resolve a session cookie. Mutation calls additionally require `X-Requested-With: SkillWeave`. Same-origin requests carry cookies automatically. Passwords, session token hashes and password hashes are never serialized through user endpoints.

| Method / resource | Workflow |
|---|---|
| POST auth/register, auth/login, auth/logout | Account/session lifecycle |
| POST auth/reset-request, auth/reset | Development terminal token delivery and single-use password reset |
| GET/PUT me | Own identity, skills, goals, preferences and availability |
| GET/POST skills | Shared catalog; creation is admin only |
| GET volunteers | Scoped directory; leaders see their assigned teams |
| POST organization/invitations, organization/join | Coordinator-issued email-bound codes, registration or unused personal-workspace joining |
| GET/PUT organization | Own organization details; updates coordinator/admin only |
| GET/POST projects; GET/PUT/DELETE projects/{id} | Project CRUD; DELETE cancels and notifies |
| GET/POST tasks; PUT/DELETE tasks/{id} | Task and requirement/dependency CRUD; assigned task constraints require resolution before editing |
| POST tasks/{id}/progress | Authorized progress; checks prerequisites |
| GET/POST applications | Volunteer participation request |
| POST optimization; GET optimization; GET optimization/{id} | Start and inspect snapshot runs |
| POST optimization/{id}/publish | Review approval, scenario application and invitations |
| GET assignments; POST assignments/{id}/respond, /lock | Scoped roster, own invitation response, coordinator locks |
| POST replacements | Persist replacement reason and notify coordinators |
| GET notifications; POST notifications/read | Own notification history |
| GET/POST hours; POST hours/{id}/approve | Submitted hours and independent approval |
| GET/POST attendance | Scoped attendance, leader/coordinator recording |
| GET/POST feedback; GET achievements | Private reflections and own verified badges |
| GET analytics; GET reports/{kind}.csv | Authorized activity and formula-safe exports |
| POST import/tasks | Multipart UTF-8 CSV, atomic row validation |
| GET audit; GET admin/users; PUT admin/users/{id} | Audited access administration |
| GET admin/organizations; GET health | Organization inventory and database health |

Errors use FastAPI `detail`: 401 session/credentials, 403 role/scope/CSRF, 404 unavailable record, 409 conflict/stale plan, 422 validation, 429 auth rate limiting. Public auth endpoints are rate limited per IP in process. Some list endpoints support offset/limit; UI pagination remains incomplete.

Optimization example:

```json
{"seed":42,"population":30,"generations":40,"mutation":0.25,"scenario":{"kind":"withdrawal","user_id":5}}
```

The 202 response includes a run ID. Poll until completed/failed. Scenario kinds: withdrawal, unavailable, capacity, deadline, mandatory, cancel, urgent. Urgent requires a complete TaskIn under `urgent` and is API-only. `publish` changes live records and must follow human review. No optimization call automatically publishes.
