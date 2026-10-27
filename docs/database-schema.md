# Database schema

`backend/models.py` is the authoritative schema. Primary keys are integers except hashed session/reset tokens. References are foreign keys; SQLite explicitly enables foreign-key enforcement.

| Group | Tables and relations |
|---|---|
| Identity | organizations → users; organization_memberships (one current membership per user), sessions, password_reset_tokens; email-bound, hashed, single-use organization_invitations |
| Skills | skills; volunteer_skills links user/skill with level 1–5 and explicit verification; volunteer_availability with positive windows |
| Planning | projects belong to organization and optional leader; tasks belong to project; task_required_skills; task_dependencies |
| Participation | applications links project/user; assignments links task/user with status, lock and stored explanation |
| Execution | task_progress, attendance (one current entry per assignment), volunteer_hour_records (one record per assignment), replacement_requests |
| Reflection | feedback, achievements, notifications |
| Research | optimization_runs contains immutable input/config/scenario snapshots plus results and status |
| Accountability | audit_logs records actor, tenant, action, detail and UTC timestamp |

Unique constraints prevent duplicate skill entries, application pairs, assignment pairs, prerequisite pairs and achievement awards. Capacity, dates, proficiency, priority, progress, ratings and hours have database/request validation. Cancellation retains history instead of cascading destructive deletion.

Consolidations relative to the master prompt: projects also hold event details; teams are represented by task assignments; invitations and locks are assignment state; interests, preferences and learning goals are JSON profile fields; optimization config/result are JSON snapshots. Dedicated normalized tables for these concepts remain future work. Uploaded evidence is not implemented. See the README for consequences and remaining functionality.

Run `python -m alembic upgrade head` against either supported database. Initial migration uses metadata; do not edit it after deployment. Add explicit new migrations for later changes.

Revision 0002 adds organization invitations for existing installations. Invitation roles are limited to volunteer/leader; tokens expire after seven days and are returned only to an authorized creator.
