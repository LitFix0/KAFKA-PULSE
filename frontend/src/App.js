import { useState, useEffect } from "react";
import {
  PieChart, Pie, Cell, Tooltip,
  LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Legend
} from "recharts";

const API = "http://localhost:8000";

const COLORS = {
  positive: "#00e5a0",
  negative: "#ff4d6d",
  neutral:  "#5b8dee",
};

// ── Custom tooltip for pie chart ───────────────────────────────────────────────
const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div style={{
      background: "#1a1a2e", border: `1px solid ${COLORS[name] || "#333"}`,
      borderRadius: 8, padding: "8px 14px", color: "#fff", fontSize: 13,
    }}>
      <span style={{ color: COLORS[name], fontWeight: 700 }}>{name}</span>: {value}
    </div>
  );
};

// ── Sentiment badge ────────────────────────────────────────────────────────────
const Badge = ({ sentiment }) => {
  const color = COLORS[sentiment] || "#aaa";
  return (
    <span style={{
      background: color + "22", color, border: `1px solid ${color}44`,
      borderRadius: 4, padding: "2px 8px", fontSize: 11,
      fontWeight: 700, letterSpacing: 1, textTransform: "uppercase",
    }}>
      {sentiment}
    </span>
  );
};

// ── Main App ───────────────────────────────────────────────────────────────────
export default function App() {
  const [stats, setStats]       = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [feed, setFeed]         = useState([]);
  const [tick, setTick]         = useState(0);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 5000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    fetch(`${API}/api/stats`)
      .then(r => r.json())
      .then(setStats)
      .catch(() => {});

    fetch(`${API}/api/timeline?limit=40`)
      .then(r => r.json())
      .then(data => {
        const formatted = data.reverse().map((d, i) => ({
          index: i,
          score: d.score,
          sentiment: d.sentiment,
          time: d.saved_at?.slice(11, 19) || "",
        }));
        setTimeline(formatted);
      })
      .catch(() => {});

    fetch(`${API}/api/recent?limit=15`)
      .then(r => r.json())
      .then(setFeed)
      .catch(() => {});
  }, [tick]);

  // Pie chart data
  const pieData = stats ? [
    { name: "positive", value: stats.positive },
    { name: "negative", value: stats.negative },
    { name: "neutral",  value: stats.neutral  },
  ] : [];

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a1a",
      color: "#e0e0f0",
      fontFamily: "'DM Mono', 'Courier New', monospace",
      padding: "32px 40px",
    }}>

      {/* Google Font */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0a1a; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        .card {
          background: #11112a;
          border: 1px solid #1e1e40;
          border-radius: 12px;
          padding: 24px;
        }
        .card-title {
          font-size: 11px;
          letter-spacing: 2px;
          text-transform: uppercase;
          color: #555580;
          margin-bottom: 16px;
        }
        .feed-item {
          border-bottom: 1px solid #1a1a35;
          padding: 12px 0;
          transition: background 0.2s;
        }
        .feed-item:last-child { border-bottom: none; }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <h1 style={{
          fontFamily: "'Syne', sans-serif",
          fontSize: 36, fontWeight: 800,
          background: "linear-gradient(90deg, #00e5a0, #5b8dee)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          marginBottom: 4,
        }}>
          ⚡ KafkaPulse
        </h1>
        <p style={{ color: "#444466", fontSize: 13 }}>
          Real-time sentiment pipeline · auto-refreshing every 5s
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
        {[
          { label: "Total Analyzed", value: stats?.total ?? "—", color: "#fff" },
          { label: "Positive",       value: stats?.positive ?? "—", color: COLORS.positive },
          { label: "Negative",       value: stats?.negative ?? "—", color: COLORS.negative },
          { label: "Neutral",        value: stats?.neutral  ?? "—", color: COLORS.neutral  },
        ].map(({ label, value, color }) => (
          <div key={label} className="card" style={{ textAlign: "center" }}>
            <div className="card-title">{label}</div>
            <div style={{ fontSize: 38, fontWeight: 700, color, fontFamily: "'Syne', sans-serif" }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 16, marginBottom: 28 }}>

        {/* Pie chart */}
        <div className="card">
          <div className="card-title">Sentiment Distribution</div>
          <PieChart width={240} height={240}>
            <Pie
              data={pieData} cx={110} cy={110}
              innerRadius={65} outerRadius={100}
              paddingAngle={3} dataKey="value"
            >
              {pieData.map(entry => (
                <Cell key={entry.name} fill={COLORS[entry.name]} stroke="none" />
              ))}
            </Pie>
            <Tooltip content={<PieTooltip />} />
          </PieChart>

          {/* Legend */}
          <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 8 }}>
            {pieData.map(({ name }) => (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
                <div style={{ width: 8, height: 8, borderRadius: "50%", background: COLORS[name] }} />
                {name}
              </div>
            ))}
          </div>
        </div>

        {/* Line chart */}
        <div className="card">
          <div className="card-title">Sentiment Score · Timeline</div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={timeline}>
              <CartesianGrid stroke="#1a1a35" strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fill: "#444466", fontSize: 10 }} interval={9} />
              <YAxis domain={[-1, 1]} tick={{ fill: "#444466", fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: "#1a1a2e", border: "1px solid #333", borderRadius: 8 }}
                labelStyle={{ color: "#888" }}
                itemStyle={{ color: "#00e5a0" }}
              />
              <Line
                type="monotone" dataKey="score"
                stroke="#00e5a0" strokeWidth={2}
                dot={false} activeDot={{ r: 4, fill: "#00e5a0" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Live feed */}
      <div className="card">
        <div className="card-title">Live Feed · Latest Articles</div>
        {feed.length === 0 ? (
          <p style={{ color: "#444466", fontSize: 13 }}>No data yet...</p>
        ) : (
          feed.map((item, i) => (
            <div key={i} className="feed-item">
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                <Badge sentiment={item.sentiment} />
                <span style={{ color: "#555580", fontSize: 11 }}>
                  score: <span style={{ color: COLORS[item.sentiment] }}>
                    {item.score > 0 ? "+" : ""}{item.score?.toFixed(3)}
                  </span>
                </span>
                <span style={{ color: "#333355", fontSize: 11, marginLeft: "auto" }}>
                  {item.saved_at?.slice(11, 19)}
                </span>
              </div>
              <p style={{ fontSize: 13, color: "#9090b0", lineHeight: 1.5 }}>
                {item.text?.slice(0, 120)}
              </p>
            </div>
          ))
        )}
      </div>

    </div>
  );
}