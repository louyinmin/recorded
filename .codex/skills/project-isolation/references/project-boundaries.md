# Recorded Project Boundaries

Use this reference to keep product work isolated.

## Products

| Product | Source directory | Docs | Public surface |
| --- | --- | --- | --- |
| Life Atlas | `projects/life_atlas/` | `projects/life_atlas/docs/` | `/login.html`, `/life.html`, `/api/life/*` |
| Travel Accounting | `projects/travel_accounting/` plus Travel API code in `app.py` | `projects/travel_accounting/docs/` | `/travel-login.html`, `/trips.html`, `/trip.html`, `/settings.html`, `/api/trips*`, `/api/records*`, `/api/payers`, `/api/categories` |
| Expiry Radar | `projects/expiry_radar/` | `projects/expiry_radar/docs/` | `/expiry/*`, `/api/expiry/*` |
| NBA API | `projects/nba_api/` | `projects/nba_api/docs/` | `/api/nba/*` |
| Timing API | `projects/timing_api/` | `projects/timing_api/docs/` | `/api/timing/*` |
| Shared | `projects/shared/` | `projects/shared/docs/` | Shared CSS, WeChat session behavior |

## Root Files

| Path | Role | Isolation rule |
| --- | --- | --- |
| `app.py` | Flask entrypoint, Travel Accounting API, module registration, compatibility static routes | Edit only when route registration, Travel API behavior, or static compatibility requires it. Check all affected products. |
| `home.html` | Unified browser entry page | Edit when changing the system entry or product links. Preserve existing product URLs unless requested. |
| `nginx.conf` | Production static/API routing | Treat as shared. Check browser pages and `/api/*` routing. |
| `requirements.txt` | Shared Python dependencies | Treat as shared. Confirm the dependency is needed by at least one product and does not break tests. |
| `run_server.sh`, `redeploy.sh` | Shared deployment | Treat as shared operations code. Validate script imports and output URLs. |
| `run_expiry_reminder.sh`, `reset_expiry_admin_password.sh`, `setup_expiry_microsoft_oauth2.sh` | Expiry operations scripts with root entrypoints | Prefer keeping scripts at root for operator compatibility, but keep product details documented under `projects/expiry_radar/docs/`. |
| `docs/architecture/` | Cross-project architecture | Do not store product-specific details here unless they explain cross-project coupling. |
| `docs/operations/` | Deployment and operational knowledge | Keep server operation notes here. |

## Compatibility Packages

These root packages preserve old imports. They should stay small:

- `life_backend/`
- `expiry_backend/`
- `nba_backend/`
- `timing_backend/`
- `wechat_backend/`

Real implementations live under `projects/*/backend/`. If implementation code appears in root compatibility packages, move it back under the owning project and keep only import/bootstrap compatibility at root.

## Shared Files

| Path | Consumers | Rule |
| --- | --- | --- |
| `projects/shared/frontend/assets/css/style.css` | Life Atlas login and Travel Accounting pages | Changes may affect both browser products. Check `/login.html` and Travel pages. |
| `projects/shared/backend/wechat_backend/` | NBA API and Timing API | Changes affect `/api/nba/wechat/session`, `/api/timing/wechat/session`, and generic `/api/wechat/session`. |
| `projects/shared/docs/` | Shared modules | Document only shared behavior here. |

## Product Ownership Details

### Life Atlas

- Frontend pages: `projects/life_atlas/frontend/login.html`, `projects/life_atlas/frontend/life.html`.
- Frontend assets: `projects/life_atlas/frontend/assets/`.
- Backend: `projects/life_atlas/backend/life_backend/`.
- Runtime uploads remain under `RECORDED_BASE_DIR/assets/uploads/life/...` and public URL `/assets/uploads/life/...`.
- Avoid changing Travel pages when changing Life Atlas login, even though login uses shared CSS.

### Travel Accounting

- Frontend pages: `projects/travel_accounting/frontend/`.
- Frontend JS: `projects/travel_accounting/frontend/assets/js/`.
- Shared CSS: `projects/shared/frontend/assets/css/style.css`.
- API implementation currently lives in `app.py`; treat Travel API edits as root shared-file edits with a Travel reason.
- Original request docs: `projects/travel_accounting/docs/original-requirements.md`.

### Expiry Radar

- Frontend: `projects/expiry_radar/frontend/`.
- Backend: `projects/expiry_radar/backend/expiry_backend/`.
- Docs: `projects/expiry_radar/docs/`.
- Public URL prefix: `/expiry/`.
- API prefix: `/api/expiry/`.
- Operator scripts remain root-level for deployment compatibility.

### NBA API

- Backend: `projects/nba_api/backend/nba_backend/`.
- Docs and handoffs: `projects/nba_api/docs/`.
- Asset and inventory manifests: `projects/nba_api/docs/asset-manifests/`.
- Runtime image directories remain server-local at `nba_images/`, `nba_avatar/`, and `nba_team_images/`; do not move image files unless the user asks.
- Public API prefix: `/api/nba/`.

### Timing API

- Backend: `projects/timing_api/backend/timing_backend/`.
- Docs: `projects/timing_api/docs/`.
- Public API prefix: `/api/timing/`.
- Uses shared WeChat session backend.

## Public URL Compatibility

Keep these stable unless explicitly changed:

- `/`
- `/home.html`
- `/login.html`
- `/life.html`
- `/travel-login.html`
- `/trips.html`
- `/trip.html`
- `/settings.html`
- `/expiry/`
- `/expiry/login.html`
- `/expiry/dashboard.html`
- `/expiry/settings.html`
- `/expiry/admin-users.html`
- `/life/assets/*`
- `/travel/assets/*`
- `/shared/assets/*`
- `/expiry/assets/*`
- `/assets/uploads/life/*`
- Legacy asset compatibility: `/assets/css/life.css`, `/assets/css/style.css`, `/assets/js/*`, `/assets/img/life-login-hero-left.png`, `/assets/icons/life/*`

## Documentation Placement

- Product feature docs: `projects/<product>/docs/`.
- Cross-project route or structure docs: `docs/architecture/`.
- Deployment, Git, server, and operator instructions: `docs/operations/`.
- NBA handoff and asset JSON: `projects/nba_api/docs/`.
- No root-level `.md` or `.json` knowledge files.
