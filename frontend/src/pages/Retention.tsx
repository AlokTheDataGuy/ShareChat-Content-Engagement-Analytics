import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

function cellStyle(rate: number): React.CSSProperties {
  if (rate >= 70) return { background: "#FF6B2C", color: "#fff" };
  if (rate >= 50) return { background: "#FF8A57", color: "#fff" };
  if (rate >= 30) return { background: "#FFCDB5", color: "#7c2d12" };
  if (rate >= 15) return { background: "#FFF0EA", color: "#9CA3AF" };
  return { background: "transparent", color: "#d1d5db" };
}

export default function Retention() {
  const cohort = useAPI(api.retention.cohortMatrix);
  const dayRet = useAPI(api.retention.dayRetention);

  if (cohort.error) return <ErrorState message={cohort.error} />;

  const cohortMonths   = [...new Set((cohort.data ?? []).map((r: { cohort_month: string }) => r.cohort_month))].sort() as string[];
  const activityMonths = [...new Set((cohort.data ?? []).map((r: { activity_month: string }) => r.activity_month))].sort() as string[];

  const lookup = new Map<string, number>();
  (cohort.data ?? []).forEach((r: { cohort_month: string; activity_month: string; retention_rate: number }) => {
    lookup.set(`${r.cohort_month}::${r.activity_month}`, r.retention_rate);
  });

  return (
    <PageShell
      title="Retention Analysis"
      subtitle="Cohort-based retention matrix and day-N retention curve"
      description="Retention tells you whether users find enough value to come back. The cohort heatmap shows every acquisition month as a row — reading across reveals how that group retained over time. The day-N curve collapses all cohorts into a single 30-day view."
    >
      <Card title="Day-N Retention Curve (30 days)">
        <p className="text-xs text-text-muted mb-4">
          Each point is the percentage of Day-0 users still active on that day. The curve always starts at 100% and drops — the question is <em>how fast</em>. A sharp cliff at Day 1 means onboarding is failing. Flattening after Day 7 means a habit loop has formed. The "floor" of the curve (where it flattens) is your core engaged user rate.
        </p>
        {dayRet.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={dayRet.data ?? []} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="day_num" tick={TICK_STYLE} tickLine={false}
                label={{ value: "Days since first session", position: "insideBottom", offset: -4, fill: "#9CA3AF", fontSize: 11 }} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v}%`} width={44} domain={[0, 100]} />
              <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`${v}%`, "Retention Rate"]} />
              <Line type="monotone" dataKey="rate" stroke="#FF6B2C" strokeWidth={2.5} dot={false} activeDot={{ r: 5, fill: "#FF6B2C" }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      <Card title="Monthly Cohort Retention Matrix">
        <p className="text-xs text-text-muted mb-4">
          Rows = acquisition month. Columns = calendar month. Each cell shows what % of that cohort was still active. <strong>Reading across a row</strong> shows how a cohort decays. <strong>Reading down a column</strong> shows whether newer cohorts are retaining better than older ones (a sign of product improvement). Orange = strong, white = churned, — = future months not yet reached.
        </p>
        {cohort.loading ? <Spinner /> : (
          <div className="overflow-x-auto">
            <table className="text-xs w-full border-collapse">
              <thead>
                <tr>
                  <th className="text-left text-text-muted font-bold uppercase tracking-wider pb-2 pr-3 w-20 text-[10px]">Cohort</th>
                  {activityMonths.map((m) => (
                    <th key={m} className="text-center text-text-muted font-bold uppercase tracking-wider pb-2 px-1 min-w-[52px] text-[10px]">{m.slice(5)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohortMonths.map((cm) => (
                  <tr key={cm}>
                    <td className="text-text-secondary pr-3 py-0.5 font-semibold">{cm.slice(5)}</td>
                    {activityMonths.map((am) => {
                      const rate = lookup.get(`${cm}::${am}`);
                      return (
                        <td key={am} className="px-1 py-0.5 text-center">
                          {rate !== undefined ? (
                            <span className="inline-block px-1.5 py-0.5 text-[11px] font-semibold" style={cellStyle(rate)}>
                              {rate}%
                            </span>
                          ) : (
                            <span className="text-bg-border">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Insight title="What to act on">
        If a specific cohort row shows significantly worse retention than adjacent rows, trace it back to what changed that month — a product release, a push notification policy change, or a content quality drop. Cohort analysis is most powerful when cross-referenced with the product changelog.
      </Insight>
    </PageShell>
  );
}
