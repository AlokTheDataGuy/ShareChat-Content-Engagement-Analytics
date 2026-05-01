import {
  BarChart, Bar, Cell, LabelList,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, SC_COLORS, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import KPICard from "../components/ui/KPICard";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

export default function LanguageAnalysis() {
  const cross = useAPI(api.language.crossAnalysis);
  const match = useAPI(api.language.userLanguageMatch);

  if (cross.error) return <ErrorState message={cross.error} />;

  const nativeRate = match.data?.find((r: { match_type: string }) => r.match_type === "Native")?.eng_rate ?? 0;
  const crossRate  = match.data?.find((r: { match_type: string }) => r.match_type === "Cross-Language")?.eng_rate ?? 0;
  const delta      = (nativeRate - crossRate).toFixed(2);

  return (
    <PageShell
      title="Language Analysis"
      subtitle="Cross-language content performance across 15 Indian languages"
      description="ShareChat's differentiation is depth in regional languages. This page tracks engagement quality per language and whether users engage more with native vs cross-language content."
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
        <KPICard label="Languages Tracked"   value={cross.data?.length ?? 0}  sub="Active content languages"     color="orange" />
        <KPICard label="Native Eng. Rate"    value={`${nativeRate}%`}          sub="User's own language content"  color="teal" />
        <KPICard label="Cross-Language Rate" value={`${crossRate}%`}           sub="Content in other languages"   color="green" />
        <KPICard label="Native vs Cross Δ"   value={`+${delta}pp`}             sub="Engagement lift for native"   color="purple" />
      </div>

      {/* Stacked bar — like/share/comment per language */}
      <Card title="Like, Share & Comment Rate by Language">
        <p className="text-xs text-text-muted mb-4">
          Stacked bars show engagement composition. A language with a high <strong>share rate</strong> (teal)
          relative to likes is producing viral content. High <strong>comment rate</strong> (blue) means
          strong community or opinion-driven content — invest moderation there.
        </p>
        {cross.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={cross.data ?? []} margin={{ top: 8, right: 8, left: 0, bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="language" tick={{ ...TICK_STYLE, fontSize: 10 }}
                tickLine={false} axisLine={false} angle={-40} textAnchor="end" interval={0} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${v}%`} width={40} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Legend iconType="circle" iconSize={8}
                formatter={(v) => <span style={{ color: "#9CA3AF", fontSize: 12 }}>{v}</span>} />
              <Bar dataKey="like_rate"    fill="#FF6B2C" name="Like %"    radius={[2, 2, 0, 0]} stackId="a" />
              <Bar dataKey="share_rate"   fill="#10B981" name="Share %"   stackId="a" />
              <Bar dataKey="comment_rate" fill="#00BCD4" name="Comment %" radius={[2, 2, 0, 0]} stackId="a" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      {/* Native vs cross — side-by-side visual comparison */}
      <Card title="Native vs Cross-Language Engagement">
        <p className="text-xs text-text-muted mb-4">
          Native = user consuming content in their signup language. Cross-language = consuming content in
          a different language. A non-zero cross-language rate is healthy — it means users are discovering
          content beyond their language boundary, which drives longer sessions.
        </p>
        {match.loading ? <Spinner /> : (
          <div className="grid grid-cols-2 gap-8 py-4">
            {(match.data ?? []).map((row: { match_type: string; events: number; eng_rate: number }, i: number) => {
              const accent = i === 0 ? "#FF6B2C" : "#9CA3AF";
              const total  = (match.data ?? []).reduce((s: number, r: { events: number }) => s + r.events, 0);
              const share  = total ? Math.round(row.events / total * 100) : 0;
              return (
                <div key={row.match_type} className="space-y-4">
                  <div className="border-b-4 pb-4" style={{ borderColor: accent }}>
                    <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-1">{row.match_type}</div>
                    <div className="text-5xl font-extrabold" style={{ color: accent }}>{row.eng_rate}%</div>
                    <div className="text-sm text-text-muted mt-1">engagement rate</div>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Events</span>
                      <span className="font-semibold text-text-primary">{row.events?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Share of total</span>
                      <span className="font-semibold text-text-primary">{share}%</span>
                    </div>
                  </div>
                  <div className="bg-bg-elevated h-2 w-full rounded-full overflow-hidden">
                    <div className="h-2 rounded-full" style={{ width: `${share}%`, background: accent }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Insight title="Algorithm Implication">
        Native content outperforms cross-language by {delta} percentage points. The feed ranking model
        should weight language match strongly — but not exclusively, since cross-language discovery is how
        users extend their session time and content diet.
      </Insight>
    </PageShell>
  );
}
