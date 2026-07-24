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

Manifest URLs look like `https://api.example.com/nbagame/v1/assets/files/asset-<sha256>/players-0.png`. The top-level `manifestVersion` starts with `content-` and changes automatically when any whitelisted file, key, or extension changes. Each asset's `version` is content-addressed, so unchanged assets retain the same URL across manifest updates. Keep sending `X-App-Id` when reading a file. Versioned URLs are immutable and cacheable for one year. Cache by page lifecycle: merge concurrent requests for the same group, lazily load headshot sprites, reuse decoded images, and release page-specific images when leaving the page.

## Career synchronization

### `GET /bootstrap` and `GET /career`

After login, call `/bootstrap` for the profile, cloud revision, and manifest version. Call `/career` when a full restore is needed. A missing save still returns `200` with `snapshot: null` and `revision: 0`.

### `PUT /career`

Send authorization, a UUID `Idempotency-Key`, and `If-Match: "career-<revision>"`; new users send `"career-0"`. The request follows section 5 of [the backend contract](../../../nbagame/backend-integration.md), with a maximum snapshot size of 2 MB. A successful response contains `revision`, `etag`, and `updatedAt`. For `409 CAREER_CONFLICT`, reconcile against the cloud snapshot in `error.details`; never overwrite it silently. Repeating the same `clientRevision + snapshot` does not increment the server revision.

### `DELETE /career`

Authorization, a UUID `Idempotency-Key`, and the current `If-Match` are required. This deletes only the current Court Deck user's career and preserves completed-season history.

## Season completion leaderboard

### `POST /leaderboards/season-starts/events`

The legacy route name remains stable, but the event means "season completed",
not "season started". Submit it once after the career has entered `results`.

Headers:

```http
Authorization: Bearer <accessToken>
Idempotency-Key: <UUID>
Content-Type: application/json
```

Request:

```json
{
  "eventId": "2afdcac9-9b4e-4dc3-853c-34ad16b577e1",
  "seasonNumber": 2,
  "team": "LAL",
  "occurredAt": "2026-07-22T08:02:00Z"
}
```

Synchronize the completed `results` career first. The event's `seasonNumber`
and `team` must match that career. The server updates the current user's record
for that team with `max(previousHighest, seasonNumber)`.

Success:

```json
{
  "requestId": "req_06",
  "data": {
    "eventId": "2afdcac9-9b4e-4dc3-853c-34ad16b577e1",
    "team": "LAL",
    "seasonNumber": 2,
    "improved": true
  }
}
```

`seasonNumber` is the highest completed season after applying the event.
`improved` is `false` when the submitted season does not beat the stored record.
Reusing an event ID, idempotency key, or completed career revision returns the
first result and never changes the score twice. A career that is missing, is not
in `results`, or has a different team or season returns `409 CAREER_CONFLICT`.

### `GET /leaderboards/season-starts?scope=<scope>&limit=<limit>&cursor=<cursor>`

- `scope`: `personal`, `friends`, or `global`; defaults to `global`.
- `limit`: 1 through 50; defaults to 20.
- `cursor`: opaque `nextCursor` from the previous response.

Response:

```json
{
  "requestId": "req_07",
  "data": {
    "scope": "global",
    "friendsAvailable": true,
    "rows": [
      {
        "rank": 1,
        "playerName": "Player A",
        "team": "LAL",
        "seasonNumber": 12,
        "isSelf": false
      },
      {
        "rank": 8,
        "playerName": "Me",
        "team": "LAL",
        "seasonNumber": 2,
        "isSelf": true
      }
    ],
    "nextCursor": null,
    "generatedAt": "2026-07-22T08:03:00Z"
  }
}
```

`personal` returns only the current user's team records. `global` remains
application-scoped. The friend provider is not connected yet, so `friends`
returns `200`, an empty `rows` array, and `friendsAvailable: false`.

The server ranks by `seasonNumber` descending, then the earliest server time at
which that score was reached, then stable user ID and team code. Display the returned `rank`
without recalculating it. Legacy `starts` totals are retained only as historical
database data; they are neither migrated into nor returned by this leaderboard.

## Integration order

1. Configure the API base URL and `NBAGAME_APP_ID`; wrap `wx.login` and re-login after token expiry.
2. Add page-lifecycle manifest and image caching. Remove packaged assets only after migration verification.
3. Upload stable snapshots after game settlement, season simulation, upgrades, playoff changes, new seasons, and career resets. Preserve the original idempotency key when retrying.
4. Synchronize an authorized profile. After entering `results`, upload the completed career before its completion event. Fetch the leaderboard when its panel opens.
