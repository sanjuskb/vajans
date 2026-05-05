import React from "react";

interface Props { score: number; size?: number; status: string; }

export default function ScoreRing({ score, size = 96, status }: Props) {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const fill = circ * (1 - score);
  const color = status === "DISQUALIFIED" ? "#dc2626" : score >= 0.7 ? "#16a34a" : "#d97706";

  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={10} />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth={10}
        strokeDasharray={circ}
        strokeDashoffset={fill}
        strokeLinecap="round"
        style={{ transition: "stroke-dashoffset 0.6s ease" }}
      />
      <text
        x="50%" y="50%"
        textAnchor="middle" dominantBaseline="central"
        style={{ fontSize: size * 0.22, fontWeight: 700, fill: color, transform: "rotate(90deg)", transformOrigin: "center", display: "block" }}
        transform={`rotate(90, ${size / 2}, ${size / 2})`}
      >
        {Math.round(score * 100)}%
      </text>
    </svg>
  );
}
