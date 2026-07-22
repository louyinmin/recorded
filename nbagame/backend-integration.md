# Court Deck 微信小游戏后端对接文档

**版本：** v1.0
**日期：** 2026-07-22
**适用对象：** 后端、运维、小游戏前端
**本阶段范围：** 后端先行开发；当前小游戏不改代码。接口、字段和缓存约定冻结后，前端再接入。

## 1. 目标与边界

本项目需要把大体积图片从小游戏包中迁出，并把玩家生涯和排行榜数据同步到后端。后端已有多个小程序/小游戏应用，所有身份、数据、资源和排行榜必须按应用隔离。

本期后端应提供：

- 微信登录换取本应用内会话；
- 图片资源清单和资源文件访问；
- 生涯进度的读取、整包快照同步、并发冲突处理；
- 开季记录及个人、好友、全服排行榜；
- 在页面生命周期内可复用的资源/API 响应缓存支持。

不在本期范围内：把比赛判定迁至服务端、实时对战、支付、跨应用合并账号、前端改造。客户端的比赛模拟仍在本地执行；后端保存同步快照并从可信字段生成排行榜，不接受客户端提交的“名次”。

## 2. 总体约束

### 2.1 应用与用户隔离

每个小游戏在后端应用注册表中有一个不可变的 `app_id`，例如 `court-deck-prod`。该值仅用于定位应用，不是密钥；小游戏构建配置中固定携带它。

微信 `code` 只能由后端使用该 `app_id` 对应的 AppID/AppSecret 换取 `openid`。后端签发的 access token 必须同时包含：

```json
{
  "sub": "user_application_id",
  "app_id": "court-deck-prod",
  "openid": "opaque-or-encrypted",
  "exp": 1780000000
}
```

所有需要身份的路由都从 token 获取 `app_id` 和当前用户；不得信任请求体、查询参数或客户端 header 中的 `user_id`、`openid`、`app_id`。资源清单可匿名访问，但必须按请求的已注册 `app_id` 返回该应用资源，不能借此读取其他应用配置。

### 2.2 统一约定

- 基础地址：`https://api.example.com/nbagame/v1`（上线时替换域名，并配置到微信合法域名）。
- 编码：UTF-8 JSON；时间均为 ISO 8601 UTC，例如 `2026-07-22T08:00:00Z`。
- 认证：`Authorization: Bearer <access_token>`。
- 应用标识：未登录资源接口使用 `X-App-Id: court-deck-prod`；已登录接口以 token 为准。
- 所有成功响应：`{ "requestId": "...", "data": { ... } }`。
- 所有失败响应：`{ "requestId": "...", "error": { "code": "...", "message": "...", "details": {} } }`。
- 所有写接口要求 `Idempotency-Key`（UUID）。同一应用、同一用户、同一接口、同一 key 在 24 小时内必须返回第一次处理的结果，禁止重复计数。
- 业务枚举、队伍代码、属性键使用本文定义值；未知字段忽略，未知必填字段拒绝并返回 `VALIDATION_ERROR`。

## 3. 鉴权与初始化

### 3.1 微信登录

`POST /auth/wechat/login`

请求头：`X-App-Id: court-deck-prod`

```json
{
  "code": "wx.login 返回的一次性 code",
  "client": {
    "platform": "wechat-minigame",
    "clientVersion": "1.0.0",
    "assetManifestVersion": "20260722.1"
  }
}
```

成功响应：

```json
{
  "requestId": "req_01",
  "data": {
    "accessToken": "eyJ...",
    "expiresIn": 7200,
    "user": {
      "id": "usrapp_01",
      "nickname": null,
      "avatarUrl": null,
      "isNew": true
    }
  }
}
```

后端行为：根据 `X-App-Id` 找到微信凭据，调用微信 `code2Session`；以 `(application_id, openid)` upsert 应用用户；只保存业务需要的 `openid` 加密值/密文索引，禁止在日志输出 `code`、`session_key`、明文 `openid` 或 token。

建议补充 `POST /auth/refresh`。refresh token 若采用，必须同样绑定 `application_id`，并支持吊销；也可让小游戏在 access token 过期后重新 `wx.login`。

### 3.2 初始化聚合读取

`GET /bootstrap`

用途：登录后一次取得云端生涯版本、当前用户资料和资源清单版本，减少首屏请求数。资源详情仍由第 4 节清单接口按组获取。

成功响应：

