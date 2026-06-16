# NBA Player API

This document describes the NBA player data APIs used by the WeChat Mini Program.

## Base URL

Use the same host as the deployed Flask service:

```text
https://your-domain.example.com
```

All endpoints in this document are relative to that host.

## Public Read APIs

These APIs are designed for the Mini Program and do not require authentication.

### List Players

```http
GET /api/nba/players
```

Returns paginated player records. The response includes profile data, season average stats, team data, and public card/avatar/team image URLs.

#### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `q` | string | No | General keyword. Matches Chinese name, English name, or team name. |
| `teamTid` | string | No | Sina team ID. Exact match. |
| `team_tid` | string | No | Alias for `teamTid`. |
| `team` | string | No | Team keyword. Matches full Chinese team name, market, or team name. |
| `teamName` | string | No | Alias for `team`. |
| `team_name` | string | No | Alias for `team`. |
| `position` | string | No | Exact player position, such as `后卫`, `前锋`, `中锋`, `控球后卫`. |
| `limit` | integer | No | Page size. Default `50`, max `200`. |
| `offset` | integer | No | Offset for pagination. Default `0`. |

#### Examples

```http
GET /api/nba/players?limit=20&offset=0
GET /api/nba/players?team=洛杉矶湖人
GET /api/nba/players?position=后卫
GET /api/nba/players?team=洛杉矶湖人&position=后卫
GET /api/nba/players?q=Luke
GET /api/nba/players?q=卢克
```

#### Response

```json
{
  "total": 1,
  "items": [
    {
      "pid": "a537047d-c29f-4dfe-99b0-3bac4e258dc7",
      "chinese_name": "卢克-肯纳德",
      "english_name": "Luke Kennard",
      "first_name": "Luke",
      "last_name": "Kennard",
      "first_name_cn": "卢克",
      "last_name_cn": "肯纳德",
      "jersey_number": "10",
      "primary_position": "后卫",
      "position": "后卫",
      "source": "sina_nba",
      "source_url": "https://slamdunk.sports.sina.com.cn/player?pid=a537047d-c29f-4dfe-99b0-3bac4e258dc7",
      "source_updated_at": "Fri Jun 12 17:39:21 +0800 2026",
      "team": {
        "tid": "583ecae2-fb46-11e1-82cb-f4ce4684ea4c",
        "market": "洛杉矶",
        "name": "湖人",
        "full_name": "洛杉矶湖人",
        "logo": {
          "filename": "Los_Angeles_Lakers.png",
          "url": "/api/nba/team-images/Los_Angeles_Lakers.png",
          "missing": false,
          "checked_at": "2026-06-16T09:10:00"
        }
      },
      "profile": {
        "birthdate": "1996-06-24",
        "age": 29,
        "nation": "美国",
        "college": "杜克大学",
        "experience": 8,
        "draft_year": "2017",
        "draft_round": "1",
        "draft_pick": "12",
        "height_cm": 196,
        "weight_kg": 93,
        "wingspan": "196cm",
        "standing_reach": "250cm",
        "current_salary": "1100万美元",
        "salary_wan_usd": 1100.0
      },
      "stats": {
        "avg_points": 8.4,
        "avg_rebounds": 2.3,
        "avg_assists": 2.2,
        "avg_steals": 0.7,
        "avg_blocks": 0.1
      },
      "image": {
        "filename": "Luke_Kennard.jpg",
        "url": "/api/nba/images/Luke_Kennard.jpg",
        "missing": false,
        "checked_at": "2026-06-15T02:46:02"
      },
      "avatar": {
        "filename": "Luke_Kennard.png",
        "url": "/api/nba/avatars/Luke_Kennard.png",
        "missing": false,
        "checked_at": "2026-06-15T02:46:02"
      },
      "created_at": "2026-06-15T01:00:00",
      "updated_at": "2026-06-15T02:46:02"
    }
  ]
}
```

### Search Players By Name

```http
GET /api/nba/players/search
```

Searches only Chinese and English player names. This endpoint is recommended for search boxes because it will not match team names.

#### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `q` | string | Yes | Name keyword. Matches Chinese or English name. |
| `keyword` | string | No | Alias for `q`. |
| `name` | string | No | Alias for `q`. |
| `teamTid` | string | No | Optional team filter. |
| `team` | string | No | Optional team keyword filter. |
| `position` | string | No | Optional position filter. |
| `limit` | integer | No | Page size. Default `20`, max `50`. |
| `offset` | integer | No | Offset for pagination. Default `0`. |

#### Examples

