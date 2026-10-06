import type { Incident } from "@/lib/api";

const VERDICT_STYLE: Record<Incident["verdict"], { label: string; color: string }> = {
  confirmed: { label: "Confirmed", color: "var(--color-rust)" },
  false_positive: { label: "Cleared", color: "var(--color-sage)" },
  uncertain: { label: "Uncertain", color: "var(--color-text-muted)" },
};

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export default function IncidentsFeed({ incidents }: { incidents: Incident[] }) {
  if (incidents.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No flagged calls yet -- run score_hallucination.py and run_agents.py to populate this feed.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-3 max-h-[420px] overflow-y-auto pr-1">
      {incidents.map((incident, i) => {
        const style = VERDICT_STYLE[incident.verdict];
        return (
          <li key={i} className="border-b border-[var(--color-panel-border)] pb-3 last:border-0">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span
                className="text-xs font-medium px-2 py-0.5 rounded-sm"
                style={{ color: style.color, border: `1px solid ${style.color}` }}
              >
                {style.label}
              </span>
              <span className="text-xs font-mono text-[var(--color-text-muted)]">
                {timeAgo(incident.created_at)}
              </span>
            </div>
            <p className="text-sm text-[var(--color-text)] mb-1">{incident.question}</p>
            <p className="text-sm text-[var(--color-text-muted)]">{incident.report}</p>
          </li>
        );
      })}
    </ul>
  );
}
