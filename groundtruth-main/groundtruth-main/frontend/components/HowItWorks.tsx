const STEPS = [
  { n: "1", title: "Ask", body: "Test questions with known correct answers are sent to the AI automatically." },
  { n: "2", title: "Score", body: "Each answer is compared to the correct one. Most pass; some get flagged for a closer look." },
  { n: "3", title: "Verify", body: "A second AI reads the flagged answer's actual content, not just the score, and judges it directly." },
  { n: "4", title: "Report", body: "Anything confirmed wrong gets a plain-English note explaining exactly what happened." },
];

export default function HowItWorks() {
  return (
    <ol className="grid sm:grid-cols-4 gap-4">
      {STEPS.map((step, i) => (
        <li key={step.n} className="relative">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-sm text-[var(--color-amber)]">{step.n}</span>
            <span className="text-sm font-medium">{step.title}</span>
          </div>
          <p className="text-sm text-[var(--color-text-muted)]">{step.body}</p>
          {i < STEPS.length - 1 && (
            <span className="hidden sm:block absolute top-1 -right-2 text-[var(--color-panel-border)]">
              →
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
