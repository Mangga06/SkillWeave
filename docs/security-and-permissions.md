# Security and permissions

Passwords use Argon2 through argon2-cffi. Sessions are random 40-byte URL-safe tokens with only SHA-256 hashes in the database and 12-hour expiry. Cookies are HttpOnly and SameSite=Lax; production enables Secure. Logout removes the session row. Deactivation removes all user sessions. Password reset tokens expire in 15 minutes and are single use; reset invalidates every session. Development delivery logs the reset token locally; production delivery is not configured.

| Role | Scope |
|---|---|
| Admin | User role/status and global skill catalog; organization inventory; privileged project lookup; other workspace list APIs remain in own organization |
| Coordinator | Own organization/project/task planning, optimization/publication, directory, hours approval, reports and audit |
| Team leader | Only projects assigned as leader and their associated team records; attendance/progress/replacement operations |
| Volunteer | Own profile, own assignment responses/hours/notifications/badges, same-organization opportunities and participation feedback |

Mutation requests carry a custom same-origin header; CORS uses exact configured origins. The browser cannot select its role/org at registration. Record helpers traverse task → project → tenant and enforce assigned-leader scope. User endpoints omit password/session hashes. Private feedback is author/coordinator/admin scoped. No volunteer can approve their own hours. Administrators cannot remove their own admin access or deactivate the last active admin.

Public auth routes have an in-process per-IP rolling limit of 20 attempts/minute. Use a distributed limiter and trusted reverse-proxy configuration for deployment. Exports escape leading spreadsheet formula characters. Task imports are UTF-8, size/row bounded and all-or-nothing. Upload/evidence handling is absent.

Remaining production work: tenant invite lifecycle, MFA, recovery/email provider, policy-controlled account erasure, retention rules, centralized audit retention, durable jobs, serializable publish locking, secure headers/CSP review, penetration testing, and distributed rate limiting. Docker configuration is for development unless credentials, HTTPS and production cookie settings are supplied.

Organization invitations use 40-byte random codes, SHA-256 hashes, seven-day expiry, one-time use, exact email binding and server-selected volunteer/leader role. Coordinators cannot invite administrators or other coordinators. Moving an existing account requires an unused single-member personal workspace with no projects, applications or assignments. Manual code sharing substitutes for unconfigured email delivery.
