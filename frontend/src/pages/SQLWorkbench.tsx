import { useState } from "react";
import { api } from "../services/api";
import { useAPI } from "../hooks/useAPI";
import { PageShell, Card, Spinner, Insight } from "../components/ui/LoadingState";
import { Play, Table2, ChevronRight } from "lucide-react";

const SAMPLE_QUERIES = [
  { label: "DAU trend",      sql: "SELECT date(session_start) as date, COUNT(DISTINCT user_id) as dau\nFROM fact_sessions\nGROUP BY date\nORDER BY date DESC\nLIMIT 14" },
  { label: "Top languages",  sql: "SELECT c.language, COUNT(*) as events\nFROM fact_engagement_events e\nJOIN dim_content c ON e.post_id = c.post_id\nGROUP BY c.language\nORDER BY events DESC\nLIMIT 10" },
  { label: "ARPU by tier",   sql: "SELECT u.city_tier, ROUND(SUM(a.revenue_inr)/COUNT(DISTINCT a.user_id),2) as arpu\nFROM fact_ad_impressions a\nJOIN dim_users u ON a.user_id = u.user_id\nGROUP BY u.city_tier\nORDER BY u.city_tier" },
  { label: "A/B summary",    sql: "SELECT u.experiment_group, COUNT(DISTINCT s.user_id) as users,\nROUND(AVG(s.session_duration_sec)/60.0,2) as avg_session_min\nFROM fact_sessions s\nJOIN dim_users u ON s.user_id = u.user_id\nWHERE u.experiment_group IN ('control','treatment')\nGROUP BY u.experiment_group" },
];

export default function SQLWorkbench() {
  const [sql, setSql]             = useState(SAMPLE_QUERIES[0].sql);
  const [result, setResult]       = useState<{ rows: Record<string, unknown>[]; count: number } | null>(null);
  const [running, setRunning]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [schema, setSchema]       = useState<Record<string, unknown>[] | null>(null);
  const tables = useAPI(api.query.tables);

  async function run() {
    setRunning(true); setError(null);
    try {
      setResult(await api.query.execute(sql));
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string };
      setError(err?.response?.data?.detail ?? err?.message ?? "Query failed");
      setResult(null);
    } finally { setRunning(false); }
  }

  async function loadSchema(table: string) {
    setSelectedTable(table);
    setSchema(await api.query.schema(table));
  }

  const columns = result?.rows?.[0] ? Object.keys(result.rows[0]) : [];

  return (
    <PageShell
      title="SQL Workbench"
      subtitle="Live read-only queries against the ShareChat SQLite warehouse"
      description="Run ad-hoc SQL directly against the 551 MB warehouse (2.97M rows across 8 tables). All queries are read-only — DROP, DELETE, INSERT, UPDATE and PRAGMA statements are blocked. Use Ctrl+Enter to run. Click any table on the left to inspect its schema."
    >
      <Insight title="Key Tables">
        <strong>fact_sessions</strong> — one row per user session (start time, duration, posts viewed/liked/shared) · <strong>fact_engagement_events</strong> — every like, share, comment, view · <strong>fact_ad_impressions</strong> — ad delivery with revenue and click data · <strong>dim_users</strong> — user profile with city tier, device, experiment group · <strong>dim_content</strong> — post metadata with language and content type · <strong>dim_creators</strong> — creator tier and follower count
      </Insight>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Table browser */}
        <div className="lg:col-span-1 space-y-3">
          <Card title="Tables">
            {tables.loading ? <Spinner /> : (
              <div className="space-y-0.5">
                {(tables.data ?? []).map((t: string) => (
                  <button key={t} onClick={() => loadSchema(t)}
                    className={`w-full text-left px-3 py-2 text-xs font-mono transition-colors flex items-center gap-2
                      ${selectedTable === t
                        ? "bg-brand-dim text-brand font-semibold border-l-2 border-brand pl-[10px]"
                        : "text-text-secondary hover:bg-bg-elevated hover:text-text-primary"}`}>
                    <Table2 size={13} className="shrink-0" />
                    {t}
                  </button>
                ))}
              </div>
            )}
          </Card>

          {schema && selectedTable && (
            <Card title={`Schema · ${selectedTable}`}>
              <div className="space-y-1.5">
                {schema.map((col: Record<string, unknown>) => (
                  <div key={String(col.name)} className="flex items-center justify-between text-xs">
                    <span className="text-text-secondary font-mono">{String(col.name)}</span>
                    <span className="text-text-muted text-[10px] uppercase tracking-wide">{String(col.type)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Editor + results */}
        <div className="lg:col-span-3 space-y-3">
          <div className="flex flex-wrap gap-2">
            {SAMPLE_QUERIES.map((q) => (
              <button key={q.label} onClick={() => setSql(q.sql)}
                className="px-3 py-1.5 text-xs bg-bg-elevated border border-bg-border text-text-secondary hover:text-brand hover:border-brand transition-colors flex items-center gap-1.5 font-medium">
                <ChevronRight size={12} />
                {q.label}
              </button>
            ))}
          </div>

          <div className="border border-bg-border overflow-hidden">
            <div className="bg-bg-elevated px-4 py-2 border-b border-bg-border flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">SQL Editor · Ctrl+Enter to run</span>
              <button onClick={run} disabled={running}
                className="flex items-center gap-2 px-4 py-1.5 bg-brand hover:bg-brand-deep text-white text-xs font-bold uppercase tracking-wide transition-colors disabled:opacity-50">
                <Play size={13} />
                {running ? "Running…" : "Run Query"}
              </button>
            </div>
            <textarea
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              onKeyDown={(e) => { if (e.ctrlKey && e.key === "Enter") run(); }}
              className="w-full bg-white text-text-primary font-mono text-sm p-4 resize-none outline-none h-40"
              spellCheck={false}
              placeholder="SELECT ..."
            />
          </div>

          {error && (
            <div className="border-l-4 border-accent-red bg-red-50 px-4 py-3 text-sm text-accent-red font-mono">
              {error}
            </div>
          )}

          {result && (
            <Card title={`Results — ${result.count.toLocaleString()} row${result.count !== 1 ? "s" : ""} · ${columns.length} column${columns.length !== 1 ? "s" : ""}`}>
              <div className="overflow-x-auto">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-bg-border">
                      {columns.map((col) => (
                        <th key={col} className="text-left px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-text-muted whitespace-nowrap">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr key={i} className="border-b border-bg-border hover:bg-bg-elevated transition-colors">
                        {columns.map((col) => (
                          <td key={col} className="px-3 py-2 text-text-secondary font-mono whitespace-nowrap">
                            {String(row[col] ?? "—")}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      </div>
    </PageShell>
  );
}
