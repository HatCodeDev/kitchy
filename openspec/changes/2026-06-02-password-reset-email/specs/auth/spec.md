# Delta Spec: Password Reset via Email

**Change**: password-reset-email  
**Domain**: auth  
**Type**: Delta Spec  
**Status**: APPROVED  
**Created**: 2026-06-02

---

## Context

Kitchy's auth layer (`app/routers/auth.py`) currently provides `/register` and `/login` only.
There is no self-service password recovery path. This spec defines the behavioral contract for
two new endpoints that complete the auth domain: `POST /forgot-password` and
`POST /reset-password`.

---

## New Requirements

### REQ-1: Forgot Password — Uniform Response (Anti-Enumeration)

`POST /forgot-password` MUST return an identical HTTP 200 response body and status regardless
of whether:
- the submitted email does not exist in the database, or
- the submitted email belongs to a user with `is_active = False`, or
- the submitted email belongs to an active, valid user.

The response body MUST be:

```json
{ "message": "If that email is registered, you will receive a reset link shortly." }
```

No field in the response MAY reveal whether the email is known to the system.

**Scenario 1.1 — Email not found**

Given the system receives `POST /forgot-password` with a well-formed email  
When no user record with that email exists in the database  
Then the system MUST return HTTP 200 with the uniform response body  
And the system MUST NOT send any email  
And the system MUST log the attempt internally for abuse detection (see REQ-7)

**Scenario 1.2 — Account is inactive**

Given the system receives `POST /forgot-password` with a well-formed email  
When a user record exists for that email but `is_active = False`  
Then the system MUST return HTTP 200 with the uniform response body  
And the system MUST NOT send any email  
And the system MUST log the attempt internally (see REQ-7)

**Scenario 1.3 — Active account**

Given the system receives `POST /forgot-password` with a well-formed email  
When a user record exists for that email and `is_active = True`  
Then the system MUST return HTTP 200 with the uniform response body  
And the system MUST generate a reset token and send the reset email (see REQ-2, REQ-3, REQ-5)

---

### REQ-2: Reset Token Generation and Storage

When a valid reset token is created, the system MUST adhere to these rules:

1. The plain token MUST be generated using `secrets.token_urlsafe(32)`.
2. Only the SHA-256 hash of the plain token (`token_hash`) MUST be persisted in the database.
   The plain token MUST NOT be written to the database, logs, or any durable store.
3. The token record MUST store `expires_at = now() + 30 minutes` (UTC).
4. The token record MUST store `used = False` at creation time.
5. The token record MUST be associated to the user via `user_id`.

**Scenario 2.1 — Token generation**

Given a valid, active user has requested a password reset  
When the system creates the token  
Then `token_hash` in `password_reset_tokens` MUST equal `SHA-256(plain_token)`  
And the plain token MUST NOT appear in `password_reset_tokens` or in any log line  
And `expires_at` MUST be exactly 30 minutes after the creation timestamp (UTC)  
And `used` MUST be `False`

---

### REQ-3: Previous Token Invalidation

When a new reset token is generated for a user, the system MUST invalidate all existing
pending tokens for that user before inserting the new one.

"Invalidate" means: for all `password_reset_tokens` rows where `user_id = <target>` and
`used = False` and `expires_at > now()`, set `used = True`.

**Scenario 3.1 — Prior pending token invalidated**

Given user U has a pending (unused, non-expired) reset token T1  
When user U requests a new password reset  
Then token T1 MUST be marked `used = True` before T2 is persisted  
And only T2 MUST be accepted for a subsequent reset attempt

---

### REQ-4: Reset Link URL Contract

The reset email MUST contain a link with the following structure:

```
https://kitchy.vonlunant.site/reset-password?token=<plain_token>
```

- The host MUST be `kitchy.vonlunant.site`.
- The path MUST be `/reset-password`.
- The token MUST be passed as the `token` query parameter.
- The plain token value MUST be URL-safe (guaranteed by `secrets.token_urlsafe`).

