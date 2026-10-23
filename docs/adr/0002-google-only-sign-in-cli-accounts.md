# Production signs in with Google only, accounts come from the CLI

Status: accepted (2026-10-23)

The app has one real user, the owner, who is also the admin. They wanted no password to keep or leak in production, and Google's 2-step verification on the account. So production has no password login. "Sign in with Google" is the only way in.

Google sign-in never creates an account. It reads the verified primary email from Google and signs in only an existing, active admin with that email. Accounts come only from `python -m app.auth.cli create-superuser EMAIL PASSWORD`, which also resets a password. There are no register, forgot-password, reset or verify routes. The app stores no Google tokens, so the users table itself is the allowlist.

The password route exists only outside production, for dev and e2e. Google cannot be automated, and no test talks to Google.

## Considered options

- **A gate in front of the app** (Cloudflare Access) or **a hosted login provider** (Auth0, Clerk). Rejected by the owner: sign-in stays inside the app.
- **A hardcoded admin email or an `ADMIN_EMAIL` setting.** Rejected: the repo is public, and the CLI-created account is the one source of truth.
- **Keeping registration and password reset.** Removed: nothing ever delivered the reset tokens, and a one-person app does not need them.

## Consequences

- `/admin` reads the same auth cookie. The session lasts 7 days.
- Production refuses to start without the Google client settings.
- The API cannot change a user's email, because in production it is the sign-in key.
- Player registration is a later stage. It will revisit this ADR, since per-user data already exists ([ADR-0006](0006-player-items-per-user-two-snapshots.md)).
