# NBA Home Cache Frontend Handoff

This document describes the backend contract for the NBA Mini Program home-page cache flow.

The frontend can render the last local home snapshot immediately, then call the backend in the background to decide whether the snapshot is still valid.

## Summary

- Use `GET /api/nba/user-config` to read user home-card metadata.
- Compare local `snapshot.dataVersion` with `response.homeCards.dataVersion`.
- If the versions match, keep the local snapshot and skip player-detail refresh.
- If the versions differ, call `GET /api/nba/players/batch?pids=...` and rebuild the local snapshot.
- Store `response.homeCards.dataVersion` as the snapshot `dataVersion`. The batch endpoint `dataVersion` is only the version of the returned batch payload.

## Endpoint: Get NBA User Config

```http
GET /api/nba/user-config
Authorization: Bearer <sessionToken>
```

Authentication is required. The token comes from `POST /api/nba/wechat/session`.

### Response

```json
{
  "app": "nba",
  "config": {
    "associated_home_player_pid": ["player_pid_1", "player_pid_2"],
    "current_home_player_pid": "player_pid_2",
    "search_default_player_pid": ["player_pid_3"]
  },
  "updatedAt": "2026-06-19T00:00:00",
  "homeCards": {
    "pids": ["player_pid_1", "player_pid_2"],
    "currentPid": "player_pid_2",
    "configUpdatedAt": "2026-06-19T00:00:00",
    "playersUpdatedAt": "2026-06-20T08:30:00",
    "dataVersion": "home_8f3c0d9a1b2c"
  }
}
```

### `homeCards` Fields

```ts
interface HomeCardsMetadata {
  pids: string[]
  currentPid: string | null
  configUpdatedAt: string | null
  playersUpdatedAt: string | null
  dataVersion: string
}
```

| Field | Meaning |
|------|---------|
| `pids` | Normalized, deduplicated, ordered home player PIDs from `associated_home_player_pid`. |
| `currentPid` | Normalized current home player PID from `current_home_player_pid`. |
| `configUpdatedAt` | Same value as top-level `updatedAt`; `null` when the user has no saved config yet. |
| `playersUpdatedAt` | Max `updated_at` among existing players in `pids`; `null` when no listed player exists. |
| `dataVersion` | Stable opaque version for the home-card render state. |

### `dataVersion` Change Rules

`homeCards.dataVersion` changes when any of these inputs change:

- `associated_home_player_pid` content or order.
- `current_home_player_pid`.
- User config `updatedAt`.
- Any associated player's home-card render fields.
- Player card image URL or missing state.
- Player avatar URL or missing state.
- Team logo URL or missing state.
- Rookie extension fields, profile fields, stats, name, jersey number, position, or team fields.

The value is opaque. The frontend should only compare it for equality and should not parse it.

## Endpoint: Batch Get Player Details

```http
GET /api/nba/players/batch?pids=player_pid_1,player_pid_2
```

Authentication is not required for this endpoint. Sending the same bearer token is harmless, but the endpoint does not depend on user identity.

### Request Rules

- `pids` is a comma-separated list.
- Empty values are ignored.
- Duplicate PIDs are removed.
- First occurrence order is preserved.
- Max unique PID count is `50`.

### Success Response

```json
{
  "items": [
    {
      "pid": "player_pid_1",
      "chinese_name": "Player One",
      "english_name": "Player One",
      "updated_at": "2026-06-20T08:30:00"
    },
    {
      "pid": "player_pid_2",
      "chinese_name": "Player Two",
      "english_name": "Player Two",
      "updated_at": "2026-06-20T08:20:00"
    }
  ],
  "missingPids": [],
  "dataVersion": "home_2c4e6a8b0d1f"
}
```

`items` contains full player detail objects with the same shape as `GET /api/nba/players/{pid}`.

`items` order follows the requested PID order after deduplication, excluding missing players.

`missingPids` contains requested PIDs that are unknown or deleted.

`dataVersion` describes this batch response only. Do not use it as the local home snapshot version; use `GET /api/nba/user-config` response `homeCards.dataVersion` for that.

### Too Many PIDs

```http
400 Bad Request
Content-Type: application/json
```

```json
{
  "message": "too many pids",
  "limit": 50
}
```

## Frontend Cache Flow

```ts
interface HomeSnapshot {
  version: 1
  currentPid: string | null
  associatedPids: string[]
  players: Player[]
  dataVersion: string
  savedAt: string
}
```

Recommended flow:

```ts
async function loadHomeCards(): Promise<HomeSnapshot | null> {
  const localSnapshot = readLocalHomeSnapshot()

  if (localSnapshot) {
    renderHomeSnapshot(localSnapshot)
  }

  const remoteConfig = await getNbaUserConfig()
  const remoteHomeCards = remoteConfig.homeCards

  if (localSnapshot?.dataVersion === remoteHomeCards.dataVersion) {
    return localSnapshot
  }

  const refreshed = await getPlayersBatch(remoteHomeCards.pids)
  const nextSnapshot: HomeSnapshot = {
    version: 1,
    currentPid: remoteHomeCards.currentPid,
    associatedPids: remoteHomeCards.pids,
    players: refreshed.items,
    dataVersion: remoteHomeCards.dataVersion,
    savedAt: new Date().toISOString(),
  }

  saveLocalHomeSnapshot(nextSnapshot)
  renderHomeSnapshot(nextSnapshot)
  return nextSnapshot
}
```

## Empty State Behavior

When the user has no associated home players, `homeCards` returns:

```json
{
  "pids": [],
  "currentPid": null,
  "configUpdatedAt": null,
  "playersUpdatedAt": null,
  "dataVersion": "home_..."
}
```

The frontend should render its normal empty or fallback state and can skip `GET /api/nba/players/batch`.

## Compatibility

Existing clients that only read these fields continue to work:

```json
{
  "app": "nba",
  "config": {},
  "updatedAt": "2026-06-19T00:00:00"
}
```

`homeCards` is additive and does not change existing `config` semantics.

## Curl Examples

Read user config and home-card metadata:

```bash
curl "https://www.onepiece188.top/api/nba/user-config" \
  -H "Authorization: Bearer REAL_SESSION_TOKEN"
```

Read player details in batch:

```bash
curl "https://www.onepiece188.top/api/nba/players/batch?pids=player_pid_1,player_pid_2"
```

Too many PIDs:

```bash
curl "https://www.onepiece188.top/api/nba/players/batch?pids=$(python3 - <<'PY'
print(','.join(f'player_{i}' for i in range(51)))
PY
)"
```

## Frontend Acceptance Checklist

- Render local `HomeSnapshot` before waiting for network.
- Compare only `snapshot.dataVersion` and `remote.homeCards.dataVersion`.
- Skip batch player request when versions match.
- Call batch player request when versions differ.
- Save `remote.homeCards.dataVersion` into the next local snapshot.
- Preserve `remote.homeCards.pids` as `associatedPids`.
- Preserve `remote.homeCards.currentPid` as `currentPid`.
- Handle `missingPids` without failing the whole home page.
- Handle empty `homeCards.pids` without calling the batch endpoint.
