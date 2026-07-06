# NBA API Docs

NBA API owns:

- Backend implementation under `projects/nba_api/backend/nba_backend/`.
- Mini Program API routes under `/api/nba/*`.
- Player card, avatar, team-image, and rookie data contracts.

Documents:

- `api.md` describes the full backend API surface.
- `home-cache-frontend-handoff.md` describes home-page cache behavior.
- `multi-card-miniprogram-handoff.md` describes multi-card player image behavior.
- `rookies-2026-miniprogram-api.md` describes the 2026 rookie API extension.
- `salaryswish-miniprogram-api.md` describes SalarySwish salary-cap collection and read APIs.
- `asset-manifests/` stores NBA rookie asset collection manifests.
- `asset-manifests/current-assets/` stores inventory manifests moved out of runtime image directories.

The root `nba_backend/` package is only a compatibility entry for existing imports.