```json
{
  "requestId": "req_02",
  "data": {
    "profile": { "id": "usrapp_01", "nickname": null, "avatarUrl": null },
    "career": { "exists": true, "revision": 18, "updatedAt": "2026-07-22T08:00:00Z" },
    "assets": { "manifestVersion": "20260722.1" }
  }
}
```

## 4. 图片资源服务

### 4.1 迁移范围

当前实际运行时引用的资源约为：根目录 `images/` 约 **22 MB**，头像子包 `subpackages/headshots/images/` 约 **15 MB**。其中头像精灵 15 张、合计约 14.6 MB，是首要迁移对象。

只迁移下表资源；未被当前运行时引用的历史 PNG/JPG、设计验证图、截图和旧版本 shell 不入库、不提供接口。

|资源组|资源键规则|现有来源|用途|加载时机|
|---|---|---|---|---|
|`home`|`broadcast-home-v6`、`broadcast-arena-bg`|`images/broadcast-home-v6.png` 等|首页和背景|首页首次进入|
|`screen-shells`|`battle-shell-v9`、`season-summary-leaderboard-v1`、`leaderboard-shell-v1`、`season-hub-shell-v1`、`playoff-hub-shell-v1`|`images/*.jpg`|战斗、赛季结算、排行榜、常规赛、季后赛框架|进入对应页面|
|`screen-modals`|`season-modal-manual-v1`、`season-modal-standings-v1`、`season-modal-stats-v1`|`images/*.jpg`|赛季中心弹层|打开对应弹层|
|`player-art`|`my-core-star-card-anime-v1`、`battle-die-body-v2`|`images/*.jpg/png`|自建球员卡、骰子|对应页面|
|`headshot-sprites`|`players-0` 至 `players-14`|`subpackages/headshots/images/players-*.png`|球员头像精灵图|需要展示阵容时按 sheet 懒加载|

`broadcast-position`、`broadcast-build-v2`、`broadcast-reveal-v2`、`broadcast-profile`、`broadcast-hub` 仍被页面渲染器引用，也应作为 `screen-shells` 中的独立资源键迁移。`bg`、`Common`、`hero`、`enemy`、`bullet` 和 `explosion*` 仅当旧玩法仍需要时迁移到 `legacy-runtime`；当前主流程不应为它们建立预加载。

### 4.2 资源清单

`GET /assets/manifest?group=<group>`

请求头：`X-App-Id: court-deck-prod`。`group` 为上表资源组；不传时返回全部组的元数据，但客户端接入后应按组请求。

支持条件请求：客户端保存上次的 `ETag`，下次传 `If-None-Match`；内容未变时返回 `304`，无响应体。响应必须带：

```http
Cache-Control: public, max-age=300, stale-while-revalidate=60
ETag: "assets-court-deck-prod-20260722.1-screen-shells"
Vary: X-App-Id
```

成功响应：

```json
{
  "requestId": "req_03",
  "data": {
    "appId": "court-deck-prod",
    "group": "screen-shells",
    "manifestVersion": "20260722.1",
    "assets": [
      {
        "key": "season-hub-shell-v1",
        "url": "https://api.example.com/nbagame/v1/assets/files/20260722.1/season-hub-shell-v1.jpg",
        "contentType": "image/jpeg",
        "bytes": 401408,
        "sha256": "base64-or-hex-digest",
        "width": 780,
        "height": 1688,
        "version": "20260722.1"
      }
    ]
  }
}
```

`GET /assets/files/{version}/{key}.{ext}`

- 文件访问必须验证 `version/key/ext` 属于请求应用；不存在返回 `404 ASSET_NOT_FOUND`。
- 可以由 API 网关直接回源对象存储，或使用应用隔离的 CDN；对小游戏暴露的仍应是本 API 域名或该 API 授权的 CDN 域名。
- 已发布的版本路径不可覆盖。内容变更必须发布新 `manifestVersion` 和新 URL（或新版本路径），从根源避免缓存污染。
- 成功文件响应：`Cache-Control: public, max-age=31536000, immutable`、`ETag`、正确 `Content-Type`、`Content-Length`、`X-Content-Type-Options: nosniff`。不需要 Cookie，也不得携带其他应用的鉴权信息。

### 4.3 客户端页面缓存契约（供后续前端接入）

缓存目标是“同一页面生命周期内不重复请求/下载/解码”，不是永久离线缓存。

