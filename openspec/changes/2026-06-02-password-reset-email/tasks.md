# Tasks: Password Reset via Email

**Change**: password-reset-email  
**Status**: DONE (Phase 8 is manual — operator tasks, not implemented by sdd-apply)  
**Created**: 2026-06-02

---

## Phase 1: Dependencies and Configuration

- [x] 1.1 Add `aiosmtplib` to `requirements.txt`
  - Satisfies: design.md (`SmtpEmailSender` implementation)
  - Add the pinned version below any existing async dependencies
  - Note: do NOT add `fastapi-mail` — design chose `aiosmtplib` directly

- [x] 1.2 Extend `app/core/config.py` — add SMTP + reset settings to `Settings`
  - Satisfies: MOD-1
  - New fields (exact names, no deviation):
    - `SMTP_HOST: str`
    - `SMTP_PORT: int = 587`
    - `SMTP_USER: str`
    - `SMTP_PASSWORD: str`
    - `MAIL_FROM: str`
    - `RESET_LINK_BASE_URL: str = "https://kitchy.vonlunant.site/reset-password"`
    - `RESET_TOKEN_TTL_MINUTES: int = 30`
  - Do NOT remove or rename any existing field

---

## Phase 2: Data Model and Migration

> Depends on Phase 1 (config must exist before migration imports `settings`).

- [x] 2.1 Create `app/models/password_reset_token.py` — `PasswordResetToken` SQLAlchemy model
  - Satisfies: REQ-9
  - Columns: `id` (UUID PK, default `uuid4`), `user_id` (UUID FK → `users.id` ON DELETE CASCADE), `token_hash` (VARCHAR(64), indexed), `expires_at` (TIMESTAMP tz), `used` (BOOLEAN, default `false`), `created_at` (TIMESTAMP tz, server default `now()`)
  - Follow the exact mapped-column style from design.md
  - Add `index=True` on both `user_id` and `token_hash` columns

- [x] 2.2 Register `PasswordResetToken` in `app/models/__init__.py`
  - Satisfies: REQ-9 (Alembic autogenerate must see the model)
  - Import and expose `PasswordResetToken` alongside existing model exports

- [x] 2.3 Generate and edit Alembic migration `alembic/versions/<rev>_add_password_reset_tokens.py`
  - Satisfies: REQ-9
  - `upgrade()`: `op.create_table("password_reset_tokens", ...)` with all columns from design.md, then `op.create_index("ix_password_reset_tokens_token_hash", ...)` and `op.create_index("ix_password_reset_tokens_user_id", ...)`
  - `downgrade()`: drop both indexes, then `op.drop_table("password_reset_tokens")`
  - Run `alembic upgrade head` locally to verify the migration applies cleanly

---

## Phase 3: Email Layer

> Can run in parallel with Phase 2 — no data model import needed here.

- [x] 3.1 Create `app/services/email/__init__.py` (empty, marks package)

- [x] 3.2 Create `app/services/email/base.py` — `EmailSender` ABC
  - Satisfies: REQ-5
  - Single abstract method: `async def send_reset_email(self, to_email: str, reset_link: str) -> None`
  - Docstring: "Send a password reset email. Raises EmailSendError on failure."

- [x] 3.3 Create `app/services/email/smtp.py` — `SmtpEmailSender`
  - Satisfies: REQ-5
  - Extends `EmailSender`; builds an `EmailMessage` and calls `aiosmtplib.send(...)` with `start_tls=True`
  - Reads `settings.SMTP_HOST`, `settings.SMTP_PORT`, `settings.SMTP_USER`, `settings.SMTP_PASSWORD`, `settings.MAIL_FROM`
  - Follow exact implementation from design.md; do not add extra headers or HTML at this stage

---

## Phase 4: Password Reset Service

> Depends on Phase 2 (model) and Phase 3 (email interface).

