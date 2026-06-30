---
name: project-isolation
description: Use when changing the Recorded repository so work stays inside the correct product boundary. Trigger for any task that edits, reviews, moves, documents, tests, or reasons about files under projects/, app.py, docs/, root compatibility packages, frontend assets, Flask routes, nginx routing, deployment scripts, or project-specific knowledge files. Helps separate Life Atlas, Travel Accounting, Expiry Radar, Timing API, NBA API, and shared files without breaking public URLs or shared runtime behavior.
---

# Project Isolation

Use this skill before modifying this repository. The goal is simple: change the target product, identify shared surfaces explicitly, and avoid accidental cross-project regressions.

## Required Workflow

1. Identify the product named by the user or implied by the touched files.
2. Read `references/project-boundaries.md` before editing if the task touches more than one product, any shared file, public URL routing, docs, deployment, or compatibility packages.
3. Keep product-specific code, assets, and docs inside that product's `projects/<product>/` directory whenever possible.
4. Treat root files as coordination surfaces. Editing them requires checking every affected product route or import.
5. Preserve public URLs unless the user explicitly asks to change them. Internal source paths may move; browser and Mini Program API paths must remain stable.
6. Validate the narrow product path plus any shared path you touched.

## Isolation Rules

- Put product knowledge beside the product in `projects/<product>/docs/`.
- Put cross-project knowledge in `docs/architecture/` or `docs/operations/`.
- Do not create root-level `.md` or `.json` knowledge files.
- Do not put product-specific frontend assets in root `assets/`; use the product's `frontend/assets/`.
- Do not put generated inventory or handoff JSON in runtime image folders; archive knowledge JSON under the owning product docs.
- Do not edit shared code to solve a product-only problem unless the shared behavior is the root cause.
- When editing shared code, list every consumer and run checks for each affected consumer.

## Shared Surface Checklist

Read `references/project-boundaries.md` and complete this checklist before editing shared surfaces:

- `app.py`: route mapping, public URL compatibility, Travel Accounting API, Flask static serving.
- `nginx.conf`: production routing for all browser pages and `/api/*`.
- Root compatibility packages: import preservation for scripts, tests, and external commands.
- `projects/shared/`: shared frontend CSS and shared WeChat session backend.
- Deployment scripts: install, redeploy, reminders, password reset, OAuth setup.
- `docs/`: cross-project documentation only.

## Validation

Use the smallest validation that proves the changed boundary still works.

- Python syntax: `uv run python -m py_compile $(fd -H -e py . | rg -v '^venv/')`
- Backend regression: `uv run python -m unittest discover -s tests`
- Route/static changes: use Flask test client smoke checks for old public URLs and new internal asset prefixes.
- Frontend projects: do not run dev/build/start/serve commands in this repository; verify by code review, static route checks, and relevant tests.

## Reporting

Report:

- Which product was changed.
- Which shared files were touched and why.
- Which public URLs or API prefixes were preserved.
- Which validations passed.
