import React from "react";
import { Medal } from "lucide-react";
import BidderBarChart from "../charts/BidderBarChart";
import type { ComparisonResponse } from "../../services/types";

interface Props { comparison: ComparisonResponse; }

const rankColor = (rank: number) =>
  rank === 1 ? "#f59e0b" : rank === 2 ? "#94a3b8" : rank === 3 ? "#cd7f32" : "#e2e8f0";

export default function ComparisonTable({ comparison }: Props) {
  if (comparison.bidders.length === 0) {
    return (
      <div style={{ textAlign: "center", color: "#94a3b8", padding: 32 }}>
        No bidder data available
      </div>
    );
  }

  return (
    <div>
      {/* Chart — overflow guard prevents layout break on zoom */}
      {comparison.bidders.length > 0 && (
        <div style={{ marginBottom: 20, width: "100%", minWidth: 0, overflow: "hidden" }}>
          <BidderBarChart bidders={comparison.bidders} />
        </div>
      )}

      {/* Rankings table */}
      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
              {["Rank", "Bidder", "Score", "Pass", "Fail", "Unknown", "Total"].map((h) => (
                <th key={h} style={{ padding: "11px 16px", textAlign: "left", fontSize: 12, fontWeight: 600, color: "#64748b" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparison.rankings.map((r) => {
              const bidder = comparison.bidders.find(
                (b) => b.bidder_id === r.bidder_id && b.bidder_name === r.bidder_name
              );
              return (
                <tr key={r.rank} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: "50%",
                      background: rankColor(r.rank),
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, fontWeight: 700,
                      color: r.rank <= 3 ? "#fff" : "#64748b",
                    }}>
                      {r.rank <= 3 ? <Medal size={14} /> : r.rank}
                    </div>
                  </td>
                  <td style={{ padding: "12px 16px", fontWeight: 600, color: "#0f172a", fontSize: 14 }}>
                    {r.bidder_name || "Unassigned"}
                  </td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{
                        height: 6, width: 80, background: "#e2e8f0", borderRadius: 3, overflow: "hidden",
                      }}>
                        <div style={{
                          height: "100%", width: `${r.total_score * 100}%`,
                          background: "#1e40af", borderRadius: 3,
                          transition: "width 0.5s ease",
                        }} />
                      </div>
                      <span style={{ fontSize: 13, fontWeight: 700, color: "#0f172a" }}>
                        {(r.total_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: "12px 16px", color: "#16a34a", fontWeight: 700 }}>{bidder?.pass ?? "—"}</td>
                  <td style={{ padding: "12px 16px", color: "#dc2626", fontWeight: 700 }}>{bidder?.fail ?? "—"}</td>
                  <td style={{ padding: "12px 16px", color: "#d97706", fontWeight: 700 }}>{bidder?.unknown ?? "—"}</td>
                  <td style={{ padding: "12px 16px", color: "#64748b" }}>{bidder?.total_criteria ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
