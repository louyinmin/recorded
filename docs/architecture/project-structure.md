# Project Structure

This repository hosts six product surfaces behind one Flask entrypoint.

## Runtime Entrypoint

- `app.py` stays at the repository root and registers every frontend/static route and backend blueprint.
- Public URLs are intentionally stable. Moving source files under `projects/` must not change existing browser or mini-program API paths.
- Runtime data still belongs under `RECORDED_BASE_DIR`, including databases and uploaded files such as `/assets/uploads/life/...`.

## Product Directories

| Product | Source directory | Public surface |
| --- | --- | --- |
| Life Atlas | `projects/life_atlas/` | `/login.html`, `/life.html`, `/api/life/*` |
| Travel Accounting | `projects/travel_accounting/` | `/travel-login.html`, `/trips.html`, `/trip.html`, `/settings.html`, `/api/trips*`, `/api/records*` |
| Expiry Radar | `projects/expiry_radar/` | `/expiry/*`, `/api/expiry/*` |
| Timing API | `projects/timing_api/` | `/api/timing/*` |
| NBA API | `projects/nba_api/` | `/api/nba/*` |
| Court Deck Mini Game | `projects/nbagame_api/` | `/nbagame/v1/*` |

Shared code and assets live under `projects/shared/`.

## Documentation Directories

| Scope | Documentation directory |
| --- | --- |
| Cross-project architecture | `docs/architecture/` |
| Deployment and operations | `docs/operations/` |
| Life Atlas | `projects/life_atlas/docs/` |
| Travel Accounting | `projects/travel_accounting/docs/` |
| Expiry Radar | `projects/expiry_radar/docs/` |
| Timing API | `projects/timing_api/docs/` |
| NBA API | `projects/nba_api/docs/` |
| Court Deck Mini Game | `projects/nbagame_api/docs/` |
| Shared modules | `projects/shared/docs/` |

## Compatibility Rules

- Root backend packages such as `nba_backend`, `nbagame_backend`, and `expiry_backend` are compatibility entries. Their real implementation files live under `projects/*/backend/`.
- Project-specific frontend assets use stable prefixes:
  - `/life/assets/*`
  - `/travel/assets/*`
  - `/expiry/assets/*`
  - `/shared/assets/*`
- Legacy asset paths such as `/assets/css/style.css` and `/assets/js/common.js` are still resolved by Flask for older cached pages.
- `nginx.conf` falls back to Flask for moved static files, while `/api/*` and Court Deck's isolated `/nbagame/*` continue to proxy to Flask directly.
