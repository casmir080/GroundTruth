"use client";

import { LineChart, Line, XAxis, YAxis, ReferenceLine, Tooltip, ResponsiveContainer } from "recharts";
import type { DriftPoint } from "@/lib/api";

export default function DriftChart({ points }: { points: DriftPoint[] }) {
  if (points.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)]">
        No drift snapshots yet -- run psi_drift.py at least twice to see a trend here.
      </p>
    );
  }

  const data = points.map((p, i) => ({
    index: i + 1,
    psi: p.psi,
    label: `${p.baseline_run} -> ${p.current_run}`,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
        <XAxis
          dataKey="index"
          tick={{ fill: "var(--color-text-muted)", fontFamily: "var(--font-mono)", fontSize: 12 }}
          axisLine={{ stroke: "var(--color-panel-border)" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "var(--color-text-muted)", fontFamily: "var(--font-mono)", fontSize: 12 }}
          axisLine={{ stroke: "var(--color-panel-border)" }}
          tickLine={false}
          tickFormatter={(v: number) => v.toFixed(3)}
          width={48}
        />
        {/* the conventional "significant shift" cutoff, drawn in as a reference */}
        <ReferenceLine y={0.25} stroke="var(--color-rust)" strokeDasharray="4 4" strokeOpacity={0.6} />
        <Tooltip
          contentStyle={{
            background: "var(--color-panel)",
            border: "1px solid var(--color-panel-border)",
            borderRadius: 4,
            fontFamily: "var(--font-mono)",
            fontSize: 12,
          }}
          labelFormatter={() => ""}
          formatter={(value: number, _name, props) => [value.toFixed(4), props.payload.label]}
        />
        <Line
          type="monotone"
          dataKey="psi"
          stroke="var(--color-amber)"
          strokeWidth={2}
          dot={{ r: 3, fill: "var(--color-amber)" }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}