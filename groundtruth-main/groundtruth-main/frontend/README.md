# GroundTruth dashboard

Next.js + Tailwind. Reads from the backend's public `/v1/dashboard/*`
endpoints (no API key needed -- these are read-only aggregates, filtered to
never expose live-traffic prompts, only benchmark data and summary stats).

## Run

```
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE_URL at your backend
npm install
npm run dev
```

Open http://localhost:3000. The backend must be running (`uvicorn app.main:app --reload`
from `backend/`) with CORS allowing this origin -- set `FRONTEND_ORIGIN` in the
backend's `.env` if you're not using the default `http://localhost:3000`.

## Deploy

Deploy to Vercel like any Next.js app; set `NEXT_PUBLIC_API_BASE_URL` to your
deployed backend's URL (Render, etc.) in the Vercel project's environment
variables, and set `FRONTEND_ORIGIN` on the backend to your Vercel URL.