1. 页面（或当前 Canvas screen）首次需要某资源组时，先读内存 `pageAssetCache[group]`；命中则直接复用已有 URL、下载文件路径或 `wx.createImage()` 实例。
2. 未命中时请求一次 manifest；同一组的并发请求必须合并为同一个 Promise。按需下载图片后写入 `pageAssetCache`，并在图片 `onload` 后复用同一实例。
3. 退出该页面时释放该页面专属 cache 和图片实例；跨页面通用资源可保留在 `appAssetCache`，但不要求持久化到下一次冷启动。
4. 只要当前进程内的 `manifestVersion` 不变，不再请求同一组 manifest。版本发生变化时，新页面使用新 URL；正在绘制的页面继续使用旧实例，避免闪烁。
5. 资源请求失败时允许回退到包内兜底资源（迁移过渡期），记录一次可观测错误；不可无限重试。后端不因短暂缓存未命中返回业务错误。

后端只需保证 manifest 的 ETag/版本和不可变文件 URL 正确；页面内对象复用由后续前端实现。

## 5. 生涯进度同步

### 5.1 数据原则

- 云端以“最后确认的完整生涯快照”保存。当前游戏状态包含赛程、常规赛/季后赛战果和统计，拆成大量细粒度写接口会放大失败与一致性风险。
- 客户端有递增的 `clientRevision`；服务端写成功后返回单调递增的 `revision`。同一份快照重复上传必须幂等。
- `battle` 动画中的临时状态不上传；只有比赛已结算、赛季模拟结束、属性强化完成、进入/结束季后赛、开新赛季、重开旅程等稳定状态上传。
- 客户端本地存储仍是弱网兜底；登录/恢复时以服务端 revision 做冲突判断。排行榜由服务端聚合事件生成，不能使用客户端传入的排名字段。

### 5.2 读取

`GET /career`

```json
{
  "requestId": "req_04",
  "data": {
    "revision": 18,
    "updatedAt": "2026-07-22T08:00:00Z",
    "snapshot": { "schemaVersion": 1, "state": {} }
  }
}
```

无存档时返回 `200` 且 `snapshot: null`、`revision: 0`，不要用 404。响应：`Cache-Control: private, no-store`。

### 5.3 快照写入

`PUT /career`

请求头：`Authorization`、`Idempotency-Key`、`If-Match: "career-18"`。新用户使用 `If-Match: "career-0"`。

```json
{
  "schemaVersion": 1,
  "clientRevision": 18,
  "clientUpdatedAt": "2026-07-22T08:00:00Z",
  "reason": "regular_game_completed",
  "snapshot": {
    "phase": "season",
    "position": "PG",
    "attrs": { "three": 88, "mid": 81, "pass": 90, "rebound": 70, "athletic": 84, "clutch": 86 },
    "careerTeam": "LAL",
    "progression": {
      "seasonNumber": 1,
      "upgradePoints": 2,
      "regularRewards": 1,
      "playoffWins": 0,
      "championships": 0
    },
    "season": {
      "seasonNumber": 1,
      "wins": 12,
      "losses": 6,
      "currentWinStreak": 3,
      "schedule": [],
      "games": [],
      "playerStats": {},
      "playoffStats": {},
      "standings": {},
      "qualification": null,
      "round": 0,
      "isChampion": false,
      "playoffResult": null
    },
    "leaderboardProfile": {
      "playerName": "我",
      "totalStarts": 1,
      "teamStarts": { "LAL": 1 },
      "lastTeam": "LAL"
    }
  }
}
```

当前前端内部字段与上述对应：`court-deck-career-v2.state` 是 `snapshot` 的主体；`season.processedDays` 在 JSON 中必须是数组；`battle` 始终为 `null`；`court-deck-leaderboard-v1` 作为 `leaderboardProfile` 一并镜像。后端保存原始 snapshot JSON，同时抽取查询字段：`season_number`、`career_team`、`phase`、`wins`、`losses`、`is_champion`、`playoff_result`、`updated_at`。

服务端校验至少包括：

- `schemaVersion = 1`；`phase` 属于 `menu/reveal/season/playin/playoff/results`；
- 位置只允许 `PG/SG/SF/PF/C`；属性键固定为 `three/mid/pass/rebound/athletic/clutch`，值为 0–100；
- 队伍代码必须是当前游戏支持的 NBA 队伍代码；`wins/losses` 非负且常规赛不超过 82；
- `season.seasonNumber` 与 `progression.seasonNumber` 一致；
- 请求体禁止带 `rank`、其他用户 ID、其他应用 ID。若出现，忽略 `rank`，其他越权字段返回 `VALIDATION_ERROR`；
- 设置合理 JSON 大小上限（建议 2 MB）与嵌套深度上限，防止异常快照占满存储。

