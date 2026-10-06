# GroundTruth

**An LLM monitoring system for detecting hallucinations and tracking model behavior over time.**

AI systems are often evaluated during development and then trusted in production. The problem is that models can change as providers update them, prompts are modified, or configurations evolve. A response can also sound confident while being factually incorrect.

**GroundTruth** addresses both problems. It runs known-answer benchmark questions through an LLM, evaluates the responses, verifies suspicious results with a second AI model, and tracks changes in model behavior across repeated runs.

---

## Architecture

```text
Ask → Score → Verify → Report → Track Drift
```

### 1. Ask

Benchmark questions from **TruthfulQA** are sent through the target LLM. Each request is logged with information such as the prompt, response, token usage, latency, and estimated cost.

### 2. Score

The system compares model responses with known reference answers using embedding-based cosine similarity.

This is intentionally treated as a **heuristic**, not a final accuracy decision. Its purpose is to identify responses that require further investigation.

### 3. Verify

Responses flagged by the scoring stage are passed to a second LLM through a **LangGraph verification workflow**.

The verifier reads the actual response content and determines whether the answer is genuinely incorrect. It also generates a short, plain-English incident report.

### 4. Track Drift

**Population Stability Index (PSI)** is used to compare score distributions between different runs of the same benchmark.

This shifts the focus from simply asking:

> "Is this answer wrong?"

to:

> "Has the model's behavior changed?"

---

## Key Design Decisions

### OpenTelemetry

LLM calls are instrumented using **OpenTelemetry GenAI semantic conventions**, including `gen_ai.*` attributes for model information, tokens, latency, cost, and errors.

This keeps the observability layer compatible with platforms such as Langfuse, Arize Phoenix, and Datadog.

### Supabase / PostgreSQL

Supabase provides the PostgreSQL database used for storing benchmark and monitoring data.

Row Level Security (RLS) is enabled, while raw prompt and response data remains accessible through the backend service key rather than directly through the public database interface.

### Public Dashboard

The project includes a **Next.js dashboard** for displaying monitoring results.

The public-facing endpoints expose aggregate benchmark information and deliberately exclude live-traffic data using the `source='benchmark'` filter. This prevents potentially sensitive user prompts or responses from appearing on a public dashboard.

---

# Results

The monitoring pipeline was tested using `qwen-plus`.

### PSI Drift

Two independent 30-question runs produced:

```text
PSI = 0.0096
```

The very low PSI indicates minimal distribution change between the two runs, which is the expected result when the model's behavior remains stable.

### Hallucination Verification

Approximately **21% of responses initially flagged by the scoring stage were confirmed as genuinely incorrect** after verification.

This demonstrates why the verification stage is important: embedding similarity is useful for identifying suspicious responses, but it should not be treated as the final accuracy decision.

### Reproducible Answer Instability

The system also identified a reproducible example of factual instability.

When repeatedly asked who "the richest person who didn't finish high school" was, the model returned different individuals across runs, including **Richard Branson** and **Amancio Ortega**.

This represents the type of behavioral inconsistency that GroundTruth is designed to surface.

### Verification Failure That Led to an Improvement

During development, an early verification prompt used the labels `confirmed` and `false_positive` without clearly defining what the labels represented.

The model occasionally inverted their intended meaning.

The issue was identified by comparing the verification output against the actual answer content. The workflow was subsequently changed to ask a direct yes/no accuracy question, with the final mapping handled in code rather than relying on the model's choice of label.

---

# Getting Started

## Backend

### 1. Set Up Supabase

Create a Supabase project and execute the SQL files in the `supabase/` directory in order, from:

```text
schema.sql
```

through:

```text
schema_06_cost.sql
```

### 2. Configure Environment Variables

```bash
cd backend
cp .env.example .env
```

Add the required environment variables, including a valid:

```text
GROUNDTRUTH_API_KEY
```

Protected API routes require this key and return `401` when it is missing or invalid.

### 3. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Start the API

```bash
uvicorn app.main:app --reload
```

### 5. Test the API

The `/v1/chat` endpoint requires an API key and is rate-limited to 10 requests per minute per caller.