```http
GET /api/nba/players/search?q=卢克
GET /api/nba/players/search?q=Luke
GET /api/nba/players/search?name=Kennard
GET /api/nba/players/search?q=Luke&team=湖人
```

#### Empty Query Response

```json
{
  "total": 0,
  "items": []
}
```

For non-empty queries, the response shape is the same as `GET /api/nba/players`.

### Get Player Detail

```http
GET /api/nba/players/{pid}
```

Returns a single player record.

#### Example

```http
GET /api/nba/players/a537047d-c29f-4dfe-99b0-3bac4e258dc7
```

#### Success Response

The response is one player object, using the same player structure shown in `List Players`.

#### Not Found Response

```json
{
  "error": "球员不存在"
}
```

### Get Filter Options

```http
GET /api/nba/filters
```

Returns team and position options for UI filter controls.

#### Response

```json
{
  "teams": [
    {
      "tid": "583ecae2-fb46-11e1-82cb-f4ce4684ea4c",
      "market": "洛杉矶",
      "name": "湖人",
      "full_name": "洛杉矶湖人",
      "player_count": 18
    }
  ],
  "positions": [
    {
      "position": "后卫",
      "player_count": 162
    },
    {
      "position": "前锋",
      "player_count": 126
    }
  ]
}
```

### Get Player Card Image

```http
GET /api/nba/images/{filename}
```

Serves a player card image from the server-side `NBA_IMAGE_DIR`.

The Mini Program should use the `image.url` value returned by the player APIs.

#### Example

```http
GET /api/nba/images/Luke_Kennard.jpg
```

### Get Player Avatar

```http
GET /api/nba/avatars/{filename}
```

Serves a player avatar image from the server-side `NBA_AVATAR_DIR`.

The Mini Program should use the `avatar.url` value returned by the player APIs.

#### Example

```http
GET /api/nba/avatars/Luke_Kennard.png
```

### Get Team Image

```http
GET /api/nba/team-images/{filename}
```

Serves a team logo image from the server-side `NBA_TEAM_IMAGE_DIR`.

The Mini Program should use the `team.logo.url` value returned by the player and filter APIs.

#### Example

```http
GET /api/nba/team-images/Los_Angeles_Lakers.png
```

### List Missing Images

```http
GET /api/nba/images/missing
```

Returns players that do not currently have a matched player card image.

#### Response

```json
{
  "items": [
    {
      "pid": "example-player-id",
      "chinese_name": "示例球员",
      "english_name": "Example Player",
      "team_full_name": "示例球队"
    }
  ]
}
```

When all images are matched:

```json
{
  "items": []
}
```

### List Missing Avatars

```http
GET /api/nba/avatars/missing
```

Returns players that do not currently have a matched avatar image.

#### Response

```json
{
  "items": [
    {
      "pid": "example-player-id",
      "chinese_name": "示例球员",
      "english_name": "Example Player",
      "team_full_name": "示例球队"
    }
  ]
}
```

When all avatars are matched:

```json
{
  "items": []
}
```

### List Missing Team Images

```http
GET /api/nba/team-images/missing
```

Returns teams that do not currently have a matched team logo image.

#### Response

```json
{
  "items": [
    {
      "team_tid": "583ecb8f-fb46-11e1-82cb-f4ce4684ea4c",
      "team_market": "亚特兰大",
      "team_name": "老鹰",
      "team_full_name": "亚特兰大老鹰",
      "player_count": 19
    }
  ]
}
```

When all team images are matched:

```json
{
  "items": []
}
```

## Admin Sync APIs

These endpoints update local data. In production, set `NBA_SYNC_TOKEN` and send it with `X-NBA-Sync-Token`.

```http
X-NBA-Sync-Token: your-token
```

If `NBA_SYNC_TOKEN` is not configured, sync APIs are open. Production deployments should configure it.

### Sync One Player

```http
POST /api/nba/sync/player
Content-Type: application/json
X-NBA-Sync-Token: your-token

{
  "pid": "a537047d-c29f-4dfe-99b0-3bac4e258dc7"
}
```

#### Response

```json
{
  "ok": true,
  "player": {
    "pid": "a537047d-c29f-4dfe-99b0-3bac4e258dc7",
    "chinese_name": "卢克-肯纳德",
    "english_name": "Luke Kennard"
  }
}
```

### Sync All Players

```http
POST /api/nba/sync
Content-Type: application/json
X-NBA-Sync-Token: your-token

{
  "concurrency": 8
}
```

#### Optional Body Parameters

