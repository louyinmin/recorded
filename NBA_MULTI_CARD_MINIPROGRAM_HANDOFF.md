# NBA Multi-Card Mini Program Handoff

## Goal

The backend now supports one NBA player owning multiple player-card images.

The Mini Program should keep the existing player carousel behavior, but each player can now expose an ordered `cards` array. Existing clients that only read `Player.image` still work because `image` remains populated from the first available card.

## Base Rules

- Use `Player.cards` for new multi-card UI.
- Keep `Player.image` only as a fallback for old or incomplete responses.
- Preserve the current player order from `associated_home_player_pid`.
- Preserve the card order returned by the backend.
- Resolve relative image URLs against the existing API base URL.
- If a selected card no longer exists, fall back to the first available card for that player.

## Image Upload Naming

The upload directory is the backend `NBA_IMAGE_DIR`.

Use English-name numbered files:

```text
English_Name.{ext}
English_Name_1.{ext}
English_Name_2.{ext}
English_Name_3.{ext}
```

Example:

```text
A_J_Lawson.jpg
A_J_Lawson_1.jpg
A_J_Lawson_2.jpg
```

Meaning:

```text
A_J_Lawson.jpg    -> default card
A_J_Lawson_1.jpg  -> second card
A_J_Lawson_2.jpg  -> third card
```

Backend sync maps these files into stable internal card IDs:

```text
{pid}_default
{pid}_1
{pid}_2
```

The Mini Program should never derive card order from filenames. Use `cards[n].sortOrder` and the returned array order.

## Sync Endpoint

Backend operators sync uploaded images with:

```http
POST /api/nba/sync/images
X-NBA-Sync-Token: <token>
```

Response includes the active naming rule:

```json
{
  "ok": true,
  "result": {
    "card_count": 620,
    "matched_count": 537,
    "missing_count": 0,
    "checked_at": "2026-06-26T08:30:00",
    "namingRule": {
      "preferred": "English_Name.{ext}, English_Name_1.{ext}, English_Name_2.{ext}",
      "default": "English_Name.{ext}",
      "numbered": "English_Name_{n}.{ext}"
    }
  }
}
```

This endpoint is backend-only. The Mini Program does not call it.

## Player Types

Recommended Mini Program type additions:

```ts
interface PlayerAsset {
  filename?: string
  url?: string
  missing?: boolean
  checked_at?: string
}

interface PlayerCard {
  cardId: string
  pid: string
  title?: string
  season?: string
  series?: string
  variant?: string
  rarity?: string
  sortOrder: number
  image: PlayerAsset
  created_at?: string
  updated_at?: string
}

interface Player {
  pid: string
  chinese_name?: string
  english_name?: string
  image?: PlayerAsset
  cards?: PlayerCard[]
  avatar?: PlayerAsset
  updated_at?: string
}
```

## Player Detail

```http
GET /api/nba/players/{pid}
```

Response now includes `cards`:

```json
{
  "pid": "player_pid_1",
  "chinese_name": "Player One",
  "image": {
    "filename": "A_J_Lawson.jpg",
    "url": "/api/nba/card-images/A_J_Lawson.jpg",
    "missing": false
  },
  "cards": [
    {
      "cardId": "player_pid_1_default",
      "pid": "player_pid_1",
      "title": "Default Card",
      "variant": "default",
      "sortOrder": 10,
      "image": {
        "filename": "A_J_Lawson.jpg",
        "url": "/api/nba/card-images/A_J_Lawson.jpg",
        "missing": false
      }
    },
    {
      "cardId": "player_pid_1_1",
      "pid": "player_pid_1",
      "title": "Card 2",
      "variant": "1",
      "sortOrder": 20,
      "image": {
        "filename": "A_J_Lawson_1.jpg",
        "url": "/api/nba/card-images/A_J_Lawson_1.jpg",
        "missing": false
      }
    }
  ]
}
```

## Batch Player Detail

```http
GET /api/nba/players/batch?pids=player_pid_1,player_pid_2
```

Use this for home-card snapshot refresh. It returns full player objects with `cards`.

Important behavior:

- Response `items` preserves requested PID order.
- Duplicate requested PIDs are removed.
- Unknown PIDs are listed in `missingPids`.
- `dataVersion` describes only this batch response.
- Home cache invalidation should use `GET /api/nba/user-config` response `homeCards.dataVersion`, not the batch `dataVersion`.

## Optional Card List Endpoint

```http
GET /api/nba/players/{pid}/cards
```

This returns only card variants:

```json
{
  "pid": "player_pid_1",
  "items": [
    {
      "cardId": "player_pid_1_default",
      "pid": "player_pid_1",
      "sortOrder": 10,
      "image": {
        "url": "/api/nba/card-images/A_J_Lawson.jpg",
        "missing": false
      }
    }
  ],
  "updatedAt": "2026-06-26T08:30:00"
}
```

The first Mini Program implementation can skip this endpoint if home and detail pages already use full player detail responses.

## User Config

Existing fields remain:

```ts
associated_home_player_pid: string[]
current_home_player_pid: string | null
search_default_player_pid: string[]
```

