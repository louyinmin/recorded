# 2026 NBA Rookies Mini Program API

## Overview

2026 rookies are stored in the existing NBA player API and grouped under a virtual team:

```text
2026 新秀
```

The normal player list, search, filters, and detail endpoints can be reused by the Mini Program.

## Admin Sync

This endpoint is for backend/admin use, not normal Mini Program browsing.

```http
POST /api/nba/sync/rookies-2026
X-NBA-Sync-Token: <sync-token>
```

Response:

```json
{
  "ok": true,
  "result": {
    "source_url": "https://news.zhibo8.com/nba/2026-06-24/6a3b1f07f33eenative.htm",
    "team_full_name": "2026 新秀",
    "requested_count": 30,
    "succeeded_count": 30,
    "failed_count": 0,
    "errors": []
  }
}
```

## Mini Program Read APIs

### Get Team Filters

```http
GET /api/nba/filters
```

The `teams` array will include:

```json
{
  "tid": "rookies-2026",
  "market": "2026",
  "name": "新秀",
  "full_name": "2026 新秀",
  "player_count": 30
}
```

Use this team as the entry for the 2026 rookie category.

### List 2026 Rookies

Recommended:

```http
GET /api/nba/players?teamTid=rookies-2026&limit=50
```

Alternative:

```http
GET /api/nba/players?team=2026%20%E6%96%B0%E7%A7%80&limit=50
```

Response shape is the same as the existing player list:

```json
{
  "items": [
    {
      "pid": "rookie-2026-01-aj-dybantsa",
      "chinese_name": "AJ·迪班萨",
      "english_name": "AJ Dybantsa",
      "team": {
        "tid": "rookies-2026",
        "full_name": "2026 新秀"
      },
      "profile": {
        "draft_year": "2026",
        "draft_round": "1",
        "draft_pick": "1"
      },
      "extension": {
        "source": "zhibo8_2026_rookies",
        "rookie": {
          "selected_team": "奇才"
        }
      }
    }
  ],
  "total": 30
}
```

### Search Rookies

Existing search endpoint works:

```http
GET /api/nba/players/search?q=迪班萨
GET /api/nba/players/search?q=AJ
```

### Get Rookie Detail

```http
GET /api/nba/players/{pid}
```

Example:

```http
GET /api/nba/players/rookie-2026-01-aj-dybantsa
```

Important fields:

```json
{
  "pid": "rookie-2026-01-aj-dybantsa",
  "chinese_name": "AJ·迪班萨",
  "english_name": "AJ Dybantsa",
  "source": "zhibo8_2026_rookies",
  "team": {
    "tid": "rookies-2026",
    "market": "2026",
    "name": "新秀",
    "full_name": "2026 新秀"
  },
  "profile": {
    "birthdate": "2007年1月29日",
    "college": "杨百翰大学",
    "draft_year": "2026",
    "draft_round": "1",
    "draft_pick": "1",
    "height_cm": 206,
    "weight_kg": 98,
    "wingspan": "7尺1（2米16）"
  },
  "extension": {
    "source": "zhibo8_2026_rookies",
    "rookie": {
      "draft_year": 2026,
      "draft_pick": 1,
      "listed_name": "AJ·迪班萨",
      "listed_position": "前锋",
      "selection_text": "奇才",
      "selected_team": "奇才",
      "university_team": "杨百翰大学",
      "height": "6尺9（2米06）",
      "weight": "217磅（98公斤）",
      "wingspan": "7尺1（2米16）",
      "player_template": "安东尼/麦迪/保罗·乔治",
      "stats_text": "迪班萨大一赛季为球队出战了35场比赛...",
      "tag": {
        "title": "模板麦迪的超强得分手！迪班萨依靠犀利进攻 锁定大年状元席位？",
        "url": "https://news.zhibo8.com/nba/2026-05-27/6a1136ff7b2c0native.htm"
      }
    }
  },
  "image": {
    "filename": "AJ_Dybantsa.jpg",
    "url": "/api/nba/images/AJ_Dybantsa.jpg",
    "missing": false
  },
  "avatar": {
    "filename": "AJ_Dybantsa.png",
    "url": "/api/nba/avatars/AJ_Dybantsa.png",
    "missing": false
  }
}
```

## Field Notes

- `team.full_name` is always `2026 新秀` for rookie records. It is a category for display and filtering.
- `extension.rookie.selected_team` is the actual selected/final team.
- If the draft text includes trades, the backend stores the final destination team. Example: `交易去灰熊，再送往活塞` becomes `活塞`.
- `extension.rookie.tag` contains the article title and URL for the detail tag.
- `extension.rookie.university_team` is the college/team from the detail page. It does not overwrite `team`.
- `顺位预测` is intentionally not returned because `draft_pick` already stores the actual pick.

## Asset Notes

Rookie card and avatar assets use the same fields as active players:

```json
{
  "image": {
    "url": "/api/nba/images/AJ_Dybantsa.jpg",
    "missing": false
  },
  "avatar": {
    "url": "/api/nba/avatars/AJ_Dybantsa.png",
    "missing": false
  }
}
```

Before assets are uploaded, `missing` will be `true` and `url` will be empty.

After placing files in server-local directories, run:

```http
POST /api/nba/sync/images
POST /api/nba/sync/avatars
```

Suggested asset list is in:

```text
asset-manifests/nba_rookies_2026_assets.json
```
