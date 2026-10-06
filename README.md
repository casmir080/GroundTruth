GroundTruth

An LLM output monitor that catches two things most teams don't watch for: when a model's answers quietly drift over time, and when it states something false with total confidence.

Most AI products get evaluated once, then trusted indefinitely. But the model behind them keeps changing -- provider updates, prompt tweaks -- and a confidently wrong answer looks identical to a correct one unless something is actually checking. GroundTruth runs known-answer questions through an LLM on a schedule, scores each response for factual grounding, verifies anything suspicious with a second AI reading the actual content (not just a similarity score), and tracks whether the model's behavior is shifting between runs.

Architecture
Ask  ->  Score  ->  Verify  ->  Report  ->  Track drift
Stage	What it does	Why this way
Ask	Sends benchmark questions (TruthfulQA) through the model, logs every call -- prompt, response, tokens, latency, cost -- to Postgres.	TruthfulQA is built from questions people commonly get wrong, so it actually exercises the failure mode this tool exists to catch, not just easy trivia.
Score	Embeds the response and compares it against known correct/incorrect reference answers (cosine similarity).	Cheap and fast enough to run on every call. Explicitly a heuristic -- flags likely problems, isn't a verdict on its own.
Verify	A second LLM call (LangGraph: verify -> synthesize) reads the flagged answer's actual content and judges it directly, then writes a one-sentence plain-English incident note.	The similarity heuristic has real false positives (a correct answer can embed oddly). A second pass that reads content, not scores, catches those -- see Results below for a case where it mattered.
Track drift	PSI (Population Stability Index) compares the distribution of scores between two runs of the same questions. Same technique used on an earlier project, Watchtower, applied here to LLM output instead of tabular ML features.	Answers the actual question this tool is for: not "is this answer wrong" but "has behavior changed."
Other choices worth explaining:

OpenTelemetry GenAI semantic conventions for tracing every call (gen_ai.* attributes) instead of a custom logging format -- these traces would work with Langfuse, Arize Phoenix, or Datadog without writing per-backend integration code.
Supabase/Postgres for storage, with RLS on and no anon policies -- the raw prompt/response data is only ever readable via the backend's service key, never directly.
A public dashboard (Next.js) reads from separate, deliberately unauthenticated aggregate endpoints that exclude live-traffic data by a hard filter (source='benchmark') -- a public status page showing someone's real prompt would be a privacy problem the moment live traffic starts flowing through this.
Results
From running this against qwen-plus:

PSI = 0.0096 comparing two independent 30-question runs of the same model, same day -- correctly near zero, which is what should happen when nothing has actually changed. That's the pipeline validating itself before it's trusted to flag something real.
~21% of flagged answers were confirmed genuinely wrong after the verify stage, on questions deliberately built from common misconceptions -- consistent with what TruthfulQA is designed to surface, not a sign of an unstable model.
A real, reproducible catch: asked repeatedly who "the richest person who didn't finish high school" is, the model gave different named individuals (Richard Branson in some runs, Amancio Ortega in others) -- genuine answer instability on a specific fact, exactly the kind of thing drift-checking is meant to surface, not just wording changes.
The verifier caught its own mistake being made. An early version of the verify prompt asked the model to answer with the word confirmed or false_positive without specifying what was being confirmed -- and the model quietly inverted its meaning, labeling accurate answers as hallucinations and a real wrong answer as fine. Caught by checking actual output content against the labels, not by trusting the labels. Fixed by asking a plain yes/no accuracy question instead and mapping the result in code, not in the model's word choice.
Run it
Backend:

Supabase: create a project, run every file in supabase/ in order (schema.sql through schema_06_cost.sql) in the SQL Editor.
cd backend && cp .env.example .env and fill in the values, including a real GROUNDTRUTH_API_KEY -- without one, every protected route returns 401 by design.
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload
Try it (note the X-API-Key header, and that /v1/chat is rate-limited to 10/minute per caller):
curl -X POST localhost:8000/v1/chat \
  -H "Content-Type: application/json" -H "X-API-Key: YOUR_KEY" \
  -d '{"prompt": "What is the capital of Nigeria?", "query_type": "geography"}'
Pipeline (run in order):

python -m scripts.load_benchmark --n 30 --run-id my-run
python -m scripts.embed_calls
python -m scripts.score_hallucination
python -m scripts.run_agents        # verify + write plain-English incident reports
python -m scripts.psi_drift         # compares the two most recent runs if no args given
python -m scripts.check_alerts      # posts to Slack if drift or flag rate is over threshold
.github/workflows/monitor.yml runs this whole sequence daily via GitHub Actions -- add SUPABASE_URL, SUPABASE_SERVICE_KEY, DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, and optionally SLACK_WEBHOOK_URL as repo secrets to enable it. .github/workflows/ci.yml runs the test suite on every push (no secrets needed). .github/workflows/purge.yml runs the retention purge monthly.

Tests:

cd backend && pytest tests/ -v
Covers the drift (PSI) and hallucination-scoring math in isolation (app/drift.py, app/hallucination.py) -- no network or database needed.

Dashboard:

cd frontend
cp .env.local.example .env.local
npm install
npm run dev
Open http://localhost:3000. Set FRONTEND_ORIGIN in the backend's .env to match wherever the dashboard is running (CORS).

Deploy
Push this repo to GitHub (Render and Vercel both deploy from a connected repo).
Backend, on Render: dashboard -> New -> Blueprint -> connect the repo. Render reads render.yaml at the repo root automatically. You'll be prompted for the sync: false secrets -- leave FRONTEND_ORIGIN blank for now.
Frontend, on Vercel: dashboard -> Add New -> Project -> import the same repo. Set Root Directory to frontend. Add NEXT_PUBLIC_API_BASE_URL = your Render backend's URL.
Back on Render, set FRONTEND_ORIGIN to your new Vercel URL, so CORS allows the deployed dashboard to reach the API.
For the scheduled workflows: add the same secrets as GitHub repo secrets (Settings -> Secrets and variables -> Actions) -- separate from Render's and Vercel's env vars.
Render's free tier sleeps after 15 minutes of inactivity; the first request after that takes 30-60 seconds to wake back up. That's expected -- the dashboard's "unreachable" state is exactly what handles that gracefully.

Observability
Every LLM call emits an OpenTelemetry span (gen_ai.* attributes: model, tokens, latency, cost, errors). Spans print to the console by default; set OTEL_EXPORTER_OTLP_ENDPOINT to send them to Langfuse, Phoenix, Datadog, or any other OTLP-compatible backend instead.

Data retention
Raw prompt/response text is purged after 90 days (scripts/purge_old_calls.py, monthly via .github/workflows/purge.yml). Numeric scores (hallucination flags, drift snapshots) are kept indefinitely so trend charts still work after the raw text is gone.

Security notes
Rotate DASHSCOPE_API_KEY if it's ever appeared in a terminal session shared outside your own machine.
GROUNDTRUTH_API_KEY gates every route except /, /health, and /docs. Treat it like a password.
Supabase tables use the service key from the backend only; RLS is on with no policies, so the anon key can't read anything even if it leaked.
What's real vs. stubbed
Real: call logging, live/benchmark source labels, embedding-based drift (PSI), hallucination-score heuristic, LangGraph verify+synthesize agent pipeline, cost estimation, OTel tracing, API auth, rate limiting, pagination past 1000 rows, data retention purge, CI, scheduled runs, alerting, the dashboard, deploy config.

Not yet built: retrieval-augmented grounding for live (non-benchmark) traffic -- the hallucination check currently relies on TruthfulQA's reference answers, which only exist for benchmark questions.