New fields:

```ts
current_home_card_id: string | null
home_player_card_selection: Record<string, string>
```

Meaning:

- `current_home_card_id`: current selected card on the home page.
- `home_player_card_selection`: last selected card per player. Keys are player PIDs, values are card IDs.

Default config:

```json
{
  "associated_home_player_pid": [],
  "current_home_player_pid": null,
  "current_home_card_id": null,
  "home_player_card_selection": {},
  "search_default_player_pid": []
}
```

Patch example:

```http
PATCH /api/nba/user-config
Authorization: Bearer <sessionToken>
Content-Type: application/json

{
  "config": {
    "current_home_player_pid": "player_pid_1",
    "current_home_card_id": "player_pid_1_1",
    "home_player_card_selection": {
      "player_pid_1": "player_pid_1_1"
    }
  }
}
```

## Home Cache Metadata

```http
GET /api/nba/user-config
Authorization: Bearer <sessionToken>
```

Response includes:

```json
{
  "app": "nba",
  "config": {
    "associated_home_player_pid": ["player_pid_1"],
    "current_home_player_pid": "player_pid_1",
    "current_home_card_id": "player_pid_1_1",
    "home_player_card_selection": {
      "player_pid_1": "player_pid_1_1"
    },
    "search_default_player_pid": []
  },
  "updatedAt": "2026-06-26T08:30:00",
  "homeCards": {
    "pids": ["player_pid_1"],
    "currentPid": "player_pid_1",
    "currentCardId": "player_pid_1_1",
    "cardSelection": {
      "player_pid_1": "player_pid_1_1"
    },
    "configUpdatedAt": "2026-06-26T08:30:00",
    "playersUpdatedAt": "2026-06-26T08:20:00",
    "cardsUpdatedAt": "2026-06-26T08:30:00",
    "dataVersion": "home_8f3c0d9a1b2c"
  }
}
```

`homeCards.dataVersion` changes when:

- associated player list changes,
- current player changes,
- current card changes,
- per-player card selection changes,
- player render data changes,
- card is added, removed, renamed, reordered, or assigned a new image URL,
- card image missing state changes.

## Recommended Mini Program Selection Logic

Use this helper shape on the frontend:

```ts
function getPlayerCards(player: Player): PlayerCard[] {
  if (player.cards?.length) return player.cards
  if (player.image?.url) {
    return [{
      cardId: `${player.pid}_legacy`,
      pid: player.pid,
      sortOrder: 10,
      image: player.image
    }]
  }
  return []
}

function resolveSelectedCard(
  player: Player,
  cardSelection: Record<string, string>,
  currentCardId?: string | null
): PlayerCard | undefined {
  const cards = getPlayerCards(player)
  const selectedCardId = cardSelection[player.pid] || currentCardId || ''
  return cards.find((card) => card.cardId === selectedCardId) || cards[0]
}
```

When the user switches card inside the same player:

```ts
await patchUserConfig({
  current_home_player_pid: player.pid,
  current_home_card_id: card.cardId,
  home_player_card_selection: {
    ...previousSelection,
    [player.pid]: card.cardId
  }
})
```

When the user switches player:

- Load that player's last card from `home_player_card_selection[player.pid]`.
- If missing, use the first returned card.
- Persist both `current_home_player_pid` and `current_home_card_id`.

## Share URL

Existing share URLs with only `pid` remain valid:

```text
/pages/home/index?pid=player_pid_1&source=share
```

To share a specific card, include `cardId`:

```text
/pages/home/index?pid=player_pid_1&cardId=player_pid_1_1&source=share
```

Frontend behavior:

- If `cardId` exists and belongs to the player, select it.
- If `cardId` is missing or invalid, fall back to the first card.

## Image URL Handling

Card images use:

```text
/api/nba/card-images/{filename}
```

The old route still works:

```text
/api/nba/images/{filename}
```

New Mini Program code should render `cards[n].image.url` first.

Fallback order:

```text
selectedCard.image.url
player.image.url
local placeholder
```

## Frontend Implementation Checklist

- Add `PlayerCard` type.
- Add `cards?: PlayerCard[]` to `Player`.
- Add `current_home_card_id` and `home_player_card_selection` to user config handling.
- Add `currentCardId`, `cardSelection`, and `cardsUpdatedAt` to `homeCards` metadata handling.
- Use `homeCards.dataVersion` to decide whether to refresh the local home snapshot.
- Store selected card ID with the local home snapshot if the snapshot schema is versioned.
- Render `selectedCard.image.url` instead of only `player.image.url`.
- Add vertical or in-card card switching inside the existing player carousel.
- Preserve fallback to `Player.image` for players without `cards`.
- Include optional `cardId` in share paths when sharing a specific card.

## Validation Cases

Backend behavior already covered by tests:

- English numbered files sync as multiple cards.
- `Player.image` remains populated.
- Detail and batch responses include ordered `cards`.
- `GET /api/nba/players/{pid}/cards` returns ordered cards.
- User config accepts new card-selection fields.
- `homeCards.dataVersion` is stable across repeated reads.
- `homeCards.dataVersion` changes when card render data changes.