| Name | Type | Description |
|------|------|-------------|
| `concurrency` | integer | Concurrent player detail requests. Default `8`, max `16`. |
| `season` | string/integer | Sina season parameter. Defaults to the season returned by Sina roster data. |
| `limitTeams` | integer | Debug-only limit for number of teams to sync. |
| `limit_teams` | integer | Alias for `limitTeams`. |
| `limitPlayers` | integer | Debug-only limit for number of players to sync. |
| `limit_players` | integer | Alias for `limitPlayers`. |

#### Response

```json
{
  "ok": true,
  "result": {
    "season": 2025,
    "team_count": 30,
    "requested_count": 537,
    "succeeded_count": 537,
    "failed_count": 0,
    "errors": [],
    "elapsed_seconds": 18.205
  }
}
```

### Sync Player Images

```http
POST /api/nba/sync/images
Content-Type: application/json
X-NBA-Sync-Token: your-token
```

Matches player card files under `NBA_IMAGE_DIR` by English player name, updates `image.url`, and marks missing images.

The request body cannot override the image directory. The server always uses `NBA_IMAGE_DIR`.

#### Response

```json
{
  "ok": true,
  "result": {
    "total": 537,
    "asset_count": 587,
    "avatar_count": 587,
    "matched_count": 537,
    "missing_count": 0,
    "missing": [],
    "collisions": [],
    "checked_at": "2026-06-15T02:46:02"
  }
}
```

### Sync Player Avatars

```http
POST /api/nba/sync/avatars
Content-Type: application/json
X-NBA-Sync-Token: your-token
```

Matches avatar files under `NBA_AVATAR_DIR` by English player name, updates `avatar.url`, and marks missing avatars.

The request body cannot override the avatar directory. The server always uses `NBA_AVATAR_DIR`.

#### Response

```json
{
  "ok": true,
  "result": {
    "total": 537,
    "asset_count": 589,
    "image_count": 589,
    "matched_count": 537,
    "missing_count": 0,
    "missing": [],
    "collisions": [],
    "checked_at": "2026-06-15T02:46:02"
  }
}
```

### Sync Team Images

```http
POST /api/nba/sync/team-images
Content-Type: application/json
X-NBA-Sync-Token: your-token
```

Matches team logo files under `NBA_TEAM_IMAGE_DIR` by team name, updates `team.logo.url`, and marks missing team images.

The request body cannot override the team image directory. The server always uses `NBA_TEAM_IMAGE_DIR`.

#### Response

```json
{
  "ok": true,
  "result": {
    "total": 30,
    "asset_count": 30,
    "team_image_count": 30,
    "matched_count": 30,
    "missing_count": 0,
    "affected_player_count": 537,
    "missing": [],
    "collisions": [],
    "checked_at": "2026-06-16T09:10:00"
  }
}
```

## Deployment Notes

### Database

By default, NBA data is stored in:

```text
nba.db
```

Override it with:

```bash
NBA_DB_PATH=/home/user/recorded/nba.db
```

### Player Card Images

By default, card images are loaded from:

```text
nba_images/
```

Override it with:

```bash
NBA_IMAGE_DIR=/home/user/recorded/nba_images
```

By default, avatar images are loaded from:

```text
nba_avatar/
```

Override it with:

```bash
NBA_AVATAR_DIR=/home/user/recorded/nba_avatar
```

By default, team images are loaded from:

```text
nba_team_images/
```

Override it with:

```bash
NBA_TEAM_IMAGE_DIR=/home/user/recorded/nba_team_images
```

The image, avatar, and team image directories are server-local and should not be committed to Git. Upload them manually, then run:

```http
POST /api/nba/sync/images
POST /api/nba/sync/avatars
POST /api/nba/sync/team-images
```

### Sync Token

Production deployments should set:

```bash
NBA_SYNC_TOKEN=your-token
```

Then call sync endpoints with:

```http
X-NBA-Sync-Token: your-token
```

## Mini Program Integration Notes

- Use `GET /api/nba/filters` to render team and position filters.
- Use `GET /api/nba/players` for list pages.
- Use `GET /api/nba/players/search?q=...` for name search.
- Use `GET /api/nba/players/{pid}` for detail pages.
- Use `player.image.url` to display player card images.
- Use `player.avatar.url` to display player avatars.
- Use `player.team.logo.url` to display team logos.
- Use `team.logo.url` from `GET /api/nba/filters` for team filter controls.
- Do not use server-local filesystem paths. Public responses do not expose image paths.
- If `image.missing` is `true`, display a placeholder card image in the Mini Program.
- If `avatar.missing` is `true`, display a placeholder avatar in the Mini Program.
- If `team.logo.missing` is `true`, display a placeholder team logo in the Mini Program.