```bash
curl -X POST localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_KEY" \
  -d '{"prompt": "What is the capital of Nigeria?", "query_type": "geography"}'
```

---

# Monitoring Pipeline

Run the pipeline in the following order:

```bash
python -m scripts.load_benchmark --n 30 --run-id my-run
python -m scripts.embed_calls
python -m scripts.score_hallucination
python -m scripts.run_agents
python -m scripts.psi_drift
python -m scripts.check_alerts
```

The pipeline performs the following tasks:

1. Loads benchmark questions
2. Generates model responses
3. Creates embeddings
4. Scores potential hallucinations
5. Verifies flagged responses
6. Calculates PSI drift
7. Sends alerts when configured thresholds are exceeded

The GitHub Actions workflow in `.github/workflows/monitor.yml` can run the monitoring pipeline automatically each day.

---

# Testing

Run the test suite with:

```bash
cd backend
pytest tests/ -v
```

The tests cover the core PSI drift calculations and hallucination-scoring logic without requiring a network connection or live database.

---

# Dashboard

Start the frontend with:

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

The dashboard is available at:

```text
http://localhost:3000
```

Set `FRONTEND_ORIGIN` in the backend environment configuration to the dashboard's URL so that CORS is configured correctly.

---

# Deployment

GroundTruth can be deployed using **Render** for the backend and **Vercel** for the frontend.

### Backend — Render

1. Push the repository to GitHub.
2. Create a new Render Blueprint.
3. Connect the repository.
4. Render will use the `render.yaml` configuration at the repository root.
5. Configure the required environment variables and secrets.

### Frontend — Vercel

1. Import the same repository into Vercel.
2. Set the root directory to:

```text
frontend
```

3. Configure:

```text
NEXT_PUBLIC_API_BASE_URL
```

using the deployed backend URL.

4. Add the Vercel URL to the backend's `FRONTEND_ORIGIN`.

GitHub Actions can then be configured separately for scheduled monitoring, testing, alerting, and data-retention workflows.

> **Note:** Render's free tier may put the backend to sleep after a period of inactivity. The first request after sleeping can therefore take longer while the service starts again.

---

# Observability

Every LLM request generates an OpenTelemetry span containing information such as:

* Model
* Token usage
* Latency
* Estimated cost
* Errors

By configuring:

```text
OTEL_EXPORTER_OTLP_ENDPOINT
```

the traces can be sent to an OTLP-compatible observability platform such as Langfuse, Arize Phoenix, or Datadog.

---

# Data Retention

Raw prompt and response data is automatically purged after **90 days** through:

```text
scripts/purge_old_calls.py
```

The purge process is scheduled monthly through:

```text
.github/workflows/purge.yml
```

Numerical monitoring data, including hallucination flags and drift snapshots, is retained for long-term trend analysis.

---

# Security

GroundTruth includes several security controls:

* API-key authentication for protected routes
* Rate limiting on the chat endpoint
* Supabase Row Level Security
* Backend-only access to the database service key
* Separation of benchmark and live-traffic data
* Automated data retention and deletion
* Environment-based secret management

API keys should never be committed to the repository.

---

# Current Scope

### Implemented

* LLM call logging
* Benchmark and live source labels
* Embedding-based scoring
* PSI drift detection
* Hallucination scoring
* LangGraph verification workflow
* Incident reporting
* Cost estimation
* OpenTelemetry tracing
* API authentication
* Rate limiting
* Pagination
* Data-retention automation
* CI testing
* Scheduled monitoring
* Alerting
* Monitoring dashboard
* Deployment configuration

### Planned

The current hallucination detection workflow is designed around benchmark questions with known reference answers.

**Retrieval-augmented grounding for live, non-benchmark traffic is not yet implemented.** This is the next major area for extending the system beyond benchmark-based evaluation.

---

## Project Goal

GroundTruth is built around a simple idea:

**LLM applications should be monitored after deployment, not just evaluated before it.**

By combining automated evaluation, secondary verification, drift detection, observability, and reporting, the project provides a practical foundation for understanding how an LLM behaves as it changes over time.

## Author

**Casmir Udeme**

Data Scientist/Analyst | AI/ML | Business Intelligence