成功响应：

```json
{
  "requestId": "req_05",
  "data": {
    "revision": 19,
    "etag": "career-19",
    "updatedAt": "2026-07-22T08:00:01Z"
  }
}
```

当 `If-Match` 与当前版本不一致时返回 `409 CAREER_CONFLICT`，并携带当前云端 `revision`、`updatedAt` 与 snapshot。前端后续策略：未提交的本地修改按 `clientUpdatedAt` 较新者覆盖；相同时间或无法判定时保留云端并提示用户。后端不可静默“最后写入覆盖”。

`DELETE /career` 用于“重新旅程”后的云端清档，必须带 `If-Match` 和 `Idempotency-Key`；只删除该 `application_id + user_application_id` 的生涯快照，不删除开季排行榜历史。

## 6. 开季事件与排行榜

### 6.1 开季事件

每次点击“开始赛季”或“开启下一赛季”成功后上报一次。当前游戏排行榜的统计口径为“按球队统计开季次数”，不是胜率或战力排名。

`POST /leaderboards/season-starts/events`

```json
{
  "eventId": "2afdcac9-9b4e-4dc3-853c-34ad16b577e1",
  "seasonNumber": 2,
  "team": "LAL",
  "occurredAt": "2026-07-22T08:02:00Z"
}
```

`eventId` 也是业务唯一键，数据库对 `(application_id, user_application_id, event_id)` 加唯一约束。服务端从 token 取得应用与用户，原子地写入事件并聚合 `team_starts`；重复事件返回首次结果，不得再次增加次数。`seasonNumber` 仅作审计/展示，不参与跨用户排序。

### 6.2 排行榜读取

`GET /leaderboards/season-starts?scope=personal|friends|global&limit=20&cursor=<opaque>`

- `personal`：当前用户按球队分组的开季次数；不读取任何其他用户。
- `friends`：仅在后端已有获授权的好友关系时返回好友及本人；尚未接入时返回空列表和 `friendsAvailable: false`，HTTP 仍为 200。
- `global`：只查询当前应用的聚合记录，绝不能跨 `application_id`。

响应：

```json
{
  "requestId": "req_06",
  "data": {
    "scope": "global",
    "friendsAvailable": true,
    "rows": [
      { "rank": 1, "playerName": "球员 A", "team": "LAL", "starts": 12, "isSelf": false },
      { "rank": 8, "playerName": "我", "team": "LAL", "starts": 2, "isSelf": true }
    ],
    "nextCursor": null,
    "generatedAt": "2026-07-22T08:03:00Z"
  }
}
```

排行规则：按 `starts DESC`，再按最早达到当前次数的时间 `ASC`，最后按稳定的用户 ID `ASC`。昵称、头像若后续允许用户授权更新，必须只修改当前应用下的资料；全服榜只返回展示字段和汇总，不返回 `openid`、内部用户 ID 或其他私密数据。

## 7. 推荐数据模型与索引

|表|关键字段|约束/用途|
|---|---|---|
|`applications`|`id`、`wechat_appid`、`status`、凭据引用|每个小游戏一条；AppSecret 放密钥系统，不入业务表明文|
|`application_users`|`id`、`application_id`、`openid_ciphertext`、`openid_hash`、展示资料|唯一索引 `(application_id, openid_hash)`；同一微信用户在不同应用是不同业务用户|
|`careers`|`application_id`、`user_id`、`revision`、`snapshot_json`、抽取字段|唯一索引 `(application_id, user_id)`；乐观锁 revision|
|`idempotency_records`|`application_id`、`user_id`、`route`、`idempotency_key`、`response_json`、`expires_at`|唯一索引 `(application_id, user_id, route, idempotency_key)`|
|`season_start_events`|`application_id`、`user_id`、`event_id`、`team`、`season_number`、`occurred_at`|唯一索引 `(application_id, user_id, event_id)`|
|`season_start_aggregates`|`application_id`、`user_id`、`team`、`starts`、`first_reached_at`|唯一索引 `(application_id, user_id, team)`；用于榜单查询|
|`asset_manifests`|`application_id`、`group`、`version`、`etag`、`published_at`|同应用、同组、同版本唯一；发布后不可变|
|`asset_files`|`application_id`、`version`、`key`、`storage_key`、`sha256`、尺寸|唯一索引 `(application_id, version, key)`；对象存储路径按应用前缀隔离|

