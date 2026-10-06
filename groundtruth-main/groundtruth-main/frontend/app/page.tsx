import DriftChart from "@/components/DriftChart";
import IncidentsFeed from "@/components/IncidentsFeed";
import HowItWorks from "@/components/HowItWorks";
import { getSummary, getDriftHistory, getIncidents } from "@/lib/api";

function StatCard({
  label,
  value,
  caption,
  accent,
}: {
  label: string;
  value: string;
  caption: string;
  accent?: string;
}) {
  return (
    <div className="border border-[var(--color-panel-border)] bg-[var(--color-panel)] p-4 rounded-sm">
      <p className="text-sm text-[var(--color-text-muted)] mb-1">{label}</p>
      <p className="text-2xl font-mono mb-1" style={{ color: accent ?? "var(--color-text)" }}>
        {value}
      </p>
      <p className="text-xs text-[var(--color-text-muted)] leading-snug">{caption}</p>
    </div>
  );
}

export default async function Dashboard() {
  const [summary, driftHistory, incidents] = await Promise.all([
    getSummary(),
    getDriftHistory(),
    getIncidents(),
  ]);

  const reachable = summary !== null;
  const stable = summary?.status?.level === "stable";
  const driftLabel = summary?.drift?.label;
  const driftColor =
    driftLabel === "significant"
      ? "var(--color-rust)"
      : driftLabel === "moderate"
        ? "var(--color-amber)"
        : "var(--color-sage)";

  return (
    <main className="max-w-5xl mx-auto px-6 py-10">
      <header className="flex items-center justify-between mb-8 pb-4 border-b border-[var(--color-panel-border)]">
        <div>
          <h1 className="text-xl font-medium">GroundTruth</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Drift and hallucination monitor for an LLM application
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm font-mono">
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ background: reachable ? "var(--color-sage)" : "var(--color-rust)" }}
          />
          <span className="text-[var(--color-text-muted)]">
            {reachable ? "reachable" : "unreachable"}
          </span>
        </div>
      </header>

      {!reachable ? (
        <p className="text-sm text-[var(--color-text-muted)]">
          Can&apos;t reach the API right now. Check that the backend is running and
          NEXT_PUBLIC_API_BASE_URL points at it.
        </p>
      ) : (
        <>
          {/* The story starts here, before any numbers: what this is and why. */}
          <section className="mb-8">
            <p className="text-base leading-relaxed max-w-3xl">
              Most AI products never notice when their model starts quietly getting
              things wrong. It doesn&apos;t crash or error, it just answers confidently,
              the same way it answers everything else. <span className="text-[var(--color-text)] font-medium">GroundTruth</span> watches
              for that: when an AI&apos;s answers to the same questions start changing over
              time (<span className="text-[var(--color-text-muted)]">drift</span>), and when it states something false with total
              confidence (<span className="text-[var(--color-text-muted)]">hallucination</span>).
            </p>
          </section>

          <section className="mb-10">
            <h2 className="text-sm text-[var(--color-text-muted)] mb-4">How it works</h2>
            <HowItWorks />
          </section>

          {/* The headline verdict -- one honest sentence, before the supporting detail. */}
          <section className="mb-6">
            <div
              className="border p-5 rounded-sm flex items-center justify-between"
              style={{
                borderColor: stable ? "var(--color-sage)" : "var(--color-rust)",
                background: "var(--color-panel)",
              }}
            >
              <div>
                <p className="text-xs text-[var(--color-text-muted)] mb-1">Current status</p>
                <p
                  className="text-2xl font-medium"
                  style={{ color: stable ? "var(--color-sage)" : "var(--color-rust)" }}
                >
                  {summary!.status.label}
                </p>
              </div>
              <p className="text-sm text-[var(--color-text-muted)] max-w-sm text-right">
                {stable
                  ? "The AI's answers aren't shifting over time. Some flagged answers are still confirmed wrong below -- expected for deliberately tricky test questions -- but that rate isn't changing."
                  : "The AI's answers are measurably different from an earlier baseline -- worth a look at what changed."}
              </p>
            </div>
          </section>

          <section className="mb-3">
            <h2 className="text-sm text-[var(--color-text-muted)]">The evidence behind that verdict</h2>
          </section>

          <section className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Total calls"
              value={String(summary!.total_calls)}
              caption="How many times this system has queried the AI so far."
            />
            <StatCard
              label={`Heuristic flags (n=${summary!.flag_rate_sample_size})`}
              value={summary!.flag_rate !== null ? `${(summary!.flag_rate * 100).toFixed(0)}%` : "--"}
              caption="A fast first-pass check flagged these for a closer look. Most turn out fine -- that's expected."
            />
            <StatCard
              label={`Confirmed after review (n=${summary!.reviewed_count})`}
              value={summary!.confirmed_rate !== null ? `${(summary!.confirmed_rate * 100).toFixed(0)}%` : "--"}
              accent={summary!.confirmed_rate !== null ? "var(--color-rust)" : undefined}
              caption="Of the flagged answers, this share were confirmed genuinely wrong. These test questions are deliberately tricky (common misconceptions), so this is expected to be above zero -- it's the trend over time that matters, not this number alone."
            />
            <StatCard
              label="Cost so far"
              value={`$${summary!.total_cost_usd.toFixed(4)}`}
              caption="Running total of what these checks have cost in AI API usage."
            />
          </section>

          <section className="grid md:grid-cols-2 gap-6">
            <div className="border border-[var(--color-panel-border)] bg-[var(--color-panel)] p-4 rounded-sm">
              <h2 className="text-sm mb-1">Is it staying consistent over time?</h2>
              <p className="text-xs text-[var(--color-text-muted)] mb-3">
                Each point compares two batches of answers to the same questions. Flat and
                near zero means the AI is being consistent; a rising line means its answers
                are changing.
              </p>
              <DriftChart points={driftHistory ?? []} />
            </div>
            <div className="border border-[var(--color-panel-border)] bg-[var(--color-panel)] p-4 rounded-sm">
              <h2 className="text-sm mb-1">What has it actually caught?</h2>
              <p className="text-xs text-[var(--color-text-muted)] mb-3">
                Real answers this system checked -- what was asked, whether it held up, and why.
              </p>
              <IncidentsFeed incidents={incidents ?? []} />
            </div>
          </section>
        </>
      )}
    </main>
  );
}