The Flutter screen that consumes this link is out of scope for this change.

**Scenario 4.1 — Link format**

Given the system is sending a reset email to an active user  
When the email is constructed  
Then the body MUST contain exactly one link matching the pattern  
`https://kitchy.vonlunant.site/reset-password?token=<token>`  
And `<token>` MUST be the plain (unhashed) token value

---

### REQ-5: Email Dispatch via EmailSender Interface

The system MUST send one reset email per valid request via the `EmailSender` interface. The
spec constrains the observable behavior, not the concrete SMTP provider.

Rules:
- Exactly one email MUST be sent per successful forgot-password request for an active user.
- The email MUST be addressed to the user's registered email address.
- The email MUST contain the reset link (see REQ-4).
- The `EmailSender` implementation MUST be injectable / replaceable via environment variables
  without code changes (provider-agnostic contract).

**Scenario 5.1 — Email sent once for valid user**

Given user U is active and requests a password reset  
When the forgot-password flow completes  
Then exactly one email MUST be dispatched to U's registered address  
And the email MUST contain the reset link

**Scenario 5.2 — No email for unknown/inactive user**

Given the submitted email does not belong to an active user  
When the forgot-password flow completes  
Then zero emails MUST be dispatched

---

### REQ-6: Reset Password — Token Validation

`POST /reset-password` accepts `{ "token": "<plain_token>", "new_password": "<password>" }`.

The system MUST validate the token before accepting the password change. Validation steps,
in order:

1. Compute `SHA-256(submitted_token)` and look up `token_hash` in `password_reset_tokens`.
2. If no matching row is found → reject with HTTP 400.
3. If `used = True` → reject with HTTP 400 (single-use enforcement).
4. If `expires_at <= now()` (UTC) → reject with HTTP 400 (expiry enforcement).
5. If all checks pass → accept the reset.

All rejection responses MUST return HTTP 400 with a generic error body. The response MUST NOT
reveal which specific check failed (prevents oracle attacks).

```json
{ "detail": "Invalid or expired reset token." }
```

**Scenario 6.1 — Token not found**

Given a client submits `POST /reset-password` with a token that has no matching `token_hash`  
When the system looks up the token  
Then the system MUST return HTTP 400 with the generic error body

**Scenario 6.2 — Token already used**

Given a valid token T was previously used to complete a reset  
When a client submits `POST /reset-password` with T again  
Then the system MUST return HTTP 400 with the generic error body  
And `hashed_password` MUST NOT be updated

**Scenario 6.3 — Token expired**

Given a token T was created more than 30 minutes ago and was never used  
When a client submits `POST /reset-password` with T  
Then the system MUST return HTTP 400 with the generic error body  
And `hashed_password` MUST NOT be updated

**Scenario 6.4 — Successful reset**

Given a valid, unused, non-expired token T associated with user U  
When a client submits `POST /reset-password` with T and a new password P  
Then the system MUST hash P using bcrypt via the existing helper in `app/core/security.py`  
And MUST update `users.hashed_password` for user U with the new hash  
And MUST mark T as `used = True`  
And MUST return HTTP 200 with:

```json
{ "message": "Password updated successfully." }
```

---

### REQ-7: Internal Abuse Logging

The system MUST log the following events at WARNING level or higher using the existing Python
`logging` infrastructure. These logs MUST NOT alter any client-facing response.

| Event | Logged fields |
|-------|---------------|
| `/forgot-password` received for unknown email | `email_hash` (SHA-256 of submitted email), `ip`, `timestamp` |
| `/forgot-password` received for inactive account | `user_id`, `ip`, `timestamp` |

The submitted email MUST NOT be logged in plain text. Only its SHA-256 hash MAY be logged to
enable correlating repeated attempts without exposing the value.

**Scenario 7.1 — Unknown email logged**

Given a client submits `/forgot-password` with an email not in the database  
When the handler processes the request  
Then the system MUST emit one log entry at WARNING level containing `email_hash` and the client IP  
And the HTTP response to the client MUST still be the uniform 200 (see REQ-1)

