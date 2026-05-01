import axios from "axios";

const client = axios.create({ baseURL: "http://localhost:8000/api" });

export const api = {
  overview: {
    kpis: () => client.get("/overview/kpis").then((r) => r.data),
    dauTrend: () => client.get("/overview/dau-trend").then((r) => r.data),
    engagementBreakdown: () => client.get("/overview/engagement-breakdown").then((r) => r.data),
    topContentTypes: () => client.get("/overview/top-content-types").then((r) => r.data),
  },
  users: {
    segments: () => client.get("/users/segments").then((r) => r.data),
    sessionsByHour: () => client.get("/users/session-by-hour").then((r) => r.data),
    retentionCurve: () => client.get("/users/retention-curve").then((r) => r.data),
    tierBreakdown: () => client.get("/users/tier-breakdown").then((r) => r.data),
  },
  content: {
    languagePerformance: () => client.get("/content/language-performance").then((r) => r.data),
    contentTypes: () => client.get("/content/content-types").then((r) => r.data),
    topCreators: () => client.get("/content/top-creators").then((r) => r.data),
    creatorTiers: () => client.get("/content/creator-tiers").then((r) => r.data),
  },
  monetisation: {
    kpis: () => client.get("/monetisation/kpis").then((r) => r.data),
    arpuByTier: () => client.get("/monetisation/arpu-by-tier").then((r) => r.data),
    revenueTrend: () => client.get("/monetisation/revenue-trend").then((r) => r.data),
    deviceMonetisation: () => client.get("/monetisation/device-monetisation").then((r) => r.data),
  },
  retention: {
    cohortMatrix: () => client.get("/retention/cohort-matrix").then((r) => r.data),
    dayRetention: () => client.get("/retention/day-retention").then((r) => r.data),
  },
  abTest: {
    results: () => client.get("/ab-test/results").then((r) => r.data),
    segmentBreakdown: () => client.get("/ab-test/segment-breakdown").then((r) => r.data),
    dailyTrend: () => client.get("/ab-test/daily-trend").then((r) => r.data),
  },
  language: {
    crossAnalysis: () => client.get("/language/cross-analysis").then((r) => r.data),
    userLanguageMatch: () => client.get("/language/user-language-match").then((r) => r.data),
  },
  query: {
    execute: (sql: string) => client.post("/query/execute", { sql }).then((r) => r.data),
    tables: () => client.get("/query/tables").then((r) => r.data),
    schema: (table: string) => client.get(`/query/schema/${table}`).then((r) => r.data),
  },
};