- [x] 4.1 Create `app/services/password_reset_service.py` — `PasswordResetService`
  - Satisfies: REQ-2, REQ-3, REQ-6
  - Method `async def request_reset(self, db: AsyncSession, email_sender: EmailSender, email: str) -> None`:
    - Look up user by email; if missing or `is_active = False` → log internally (see REQ-7) and return silently
    - Invalidate previous tokens: `UPDATE password_reset_tokens SET used = True WHERE user_id = :id AND used = False AND expires_at > now()`
    - Generate `plain_token = secrets.token_urlsafe(32)`; compute `token_hash = hashlib.sha256(plain_token.encode()).hexdigest()`
    - Insert new `PasswordResetToken(user_id=..., token_hash=..., expires_at=now() + timedelta(minutes=settings.RESET_TOKEN_TTL_MINUTES), used=False)`
    - Build `reset_link = f"{settings.RESET_LINK_BASE_URL}?token={plain_token}"`
    - Call `await email_sender.send_reset_email(user.email, reset_link)`; catch `Exception` → log internally, do NOT re-raise (avoid leaking SMTP errors to client)
  - Method `async def reset_password(self, db: AsyncSession, token: str, new_password: str) -> None`:
    - Compute `digest = hashlib.sha256(token.encode()).hexdigest()`
    - SELECT row WHERE `token_hash = :digest`; if not found → raise `InvalidTokenError`
    - If `row.used` → raise `InvalidTokenError`
    - If `row.expires_at <= datetime.now(tz=timezone.utc)` → raise `InvalidTokenError`
    - Call `get_password_hash(new_password)` from `app/core/security.py`; update `users.hashed_password`
    - Set `row.used = True`; commit
  - Define `InvalidTokenError(Exception)` in the same module (or a shared `exceptions.py` if one exists)
  - Plain token MUST NOT appear in any log line

---

## Phase 5: Pydantic Schemas

> Can run in parallel with Phase 4 — no service import needed.

- [x] 5.1 Add `ForgotPasswordRequest` and `ResetPasswordRequest` to the existing schemas module
  - Satisfies: REQ-10
  - Locate the existing auth schemas file (e.g., `app/schemas/auth.py`) and append:
    - `ForgotPasswordRequest`: `email: EmailStr`
    - `ResetPasswordRequest`: `token: str` (non-empty, `min_length=1`), `new_password: str` (`min_length=8`)
  - Do not create a new schemas file if one already exists for auth

---

## Phase 6: Endpoints

> Depends on Phase 4 and Phase 5.

- [x] 6.1 Add `POST /forgot-password` to `app/routers/auth.py`
  - Satisfies: REQ-1, REQ-7, REQ-8 (Scenario 1.1, 1.2, 1.3, 7.1, 7.2, 8.1)
  - Decorator: `@router.post("/forgot-password")` + `@limiter.limit("3/minute")` (follow existing decorator order in the file)
  - Body: `ForgotPasswordRequest`
  - Calls `await password_reset_service.request_reset(db, email_sender, body.email)`
  - Always returns `HTTP 200` with `{"message": "If that email is registered, you will receive a reset link shortly."}`
  - The service handles all branching; the router MUST NOT inspect service return values for user-enumeration-safe responses

- [x] 6.2 Add `POST /reset-password` to `app/routers/auth.py`
  - Satisfies: REQ-6, REQ-8 (Scenario 6.1, 6.2, 6.3, 6.4, 8.2)
  - Decorator: `@router.post("/reset-password")` + `@limiter.limit("5/minute")`
  - Body: `ResetPasswordRequest`
  - Calls `await password_reset_service.reset_password(db, body.token, body.new_password)`
  - On `InvalidTokenError` → return `HTTP 400` with `{"detail": "Invalid or expired reset token."}`
  - On success → return `HTTP 200` with `{"message": "Password updated successfully."}`

- [x] 6.3 Wire `EmailSender` as a FastAPI dependency in `app/routers/auth.py` (or `app/dependencies.py`)
  - Satisfies: REQ-5 (injectable interface)
  - Define `def get_email_sender() -> EmailSender: return SmtpEmailSender()`
  - Inject via `email_sender: EmailSender = Depends(get_email_sender)` in the forgot-password handler

---

## Phase 7: Tests

> Depends on Phase 6 (all production code must exist before writing tests in standard mode).

- [x] 7.1 Test: anti-enumeration — unknown email returns 200, no email sent
  - Satisfies: REQ-1 (Scenario 1.1), REQ-5 (Scenario 5.2)
  - File: `tests/routers/test_auth_password_reset.py` (create; follow `tests/routers/test_auth_rate_limit.py` structure)
  - Mock `EmailSender`; assert `send_reset_email` NOT called; assert response body == uniform message

- [x] 7.2 Test: anti-enumeration — inactive account returns 200, no email sent
  - Satisfies: REQ-1 (Scenario 1.2), REQ-5 (Scenario 5.2)
  - Create inactive user fixture; assert same uniform 200; assert mock `send_reset_email` NOT called

