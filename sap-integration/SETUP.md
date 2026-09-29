# SAP CPI Integration — Setup & Hosting Guide

This covers how to run the `backend-v2` LIMS and how to expose it so SAP
Integration Suite (CPI) can push inspection lot data into it.

## What's here

- `LIMS_QAS.postman_collection.json` — the original SAP-provided collection
  (kept **local only**, gitignored — it contains a real API key). Ask
  whoever gave you the collection for a fresh copy if you need it.
- `test_connectivity.ps1` / `test_connectivity.py` — one-off scripts that
  read credentials from `.env` in this folder and call the CPI
  `WMS_PlantData` endpoint to confirm your credentials work.
- `.env` (gitignored, create your own) — CPI credentials, never committed.

## 1. Run the app

Backend (`backend-v2`) requires Python 3.11 or 3.12 — Python 3.14 does not
yet have prebuilt wheels for some pinned dependencies (`pydantic-core`,
`greenlet`) and will fail to install without a Rust toolchain.

```powershell
cd backend-v2
py -3.12 -m pip install -r requirements/base.txt
copy .env.example .env   # then fill in real values
py -3.12 -m uvicorn src.main:app --reload --port 8899
```

Frontend (`frontend-react`):

```powershell
cd frontend-react
npm install
npx vite --port 5173
```

Open `http://localhost:5173`. Seeded users: `admin/admin123`,
`analyst/analyst123`, `supervisor/super123`, `qa/qa123`.

### Known dependency pin

`passlib==1.7.4` breaks on `bcrypt>=4.1` (its legacy self-test throws
`ValueError: password cannot be longer than 72 bytes`, surfacing as a 500 on
login). `requirements/base.txt` pins `bcrypt==4.0.1` — keep this pin if you
upgrade other packages.

## 2. The inbound SAP endpoint

`POST /api/v1/sap/inbound/inspection-lot` — this is the target CPI should
push inspection lot data to. It:

- Accepts the exact `inspLotDat` + `inspCharData` JSON shape used by the
  collection's "inspection_lot Download" request, so no CPI payload mapping
  changes are needed — only the target URL and auth header.
- Authenticates via a shared `x-api-key` header (set `SAP_INBOUND_API_KEY`
  in `backend-v2/.env`), not a LIMS user login — CPI has no LIMS account.
- Is **read-only from SAP's perspective**: it stores the lot for analysts to
  review in the LIMS UI and never calls back out to SAP.

`GET /api/v1/sap/inbound/inspection-lot` — lists received lots (requires a
LIMS login as Admin/Analyst/QA), for the app UI to display them.

If `SAP_INBOUND_API_KEY` is left blank, the endpoint accepts unauthenticated
calls and logs a warning on every request — fine for a local smoke test,
**not** fine for anything reachable from the internet.

## 3. Exposing this to SAP CPI

SAP CPI runs in the cloud and cannot reach `localhost`. You need one of:

### Option A — SAP Cloud Connector (recommended for production/real dev use)
If your company already uses Cloud Connector to let CPI reach on-prem SAP
systems, this is the standard, secure pattern: install Cloud Connector on a
machine that can reach wherever `backend-v2` runs, register it against your
CPI subaccount, and point the iFlow at the virtual host Cloud Connector
exposes. Nothing is opened to the public internet. Ask your Basis/CPI admin
team if this is already set up — it may already exist for your other SAP
integrations.

### Option B — Deploy to a reachable server
Deploy `backend-v2` to any server your network (or Cloud Connector) can
reach — a VM, container host, etc. Run it behind a reverse proxy (nginx/
Caddy) with HTTPS, set `SAP_INBOUND_API_KEY` to a strong random value, and
give CPI that URL.

### Option C — Temporary tunnel for a one-off test (ngrok or similar)
Quick way to smoke-test the whole flow before a real deployment exists:

```powershell
winget install ngrok.ngrok
ngrok http 8899
```

This prints a public HTTPS URL (changes every restart on the free tier).
Give CPI `https://<ngrok-id>.ngrok-free.app/api/v1/sap/inbound/inspection-lot`
as the target. **Set `SAP_INBOUND_API_KEY` before doing this** — without it,
the endpoint is open to anyone who finds the URL. Only use this for a short
test window, not as a standing integration.

## 4. Repointing the CPI iFlow

Whichever option you use, the change on the SAP/CPI side is:

1. Open the iFlow that currently targets the "inspection_lot Download"
   (LotRequest) endpoint.
2. Change the HTTP receiver adapter's address to your new URL
   (`.../api/v1/sap/inbound/inspection-lot`).
3. Change the auth from the API-key-in-header style already used, to send
   your `SAP_INBOUND_API_KEY` value as the `x-api-key` header.
4. Leave the request body/mapping untouched — the payload shape matches
   what CPI already sends.

## 5. Verifying it worked

```powershell
curl.exe -s http://<your-url>/api/v1/sap/inbound/inspection-lot `
  -H "Content-Type: application/json" -H "x-api-key: <your key>" `
  -d "@sample_lot_payload.json"
```

Then check it landed, logged in as an Analyst/Admin/QA user:

```powershell
curl.exe -s http://<your-url>/api/v1/sap/inbound/inspection-lot -H "Authorization: Bearer <token>"
```

Or check `/api/v1/sap/logs` for the `INSPECTION_LOT_RECEIVED` audit entry.
