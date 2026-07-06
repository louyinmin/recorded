# SalarySwish Mini Program API

This document describes the backend data flow for NBA salary-cap data collected from SalarySwish.

## Data Source

- League salary-cap tracker: `https://www.salaryswish.com/`
- Team detail pages: `https://www.salaryswish.com/teams/{teamSlug}`
- Example team slug: `lakers`

The collector keeps dollar strings exactly as published, such as `$55,116,288` and `-$29,178,108`.
English labels are translated where practical. Player names are normalized from SalarySwish display names like `Doncic, Luka` to `Luka Doncic`, then matched against `nba_players.english_name` to fill `playerNameCn` and `playerPid` when the local player table already has that player.

## Refresh Data

```http
POST /api/nba/sync/salaryswish
```

This endpoint requires `NBA_SYNC_TOKEN` only when the deployment has configured one, matching the existing NBA sync endpoints.

### Body

```json
{
  "teamSlug": "lakers",
  "teamSlugs": ["lakers", "warriors"],
  "concurrency": 4
}
```

Use `teamSlug` for one team, `teamSlugs` for a controlled batch, or omit both to refresh all teams discovered from the SalarySwish homepage.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `teamSlug` | string | No | Single SalarySwish team slug, such as `lakers`. |
| `team_slug` | string | No | Snake-case alias for `teamSlug`. |
| `teamSlugs` | string[] | No | Multiple SalarySwish team slugs. Every item must be a string. |
| `team_slugs` | string[] | No | Snake-case alias for `teamSlugs`. Every item must be a string. |
| `concurrency` | integer | No | Concurrent team detail fetches. The backend caps the maximum. |

Invalid slug parameter types return `400`:

```json
{
  "message": "teamSlug must be a string"
}
```

```json
{
  "message": "teamSlugs must be an array of team slugs"
}
```

```json
{
  "message": "teamSlugs must contain only strings"
}
```

### Script

```bash
python -m nba_backend.sync_salaryswish --team lakers
python -m nba_backend.sync_salaryswish --concurrency 4
```

The script writes into `NBA_DB_PATH`, or `nba.db` under `RECORDED_BASE_DIR` when `NBA_DB_PATH` is not set.

## List Team Cap Snapshot

```http
GET /api/nba/salaryswish/teams
```

Returns the homepage salary-cap tracker rows for Mini Program team lists.

```json
{
  "items": [
    {
      "teamSlug": "lakers",
      "season": "2026-27",
      "teamNameEn": "Los Angeles Lakers",
      "teamNameCn": "洛杉矶湖人",
      "teamAbbr": "LAL",
      "capHit": "$194,139,108",
      "capRoom": "-$29,178,108",
      "luxuryRoom": "$6,288,892",
      "firstApronRoom": "$14,875,892",
      "secondApronRoom": "$27,546,892",
      "hardCap": "-",
      "hardCapCn": "-",
      "rosterSize": {
        "display": "19/21",
        "count": 19,
        "limit": 21
      },
      "twoWays": {
        "display": "3/3",
        "count": 3,
        "limit": 3
      },
      "sourceUrl": "https://www.salaryswish.com/teams/lakers",
      "fetchedAt": "2026-07-06T12:00:00",
      "updatedAt": "2026-07-06T12:00:00"
    }
  ]
}
```

## Get Team Detail

```http
GET /api/nba/salaryswish/teams/{teamSlug}
```

Returns team summary, signing exceptions, trade exceptions, draft assets, and grouped roster/contract rows.

### Key Fields

| Field | Description |
| --- | --- |
| `summary` | Team cap overview from the top of the SalarySwish team page. |
| `signingExceptions` | Bi-Annual, Mid-Level, and other signing exception bars. |
| `tradeExceptions` | Trade exception table. Player names include Chinese matches when available. |
| `draftAssets` | Draft table grouped by year and round. Logo teams are translated to Chinese when known. |
| `draftAssets[].assets` | All visible draft pick markers in that cell, including owned, in-contention/swap, and traded-away markers. |
| `draftAssets[].ownedAssets` | Picks that are currently held outright. Use this field when the Mini Program needs to show only picks the team still owns. |
| `draftAssets[].contentionAssets` | Picks whose final owner is unresolved, such as swap/in-contention picks. |
| `draftAssets[].tradedAwayAssets` | Picks shown by SalarySwish as traded away. |
| `draftAssets[].assets[].ownershipStatus` | One of `owned`, `in_contention`, or `traded_away`. |
| `draftAssets[].assets[].ownershipStatusCn` | Chinese status label: `持有`, `互换/待定`, or `已交易走`. |
| `rosterSections` | Contract tables grouped by section, such as active roster, training camp, G-League, RFA, UFA, and cap holds. |
| `seasonSalaries[].value` | First visible salary value extracted from a SalarySwish season cell. |
| `seasonSalaries[].raw` | Original cell text retained for audit/debug display. |
| `seasonSalaries[].freeAgentStatusCn` | Translated `UFA` or `RFA` marker when present. |
| `playerPid` | Matched local NBA player ID. Empty when the SalarySwish player is not in `nba_players`. |

### Example

```json
{
  "summary": {
    "teamSlug": "lakers",
    "teamNameCn": "洛杉矶湖人",
    "capHit": "$194,139,108",
    "hardCapped": "No",
    "hardCappedCn": "否",
    "headExecutive": "Rob Pelinka",
    "headCoach": "J.J. Redick"
  },
  "signingExceptions": [
    {
      "nameEn": "Mid-Level",
      "nameCn": "中产特例",
      "remaining": "$5,775,707",
      "total": "$15,044,000"
    }
  ],
  "tradeExceptions": [
    {
      "playerNameEn": "Gabe Vincent",
      "playerNameCn": "盖布-文森特",
      "exception": "$500,000",
      "remaining": "$500,000"
    }
  ],
  "rosterSections": [
    {
      "sectionKey": "active",
      "titleCn": "现役",
      "items": [
        {
          "playerNameRaw": "Doncic, Luka",
          "playerNameEn": "Luka Doncic",
          "playerNameCn": "卢卡-东契奇",
          "statusCn": "活跃名单",
          "acquiredCn": "交易",
          "positionsCn": "控卫, 分卫",
          "termsCn": "顶薪",
          "seasonSalaries": [
            {
              "season": "2026-27",
              "value": "$51,033,600",
              "raw": "$51,033,600$51,033,600$51,033,600$0"
            }
          ]
        }
      ]
    }
  ]
}
```