**Scenario 7.2 — Inactive account logged**

Given a client submits `/forgot-password` for an inactive account  
When the handler processes the request  
Then the system MUST emit one log entry at WARNING level containing `user_id` and the client IP  
And the HTTP response to the client MUST still be the uniform 200 (see REQ-1)

---

### REQ-8: Rate Limiting

The system MUST apply rate limits to both new endpoints using the existing `slowapi` limiter
(`app/core/limiter.py`). Limits are enforced per client IP.

| Endpoint | Limit |
|----------|-------|
| `POST /forgot-password` | 3 requests / minute / IP |
| `POST /reset-password` | 5 requests / minute / IP |

When the limit is exceeded, `slowapi` MUST return HTTP 429. The implementation MUST follow the
same decorator pattern already used in the codebase (e.g., `@limiter.limit("3/minute")`).

**Scenario 8.1 — forgot-password rate limit**

Given a client IP has submitted `POST /forgot-password` 3 times within 60 seconds  
When the same IP submits a 4th request within that window  
Then the system MUST return HTTP 429  
And no token MUST be generated, no email sent, no log entry written for abuse detection

**Scenario 8.2 — reset-password rate limit**

Given a client IP has submitted `POST /reset-password` 5 times within 60 seconds  
When the same IP submits a 6th request within that window  
Then the system MUST return HTTP 429  
And no token validation MUST be attempted

---

### REQ-9: Database Schema — `password_reset_tokens`

A new table MUST be created via an Alembic migration. The table MUST have at minimum:

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID or BIGSERIAL | PRIMARY KEY |
| `user_id` | FK → `users.id` | NOT NULL, ON DELETE CASCADE |
| `token_hash` | VARCHAR / TEXT | NOT NULL, UNIQUE |
| `expires_at` | TIMESTAMP WITH TIME ZONE | NOT NULL |
| `used` | BOOLEAN | NOT NULL, DEFAULT FALSE |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() |

An index MUST exist on `(user_id, used)` to support the invalidation query (REQ-3) efficiently.

---

### REQ-10: New Pydantic Schemas

Two new request schemas MUST be defined:

**`ForgotPasswordRequest`**
- `email: EmailStr` — REQUIRED

**`ResetPasswordRequest`**
- `token: str` — REQUIRED, non-empty
- `new_password: str` — REQUIRED; minimum length enforcement is RECOMMENDED (SHOULD be ≥ 8 chars)

---

## Modified Requirements

### MOD-1: SMTP Configuration in `app/core/config.py`

The existing `Settings` class MUST be extended with the following fields (all sourced from
environment variables; `extra="ignore"` is already set). These names are the single source of
truth and MUST match the field names used by `SmtpEmailSender` and the reset service in
design.md:

- `SMTP_HOST: str`
- `SMTP_PORT: int` (default `587`)
- `SMTP_USER: str`
- `SMTP_PASSWORD: str`
- `MAIL_FROM: str` — sender identity, e.g. `"Kitchy <no-reply@vonlunant.site>"`
- `RESET_LINK_BASE_URL: str` — full base URL of the reset endpoint, including the path (e.g.,
  `https://kitchy.vonlunant.site/reset-password`); only the `?token=<plain_token>` query
  parameter is appended by the service layer.
- `RESET_TOKEN_TTL_MINUTES: int` (default `30`) — token lifetime in minutes; the default of
  30 satisfies REQ-2 while keeping the value configurable.

No existing settings fields MAY be removed or renamed.

---

## Removed Requirements

None. This delta introduces new functionality without changing existing authentication behavior.
`/register` and `/login` are untouched.

---

## Out of Scope (explicit exclusions)

- Flutter frontend: reset-password screen, deep link handling.
- SMS / WhatsApp reset channels.
- Changes to `/register` or `/login` behavior.
- Email template HTML design beyond functional content.
- Admin-initiated password resets.

---

*Design, tasks, and implementation details follow in design.md and tasks.md.*
