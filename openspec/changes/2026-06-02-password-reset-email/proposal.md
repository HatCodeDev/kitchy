# Proposal: Password Reset via Email

**Change**: password-reset-email  
**Status**: DRAFT  
**Created**: 2026-06-02

## Problem Statement

Kitchy users authenticate with email and password (`/login` in `app/routers/auth.py`),
but there is no way to recover an account when the password is forgotten. Today a locked-out
user is permanently unable to access their account, which forces manual intervention and is a
hard blocker for real-world usage.

The change must add a self-service password reset flow. Because this is a security-sensitive
flow, it MUST resist common attacks: user enumeration, token guessing/replay, token leakage at
rest, and abuse via brute force. It also must not couple Kitchy to a single email provider: the
infrastructure is self-hosted (home server on a residential IP), so deliverability is delegated
today to a managed SMTP relay, but the project must be able to switch to a self-hosted mail
server later without code changes.

## Proposed Solution

Add a two-endpoint, token-based password reset flow with a provider-agnostic email layer.

**Flow**
1. `POST /forgot-password` accepts an email. It generates a single-use, time-limited reset token,
   stores only the token's hash, and emails the plain token (embedded in a reset link) to the
   user. It ALWAYS returns the same generic response whether or not the email exists.
2. The reset link points to `kitchy.vonlunant.site` (exposed via Cloudflare Tunnel), where the
   user submits a new password.
3. `POST /reset-password` accepts the token plus the new password. It validates the token hash,
   checks expiry and single-use state, updates `hashed_password`, and marks the token as used.

**Email delivery (key architectural requirement)**
- Sending goes behind an `EmailSender` interface with an SMTP implementation. The concrete
  provider is selected entirely via environment variables — no provider lock-in.
- Initial provider: **Resend over SMTP** (`smtp.resend.com`), chosen because a residential-IP
  home mailserver cannot guarantee deliverability (IP reputation, PTR). The `vonlunant.site`
  domain is already configured in Cloudflare DNS for SPF/DKIM/DMARC.
- Switching to a self-hosted `docker-mailserver` later is a config-only change against the same
  `EmailSender` SMTP implementation.

**Security model (must-haves)**
- **No user enumeration**: `/forgot-password` returns an identical response regardless of whether
  the email maps to a user.
- **Single-use, short-lived tokens**: expiry of 15–30 minutes; token consumed (marked `used`)
  on success.
- **Hash at rest**: tokens are generated with `secrets.token_urlsafe(32)` and only their hash is
  persisted — the plain token never touches the database.
- **Previous-token invalidation**: requesting a new token invalidates outstanding tokens for that
  user.
- **Rate limiting**: both endpoints reuse the existing `slowapi` limiter pattern
  (`app/core/limiter.py`, e.g. `@limiter.limit("10/minute")`).

## Scope

In scope:
- New table `password_reset_tokens` via Alembic migration (`user_id`, `token_hash`, `expires_at`,
  `used`).
- New endpoints `POST /forgot-password` and `POST /reset-password` in `app/routers/auth.py`.
- Reset-token service plus an `EmailSender` interface and an SMTP implementation under
  `app/services/`.
- New schemas `ForgotPasswordRequest` and `ResetPasswordRequest`.
- SMTP settings added to `app/core/config.py` (Pydantic Settings, `extra="ignore"`).
- Rate limiting on both endpoints using the existing `slowapi` pattern.
- Tests (pytest): user enumeration resistance, token expiration, single-use enforcement,
  previous-token invalidation, and rate limiting.

Out of scope:
- SMS / WhatsApp reset channels (home server has no GSM hardware) — deferred to a future phase.
- Flutter frontend changes (reset-password screen / deep link handling) — deferred to a future
  phase; this change delivers the backend API and the link target.
- Changes to existing `/register` and `/login` behavior beyond reusing shared security helpers.

## Rollback Plan

1. Remove the `POST /forgot-password` and `POST /reset-password` route handlers from
   `app/routers/auth.py`.
2. Remove the reset-token service, the `EmailSender` interface/SMTP implementation, and the new
   schemas under `app/services/` and the schemas module.
3. Remove the SMTP settings from `app/core/config.py`.
4. Downgrade the Alembic migration to drop the `password_reset_tokens` table
   (`alembic downgrade -1`).

The new table is additive and isolated, so no existing data is affected. Auth (`/register`,
`/login`) is untouched, so rollback does not impact current users.

Time to rollback: ~20 minutes.

---

*See spec.md, design.md, and tasks.md for implementation details once those phases complete.*
