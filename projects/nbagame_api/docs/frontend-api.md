# Court Deck Frontend API

## Fixed boundaries

- API base URL: `https://<API_DOMAIN>/nbagame/v1`. Replace the host for local integration.
- Application identifier: `court-deck-prod`. This public value may be stored in the build configuration as `NBAGAME_APP_ID`.
- Court Deck exclusively uses `/nbagame/v1`, `nbagame.db`, and `NBAGAME_*` environment variables. It never uses `/api/nba/*`, `/api/timing/*`, `nba.db`, or `wechat.db`.
- Success envelope: `{ "requestId": "...", "data": {} }`.
- Error envelope: `{ "requestId": "...", "error": { "code": "...", "message": "...", "details": {} } }`.
- Every `POST`, `PUT`, and `PATCH` request must use `Content-Type: application/json`.

Required production secrets are `NBAGAME_WECHAT_APPID`, `NBAGAME_WECHAT_SECRET`, and `NBAGAME_TOKEN_SECRET`. `NBAGAME_PUBLIC_BASE_URL` is also required and must be the HTTPS origin registered with WeChat. Database, asset, rate-limit, and request-size settings are documented in `docs/operations/install.md`. Secrets must remain in server-side secret management.

## Login and profile

### `POST /auth/wechat/login`

Send `X-App-Id: court-deck-prod` and `{ "code": "<wx.login one-time code>", "client": { "platform": "wechat-minigame" } }`.

The response contains `data.accessToken` with a two-hour lifetime. Send `Authorization: Bearer <accessToken>` to protected endpoints. The server exchanges the code with this game's WeChat AppID, stores only an irreversible OpenID fingerprint, and never returns the OpenID, session key, or any secret. Login attempts are rate limited; retry a `429` only after the `Retry-After` interval.

### `PUT /profile`

After the user authorizes `wx.getUserProfile`, send the authorization header and a UUID `Idempotency-Key`. Body: `{ "nickname": "Display name", "avatarUrl": "https://..." }`. Nicknames are limited to 64 characters and avatar URLs must use HTTPS. Do not call this endpoint before authorization. `/bootstrap` returns the current profile.

## Image assets

### `GET /assets/manifest?group=<group>`

This endpoint is anonymous but requires `X-App-Id`. Supported groups are `home`, `screen-shells`, `screen-modals`, `player-art`, and `headshot-sprites`; omit `group` to return all groups. Each asset includes `key`, an absolute HTTPS `url`, `contentType`, `bytes`, `sha256`, dimensions, and `version`. Send `If-None-Match` to receive `304` when unchanged.

Manifest URLs look like `https://api.example.com/nbagame/v1/assets/files/20260722.1/players-0.png`. Keep sending `X-App-Id` when reading a file. Versioned URLs are immutable and cacheable for one year. Cache by page lifecycle: merge concurrent requests for the same group, lazily load headshot sprites, reuse decoded images, and release page-specific images when leaving the page.

## Career synchronization

### `GET /bootstrap` and `GET /career`

After login, call `/bootstrap` for the profile, cloud revision, and manifest version. Call `/career` when a full restore is needed. A missing save still returns `200` with `snapshot: null` and `revision: 0`.

### `PUT /career`

Send authorization, a UUID `Idempotency-Key`, and `If-Match: "career-<revision>"`; new users send `"career-0"`. The request follows section 5 of [the backend contract](../../../nbagame/backend-integration.md), with a maximum snapshot size of 2 MB. A successful response contains `revision`, `etag`, and `updatedAt`. For `409 CAREER_CONFLICT`, reconcile against the cloud snapshot in `error.details`; never overwrite it silently. Repeating the same `clientRevision + snapshot` does not increment the server revision.

### `DELETE /career`

Authorization, a UUID `Idempotency-Key`, and the current `If-Match` are required. This deletes only the current Court Deck user's career and preserves season-start history.

## Season starts and leaderboard

### `POST /leaderboards/season-starts/events`

Send authorization and a UUID `Idempotency-Key`. Body: `{ "eventId": "<UUID>", "seasonNumber": 2, "team": "LAL", "occurredAt": "2026-07-22T08:02:00Z" }`.

Synchronize the post-transition career first, then submit the event. Its season and team must match the current career, and each career revision can increment the aggregate at most once. Reusing the event ID or idempotency key returns the first result. Leaderboard tie time is the server confirmation time, not `occurredAt`.

### `GET /leaderboards/season-starts?scope=personal|friends|global&limit=20`

`personal` returns only the current user and `global` stays within Court Deck. The friend provider is not connected yet, so `friends` returns `200`, an empty `rows` array, and `friendsAvailable: false`. The server orders and ranks rows by starts, earliest server time for reaching that count, and stable user ID. The client must display the returned `rank` without recalculating it.

## Integration order

1. Configure the API base URL and `NBAGAME_APP_ID`; wrap `wx.login` and re-login after token expiry.
2. Add page-lifecycle manifest and image caching. Remove packaged assets only after migration verification.
3. Upload stable snapshots after game settlement, season simulation, upgrades, playoff changes, new seasons, and career resets. Preserve the original idempotency key when retrying.
4. Synchronize an authorized profile. After a season transition, upload the career before the event. Fetch the leaderboard when its panel opens.