所有含 `application_id` 的主查询、更新、删除条件必须显式带该字段。数据库行级安全可作为第二道防线，但不能替代应用层从 token 注入的租户过滤。

## 8. 缓存、限流与可观测性

|对象|后端响应策略|客户端生命周期策略|
|---|---|---|
|资源 manifest|ETag + `max-age=300`|同页/同组只读一次；版本不变复用|
|版本化图片文件|`max-age=31536000, immutable`|同页复用下载路径和 `Image` 对象；离页释放|
|`/bootstrap`|`private, no-store`|一次登录会话内缓存；回到前台可刷新|
|`/career`|`private, no-store`|启动/登录读取一次；写成功后用返回 revision 更新|
|排行榜|`private, max-age=30` 或 `no-store`|排行榜弹层打开时读取；弹层生命周期内复用|

建议限流：登录按 IP 和 `app_id` 限制；读接口按用户限流；写接口按用户限流且对幂等重试不计为重复业务写入。日志和指标至少包含 `requestId`、`app_id`、路由、状态码、耗时、资源版本、缓存命中、同步冲突和幂等命中；不得记录敏感凭据或完整生涯快照。

当前实现中，登录按 `IP + app_id` 固定窗口限流，默认每 60 秒 20 次，可用 `NBAGAME_LOGIN_RATE_LIMIT` 和 `NBAGAME_LOGIN_RATE_WINDOW_SECONDS` 调整。所有 JSON 写请求默认限制为 2 MB，可用 `NBAGAME_MAX_REQUEST_BYTES` 调整。

## 9. 错误码

|HTTP|错误码|处理建议|
|---|---|---|
|400|`VALIDATION_ERROR`|修正字段；不重试|
|401|`UNAUTHORIZED` / `TOKEN_EXPIRED`|重新登录后重试一次|
|403|`APP_FORBIDDEN`|检查应用状态、token 和资源归属；不降级到其他应用|
|404|`ASSET_NOT_FOUND`|使用包内兜底资源并上报；不循环请求|
|409|`CAREER_CONFLICT`|按第 5.3 节读取云端快照处理冲突|
|429|`RATE_LIMITED`|指数退避，遵从 `Retry-After`|
|500/503|`INTERNAL_ERROR` / `SERVICE_UNAVAILABLE`|保留本地待同步快照，网络恢复后带同一幂等键重试|

## 10. 后端验收清单

- [ ] 两个不同 `app_id` 使用同一微信用户登录后，得到不同 `application_users.id`，且互相不能读写生涯、事件、榜单和资源。
- [ ] `code`、`session_key`、token、明文 `openid` 未出现在日志、错误响应或监控标签中。
- [ ] 同一开季事件和同一同步请求重复提交，不会重复累计或覆盖成不同 revision。
- [ ] 并发写入旧 `If-Match` 会返回 `409 CAREER_CONFLICT`，不会静默丢失数据。
- [ ] 资源 manifest 的 `304`、版本化文件的长期缓存、资源版本升级后的新 URL 均可用；旧页面仍可安全显示已加载资源。
- [ ] `headshot-sprites` 可单独请求，不会被首页或其他 shell 预加载。
- [ ] 删除生涯后，开季历史与排行榜聚合仍保留；仅限当前应用和当前用户的生涯被删除。
- [ ] `personal`、`friends`、`global` 三个范围均不泄露其他应用的数据；好友服务未接入时稳定返回 200 空数据和能力标记。

## 11. 后续前端接入顺序（后端完成后）

1. 在构建配置写入公开 `app_id` 和 API 基础地址，接入 `wx.login` 与会话管理。
2. 增加按页面生命周期管理的 `pageAssetCache`、manifest ETag 和按需头像精灵加载；迁移后再从包内删除对应图片。
3. 在稳定游戏节点调用快照同步，离线失败写本地待同步队列；恢复网络后以原 `Idempotency-Key` 重试。
4. 将开季动作接到开季事件接口，将好友/全服排行榜接到读取接口；名次以服务端返回为准。
5. 完成资源、弱网、冲突和跨应用隔离的联调后，才移除本地存储作为主数据源。