- [x] 7.3 Test: token generation and hash storage
  - Satisfies: REQ-2 (Scenario 2.1)
  - Assert `PasswordResetToken.token_hash == sha256(plain_token)`; assert plain token NOT in DB row; assert `used = False`; assert `expires_at ≈ now() + 30 min` (within 5 s tolerance)

- [x] 7.4 Test: previous token invalidated on new request
  - Satisfies: REQ-3 (Scenario 3.1)
  - Create T1; request a second reset; assert T1 has `used = True`; assert only T2 is valid

- [x] 7.5 Test: expired token rejected at reset
  - Satisfies: REQ-6 (Scenario 6.3)
  - Create a token with `expires_at = now() - 1 second`; call `POST /reset-password`; assert HTTP 400 with generic body

- [x] 7.6 Test: already-used token rejected
  - Satisfies: REQ-6 (Scenario 6.2)
  - Use a valid token once (successful reset); submit same token again; assert HTTP 400

- [x] 7.7 Test: successful password reset
  - Satisfies: REQ-6 (Scenario 6.4)
  - Submit valid token + new password; assert HTTP 200; assert `users.hashed_password` updated; assert token `used = True`

- [x] 7.8 Test: rate limit on `/forgot-password` (3/min)
  - Satisfies: REQ-8 (Scenario 8.1)
  - File: can extend `tests/routers/test_auth_rate_limit.py` if it exists, or add to `test_auth_password_reset.py`
  - Submit 4 requests from same IP within window; assert 4th returns HTTP 429; assert `send_reset_email` called at most 3 times

- [x] 7.9 Test: rate limit on `/reset-password` (5/min)
  - Satisfies: REQ-8 (Scenario 8.2)
  - Submit 6 requests; assert 6th returns HTTP 429; assert no DB write on the 6th

---

## Phase 8: Manual Setup Checklist

> These are operator tasks — not implemented by `sdd-apply`. Complete before first production deployment.

- [ ] 8.1 Add SMTP settings to `.env` (and `.env.example` if it exists):
  ```
  SMTP_HOST=smtp.resend.com
  SMTP_PORT=587
  SMTP_USER=resend
  SMTP_PASSWORD=<your-resend-api-key>
  MAIL_FROM=Kitchy <no-reply@vonlunant.site>
  RESET_LINK_BASE_URL=https://kitchy.vonlunant.site/reset-password
  RESET_TOKEN_TTL_MINUTES=30
  ```

- [ ] 8.2 Verify sender domain in Resend dashboard
  - Go to resend.com → Domains → Add `vonlunant.site`
  - Note the DKIM public key and return-path CNAME that Resend provides

- [ ] 8.3 Add DNS records in Cloudflare for `vonlunant.site`
  - Add the DKIM TXT record (`resend._domainkey.vonlunant.site`)
  - Add the SPF TXT record (`v=spf1 include:amazonses.com ~all` or the one Resend specifies)
  - Add the CNAME for the bounce subdomain if Resend requires it
  - Wait for Resend to confirm domain verification (green status)

- [ ] 8.4 Run `alembic upgrade head` against the production database before deploying the new code

---

## Summary

**Total Tasks**: 28 (24 implementation + 4 manual)  
**Parallel opportunities**: Phase 3 can run concurrently with Phase 2; Phase 5 can run concurrently with Phase 4  
**Sequential bottleneck**: Phase 6 (endpoints) must wait for both Phase 4 and Phase 5 to be complete

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| Estimated lines changed | ~420–480 (new files: ~300; modified files: ~120–180) |
| Chained PRs recommended | No |
| 400-line budget risk | High |
| Decision needed before apply | Yes — the diff is estimated above 400 lines; flag for `size:exception` or split into two slices (infra: phases 1–3; logic+API: phases 4–7) |

**Breakdown by slice (if splitting):**

| Slice | Phases | Estimated lines | Risk |
|-------|--------|-----------------|------|
| Slice A — Infrastructure | 1, 2, 3 | ~180 | Low |
| Slice B — Service + Endpoints + Tests | 4, 5, 6, 7 | ~250–300 | Med |

If the team prefers a single PR, record `size:exception` and proceed. Both slices are independently reviewable; Slice A has no user-visible behavior, so it can land first without a feature flag.
