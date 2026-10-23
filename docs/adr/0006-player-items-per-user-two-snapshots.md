# Player items are per user, one user is one game account, two newest snapshots per place

Status: accepted (2026-10-23)

The end goal is help with crafting, so the app must know what the player owns in every place: each character's bag and warehouse, and the house chests. Today only the owner uses it, but other players should get their own items later.

So inventory data is stored per user from the start, and the admin is a user like any other. Every inventory query is scoped to the signed-in user, and another user's character is a 404. A character is known by its name within one user.

One user is one game account. That account has several characters, and the house chests (numbered 1 to 10 by the player) belong to the account, not to a character.

For each place, only the newest and the previous snapshot are kept. Change marks compare a place with its own previous snapshot, so nothing older is needed. The app knows a place as it was at the last save in game, never live.

## Considered options

- **Several game accounts per user.** Out of scope: house chests 1-10 from two accounts would collide.
- **Full snapshot history.** Not needed for the grids or change marks.
- **A `/admin` view of snapshots.** Rejected: it would let the admin browse every user's items.

## Consequences

- An upload keeps the two newest snapshots per place by save time. Re-uploading changes nothing, and an older snapshot is skipped.
- A chest's name is stored apart from its snapshots, so it outlives them.
- Today every account is an admin, so the non-admin path runs only in tests until player registration ([ADR-0002](0002-google-only-sign-in-cli-accounts.md)).
