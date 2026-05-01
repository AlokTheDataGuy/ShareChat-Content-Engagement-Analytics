import {
  BarChart, Bar, Cell, LabelList,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Spinner, ErrorState, PageShell, Card, Insight, SC_COLORS, TOOLTIP_STYLE, TICK_STYLE } from "../components/ui/LoadingState";
import KPICard from "../components/ui/KPICard";
import { useAPI } from "../hooks/useAPI";
import { api } from "../services/api";

export default function ContentPerformance() {
  const langPerf     = useAPI(api.content.languagePerformance);
  const contentTypes = useAPI(api.content.contentTypes);
  const creatorTiers = useAPI(api.content.creatorTiers);

  if (langPerf.error) return <ErrorState message={langPerf.error} />;

  const top          = langPerf.data?.[0];
  const maxLikeRate  = Math.max(...(langPerf.data?.map((r: { like_rate: number }) => r.like_rate) ?? [0]));

  return (
    <PageShell
      title="Content Performance"
      subtitle="Language reach, content type metrics, and creator ecosystem"
      description="ShareChat's core moat is regional-language content. This page tracks which languages and formats drive the most engagement, and how concentrated engagement is across the creator base."
    >
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-0 border-l border-t border-bg-border">
        <KPICard label="Top Language"      value={top?.language ?? "—"}           sub={`${top?.total_events?.toLocaleString()} events`} color="orange" />
        <KPICard label="Languages Active"  value={langPerf.data?.length ?? 0}     sub="Languages with ≥1 event"                       color="teal" />
        <KPICard label="Highest Like Rate" value={`${maxLikeRate}%`}              sub="Best performing language"                      color="green" />
        <KPICard label="Content Types"     value={contentTypes.data?.length ?? 0} sub="Distinct content formats"                      color="purple" />
      </div>

      {/* Language bars — each language its own color */}
      <Card title="Event Volume by Language">
        <p className="text-xs text-text-muted mb-4">
          Total engagement events per language. Hindi dominates by volume, but watch the per-bar colors
          to spot smaller languages with disproportionate engagement — those are the ones worth investing creator budgets in.
        </p>
        {langPerf.loading ? <Spinner /> : (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={langPerf.data ?? []} margin={{ top: 24, right: 8, left: 0, bottom: 36 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
              <XAxis dataKey="language" tick={{ ...TICK_STYLE, fontSize: 10 }}
                tickLine={false} axisLine={false} angle={-35} textAnchor="end" interval={0} />
              <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} width={44} />
              <Tooltip contentStyle={TOOLTIP_STYLE}
                formatter={(v: number) => [v.toLocaleString(), "Events"]} />
              <Bar dataKey="total_events" radius={[5, 5, 0, 0]} name="Total Events">
                {(langPerf.data ?? []).map((_: unknown, i: number) => (
                  <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                ))}
                <LabelList dataKey="total_events" position="top"
                  formatter={(v: number) => `${(v / 1000).toFixed(0)}K`}
                  style={{ fontSize: 10, fontWeight: 700, fill: "#374151" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Content format engagement — colored horizontal bars with labels */}
        <Card title="Engagement Rate by Content Format">
          <p className="text-xs text-text-muted mb-4">
            Which formats get users to actually react. Higher engagement rate = more feed real estate
            and creator support should flow to this format.
          </p>
          {contentTypes.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={contentTypes.data ?? []} layout="vertical"
                margin={{ top: 4, right: 60, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
                <XAxis type="number" tick={TICK_STYLE} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `${v}%`} />
                <YAxis dataKey="content_type" type="category" tick={TICK_STYLE}
                  tickLine={false} axisLine={false} width={72} />
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number) => [`${v}%`, "Eng. Rate"]} />
                <Bar dataKey="eng_rate" radius={[0, 5, 5, 0]} name="Eng. Rate %">
                  {(contentTypes.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <LabelList dataKey="eng_rate" position="right"
                    formatter={(v: number) => `${v}%`}
                    style={{ fontSize: 11, fontWeight: 700, fill: "#374151" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Creator tiers — colored bar chart */}
        <Card title="Total Engagement by Creator Tier">
          <p className="text-xs text-text-muted mb-4">
            If top-tier creators account for &gt;40% of total engagement, the platform has creator
            concentration risk. A healthy distribution shows mid-tier creators contributing meaningfully.
          </p>
          {creatorTiers.loading ? <Spinner /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={creatorTiers.data ?? []} margin={{ top: 24, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" vertical={false} />
                <XAxis dataKey="creator_tier" tick={TICK_STYLE} tickLine={false} axisLine={false} />
                <YAxis tick={TICK_STYLE} tickLine={false} axisLine={false}
                  tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`} width={44} />
                <Tooltip contentStyle={TOOLTIP_STYLE}
                  formatter={(v: number, name: string) => [
                    name === "total_events" ? v.toLocaleString() : `${v}%`,
                    name === "total_events" ? "Total Events" : "Avg Eng. Rate",
                  ]} />
                <Bar dataKey="total_events" radius={[6, 6, 0, 0]} name="total_events">
                  {(creatorTiers.data ?? []).map((_: unknown, i: number) => (
                    <Cell key={i} fill={SC_COLORS[i % SC_COLORS.length]} />
                  ))}
                  <LabelList dataKey="total_events" position="top"
                    formatter={(v: number) => `${(v / 1000).toFixed(0)}K`}
                    style={{ fontSize: 11, fontWeight: 700, fill: "#374151" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      <Insight title="Content Strategy Signal">
        High-engagement formats and regional languages with above-average like rates are where creator incentive
        budgets should be concentrated. Volume alone (total events) is misleading — a language with 10% of the
        events but double the engagement rate is more valuable per post.
      </Insight>
    </PageShell>
  );
}
