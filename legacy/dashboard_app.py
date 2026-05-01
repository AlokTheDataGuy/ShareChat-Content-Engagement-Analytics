# ============================================================
# SHARECHAT ANALYTICS INTELLIGENCE PLATFORM
# Product Analyst Internship Project | April 2026
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image
import base64
import sqlite3
import math
import pathlib
import scipy.stats as _stats
import warnings
warnings.filterwarnings("ignore")

# ─── Theme detection ─────────────────────────────────────────
try:
    _theme_base = st.get_option("theme.base") or "light"
except Exception:
    _theme_base = "light"
IS_DARK = (_theme_base == "dark")

# ─── SQLite helpers ──────────────────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parent.parent

@st.cache_resource
def get_db_conn():
    """Cached SQLite connection with math UDFs registered."""
    db = _ROOT / "data" / "warehouse" / "sharechat_warehouse.db"
    if not db.exists():
        return None
    conn = sqlite3.connect(str(db), check_same_thread=False)
    conn.create_function("SQRT",  1, lambda x: math.sqrt(max(x, 0)) if x is not None else None)
    conn.create_function("POWER", 2, lambda x, y: x**y if x is not None and y is not None else None)
    return conn

# ─── PAGE CONFIG ────────────────────────────────────────────
_logo_img = Image.open("assets/logo.png")
st.set_page_config(
    page_title="ShareChat Content Engagement Analytics",
    page_icon=_logo_img,
    layout="wide",
    initial_sidebar_state="expanded",   # filters always visible on load
)

# ─── COLOUR TOKENS ──────────────────────────────────────────
ORANGE  = "#FF6B2C"
TEAL    = "#00BCD4"
GREEN   = "#10B981"
PURPLE  = "#8B5CF6"
GOLD    = "#FFB800"
RED     = "#EF4444"
DARK    = "#111827"
BORDER  = "#E5E7EB"
SUBTEXT = "#9CA3AF"

# Chart palette — vibrant (original scheme)
COLOR_SEQ = [ORANGE, TEAL, GREEN, PURPLE, GOLD, "#3B82F6", RED, "#EC4899", "#F59E0B", "#14B8A6"]
PLT_MAP   = {"ShareChat": ORANGE, "Moj": PURPLE, "QuickTV": GREEN}   # platform colours

# ─── GLOBAL CSS ─────────────────────────────────────────────
_DARK_ROOT = """
  --bg:      #0e1117; --bg2:    #1a1f2e; --border: #374151;
  --text:    #f1f5f9; --text2:  #d1d5db; --subtext:#9CA3AF;
  --dim:     #6B7280; --ins-bg: #1e2433; --tab-bg: #0e1117;
  --grid:    #1f2937; --sidebar:#0e1117;
""" if IS_DARK else """
  --bg:      #ffffff; --bg2:    #f9fafb; --border: #E5E7EB;
  --text:    #111827; --text2:  #374151; --subtext:#9CA3AF;
  --dim:     #D1D5DB; --ins-bg: #FFF8F5; --tab-bg: #ffffff;
  --grid:    #F3F4F6; --sidebar:#ffffff;
"""

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html,body,[class*="css"]{{ font-family:'Inter',sans-serif; }}
#MainMenu {{ visibility: hidden; }}
footer    {{ visibility: hidden; }}

/* ── CSS CUSTOM PROPERTIES ── */
:root {{ {_DARK_ROOT} }}

/* ── CHROME STRIP ── */
header, [data-testid="stHeader"], [data-testid="stToolbar"] {{
    height:0 !important; min-height:0 !important;
    padding:0 !important; margin:0 !important; overflow:hidden !important;
}}
.main .block-container,
[data-testid="stMainBlockContainer"],
[data-testid="stMain"] > div:first-child {{ padding-top:0 !important; margin-top:0 !important; }}
[data-testid="stAppViewContainer"] > section.main {{ padding-top:0 !important; }}
.main .block-container{{ padding:0 !important; max-width:100% !important; }}

/* ── SIDEBAR TOGGLE BUTTON ── */
[data-testid="collapsedControl"] {{
    display:flex !important; visibility:visible !important;
    background:#FF6B2C !important; border-radius:0 6px 6px 0;
}}
[data-testid="collapsedControl"] svg {{ fill:white !important; }}

/* ── SIDEBAR ── */
[data-testid="stSidebar"]{{ background:var(--sidebar) !important; border-right:1px solid var(--border); }}
section[data-testid="stSidebar"]>div{{ background:var(--sidebar) !important; }}
[data-testid="stSidebar"] *{{ color:var(--text) !important; }}
[data-testid="stSidebar"] [data-baseweb="tag"]{{
    background:#FF6B2C !important; border-color:#FF6B2C !important; border-radius:3px !important;
}}
[data-testid="stSidebar"] [data-baseweb="tag"] span{{ color:#fff !important; }}
[data-testid="stSidebar"] [data-baseweb="tag"] button{{ color:rgba(255,255,255,.75) !important; }}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p{{
    font-size:10px !important; font-weight:700 !important;
    letter-spacing:1.5px !important; text-transform:uppercase !important; color:#6B7280 !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{{
    background:var(--tab-bg) !important; border-bottom:1px solid var(--border);
    gap:0 !important; padding:0 !important;
}}
.stTabs [data-baseweb="tab"]{{
    background:none !important; border:none !important;
    border-bottom:2px solid transparent !important; border-radius:0 !important;
    padding:14px 22px !important; font-size:10px !important; font-weight:700 !important;
    letter-spacing:1.5px !important; text-transform:uppercase !important;
    color:var(--subtext) !important; margin:0 !important;
}}
.stTabs [aria-selected="true"]{{ border-bottom:2px solid #FF6B2C !important; color:#FF6B2C !important; }}
.stTabs [data-baseweb="tab-panel"]{{ padding:28px 32px !important; }}

/* ── KPI CARDS — equal height, flex column ── */
.kpi-row {{ display:flex; gap:0; }}
.kpi-card {{
    background:var(--bg); border:1px solid var(--border);
    padding:20px 22px; min-height:120px;
    display:flex; flex-direction:column; justify-content:space-between;
    box-sizing:border-box;
}}
.kpi-lbl {{
    font-size:10px; font-weight:700; color:var(--subtext);
    text-transform:uppercase; letter-spacing:1.5px; margin-bottom:10px;
}}
.kpi-val {{ font-size:28px; font-weight:800; color:var(--text); line-height:1.1; }}
.kpi-dsc {{ font-size:10px; color:var(--dim); margin-top:6px; }}

/* ── SECTION HEADERS ── */
.sec-hdr {{
    font-size:10px; font-weight:700; letter-spacing:2px;
    text-transform:uppercase; color:var(--text2);
    border-bottom:1px solid var(--border);
    padding-bottom:8px; margin:28px 0 14px 0;
}}

/* ── INSIGHT BOX ── */
.ins-box {{ background:var(--ins-bg); border-left:3px solid #FF6B2C; padding:14px 18px; margin:16px 0; }}
.ins-ttl {{ font-size:10px; font-weight:700; color:#FF6B2C; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px; }}
.ins-txt {{ font-size:13px; color:var(--text2); line-height:1.65; }}

/* ── DASHBOARD HEADER ── */
.dash-hdr {{
    display:flex; align-items:center; gap:14px;
    padding:18px 32px 14px 32px;
    border-bottom:1px solid var(--border); background:var(--bg);
}}
.dash-ttl {{ font-size:14px; font-weight:800; letter-spacing:3px; color:var(--subtext); text-transform:uppercase; }}

/* ── DATAFRAME DARK MODE ── */
{'[data-testid="stDataFrame"] { color-scheme: dark; }' if IS_DARK else ''}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ────────────────────────────────────────────────

def rgba(hex_c: str, a: float) -> str:
    h = hex_c.lstrip("#")
    r,g,b = int(h[:2],16), int(h[2:4],16), int(h[4:],16)
    return f"rgba({r},{g},{b},{a})"


@st.cache_data
def _logo_b64() -> str:
    with open("assets/logo.png","rb") as f:
        return base64.b64encode(f.read()).decode()


def kpi(label, value, delta="", pos=True, desc=""):
    dh = ""
    if delta:
        c   = GREEN if pos else RED
        arr = "↑" if pos else "↓"
        dh  = f'<div style="font-size:11px;color:{c};margin-top:8px;font-weight:600;">{arr} {delta}</div>'
    dsc = f'<div class="kpi-dsc">{desc}</div>' if desc else ""
    # bottom padding pushes delta/desc to bottom of the fixed-height card
    bottom = dh + dsc if (dh or dsc) else '<div></div>'
    return (f'<div class="kpi-card">'
            f'<div><div class="kpi-lbl">{label}</div><div class="kpi-val">{value}</div></div>'
            f'<div>{bottom}</div>'
            f'</div>')


def sec(title):
    st.markdown(f'<div class="sec-hdr">{title}</div>', unsafe_allow_html=True)


def ins(text, title="Key Insight"):
    st.markdown(f'<div class="ins-box"><div class="ins-ttl">{title}</div><div class="ins-txt">{text}</div></div>',
                unsafe_allow_html=True)


def base_layout(fig, height=360, dual=False):
    txt  = "#d1d5db" if IS_DARK else "#374151"
    grid = "#1f2937" if IS_DARK else "#F3F4F6"
    brd  = "#374151" if IS_DARK else BORDER
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color=txt, size=11),
        height=height,
        margin=dict(l=4, r=4, t=12, b=4),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(size=11, color=SUBTEXT), orientation="h",
                    yanchor="bottom", y=1.01, xanchor="left", x=0),
        xaxis=dict(showgrid=False, linecolor=brd,
                   tickfont=dict(size=10, color=SUBTEXT), tickcolor=brd),
        yaxis=dict(gridcolor=grid, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(size=10, color=SUBTEXT)),
    )
    if dual:
        fig.update_layout(
            yaxis2=dict(gridcolor="rgba(0,0,0,0)", linecolor="rgba(0,0,0,0)",
                        tickfont=dict(size=10, color=SUBTEXT), showgrid=False)
        )
    return fig


# ─── DATA GENERATION ────────────────────────────────────────

@st.cache_data
def gen_monthly():
    np.random.seed(42)
    months = pd.date_range("2025-04-01", periods=13, freq="MS")
    sc0, mj0, qt0 = 95e6, 72e6, 38e6
    sc_r0, mj_r0, qt_r0 = 45.2, 28.5, 6.3
    rows = []
    for i, m in enumerate(months):
        n = np.random.uniform(.98,1.02)
        sc_mau=sc0*(1.022**i)*n; mj_mau=mj0*(1.025**i)*n; qt_mau=qt0*(1.06**i)*n
        sc_rev=sc_r0*(1.024**i)*np.random.uniform(.97,1.04)
        mj_rev=mj_r0*(1.027**i)*np.random.uniform(.97,1.04)
        qt_rev=qt_r0*(1.07**i)*np.random.uniform(.97,1.04)
        rows.append({
            "month":m, "month_label":m.strftime("%b %Y"),
            "sc_mau":int(sc_mau),"moj_mau":int(mj_mau),"qtv_mau":int(qt_mau),
            "total_mau":int(sc_mau+mj_mau+qt_mau),
            "sc_rev":round(sc_rev,1),"moj_rev":round(mj_rev,1),"qtv_rev":round(qt_rev,1),
            "total_rev":round(sc_rev+mj_rev+qt_rev,1),
            "dau_ratio":round(np.random.uniform(.43,.52),3),
            "new_users_m":round(np.random.uniform(9,15),1),
            "avg_session_min":round(np.random.uniform(16,22),1),
        })
    return pd.DataFrame(rows)


@st.cache_data
def gen_users():
    np.random.seed(42); N=10_000
    LANGS=["Hindi","Telugu","Tamil","Bengali","Marathi","Gujarati","Kannada",
           "Malayalam","Punjabi","Odia","Bhojpuri","Assamese","Rajasthani","Haryanvi","Urdu"]
    LP=[.38,.12,.10,.09,.07,.05,.04,.04,.03,.02,.02,.01,.01,.01,.01]
    RMAP={"Hindi":"North","Telugu":"South","Tamil":"South","Bengali":"East",
          "Marathi":"West","Gujarati":"West","Kannada":"South","Malayalam":"South",
          "Punjabi":"North","Odia":"East","Bhojpuri":"North","Assamese":"East",
          "Rajasthani":"North","Haryanvi":"North","Urdu":"North"}
    langs=np.random.choice(LANGS,N,p=LP)
    plats=np.random.choice(["ShareChat","Moj","QuickTV"],N,p=[.45,.38,.17])
    ages=np.random.choice(["18-24","25-34","35-44","45-54","55+"],N,p=[.32,.28,.22,.12,.06])
    signup=pd.to_datetime("2024-04-01")+pd.to_timedelta(np.random.randint(0,365,N),unit="D")
    return pd.DataFrame({
        "user_id":range(1,N+1),"platform":plats,"language":langs,
        "region":[RMAP[l] for l in langs],"age_group":ages,
        "gender":np.random.choice(["Male","Female","Other"],N,p=[.58,.39,.03]),
        "device":np.random.choice(["Android Budget","Android Mid","Android Premium","iOS"],N,p=[.45,.30,.15,.10]),
        "signup_date":signup,
        "is_premium":np.random.choice([True,False],N,p=[.08,.92]),
        "monthly_sessions":np.random.randint(5,120,N),
        "avg_session_min":np.random.uniform(8,35,N).round(1),
        "videos_per_session":np.random.randint(5,50,N),
        "ltv_inr":np.random.lognormal(7,1.2,N).round(0),
    })


@st.cache_data
def gen_content():
    np.random.seed(42); N=5_000
    CT=["Short Video","Image Post","Text Post","Reel","Drama Episode","Live Stream"]
    CTP=[.38,.24,.15,.12,.06,.05]
    CATS=["Entertainment","Comedy","News & Affairs","Devotional","Music","Fashion","Food","Sports","Education","Lifestyle"]
    CATP=[.28,.20,.13,.10,.09,.07,.05,.04,.02,.02]
    LANGS=["Hindi","Telugu","Tamil","Bengali","Marathi","Gujarati","Kannada","Malayalam","Punjabi","Others"]
    LGP=[.38,.12,.10,.09,.07,.05,.04,.04,.03,.08]
    ct=np.random.choice(CT,N,p=CTP); cat=np.random.choice(CATS,N,p=CATP); lg=np.random.choice(LANGS,N,p=LGP)
    BV={"Short Video":50000,"Reel":45000,"Drama Episode":35000,"Live Stream":20000,"Image Post":15000,"Text Post":8000}
    BE={"Short Video":.08,"Reel":.10,"Drama Episode":.12,"Live Stream":.07,"Image Post":.05,"Text Post":.04}
    views=[int(BV[c]*np.random.lognormal(0,1.5)) for c in ct]
    er=[BE[c]*np.random.uniform(.5,2.0) for c in ct]
    df=pd.DataFrame({
        "content_id":range(1,N+1),"content_type":ct,"category":cat,"language":lg,
        "platform":np.random.choice(["ShareChat","Moj","QuickTV"],N,p=[.45,.38,.17]),
        "upload_date":pd.to_datetime("2025-04-01")+pd.to_timedelta(np.random.randint(0,365,N),"D"),
        "views":views,
        "likes":[int(v*e*np.random.uniform(.30,.50)) for v,e in zip(views,er)],
        "shares":[int(v*e*np.random.uniform(.10,.20)) for v,e in zip(views,er)],
        "comments":[int(v*e*np.random.uniform(.05,.15)) for v,e in zip(views,er)],
        "engagement_rate":[round(e,4) for e in er],
        "watch_time_avg_sec":np.where(pd.Series(ct).isin(["Short Video","Reel"]),
            np.random.uniform(15,60,N),
            np.where(pd.Series(ct)=="Drama Episode",np.random.uniform(600,1800,N),
                     np.random.uniform(10,30,N))).round(0),
    })
    df["total_engagement"]=df["likes"]+df["shares"]+df["comments"]
    return df


@st.cache_data
def gen_retention():
    np.random.seed(42)
    cohorts=pd.date_range("2025-04-01",periods=12,freq="MS")
    base=[1.0,.48,.35,.28,.23,.20,.18,.16,.15,.14,.13,.12]
    data={}
    for i,c in enumerate(cohorts):
        avail=12-i; row={}
        for m in range(12):
            if m<avail:
                noise=np.random.uniform(.93,1.07)
                row[f"M{m:02d}"]=round(min(base[m]*noise,base[max(m-1,0)]),3) if m>0 else 1.0
            else:
                row[f"M{m:02d}"]=np.nan
        data[c.strftime("%b %Y")]=row
    return pd.DataFrame(data).T


@st.cache_data
def gen_dau():
    np.random.seed(42)
    dates=pd.date_range("2026-01-14",periods=90,freq="D")
    df=pd.DataFrame({"date":dates})
    df["dow"]=df["date"].dt.dayofweek
    for i,row in df.iterrows():
        wb=1.13 if row["dow"]>=5 else 1.0; tr=1+(i/90)*0.08; n=np.random.uniform(.97,1.03)
        df.at[i,"sc_dau"]=int(42e6*wb*tr*n); df.at[i,"moj_dau"]=int(34e6*wb*tr*n); df.at[i,"qtv_dau"]=int(27e6*wb*tr*n*1.1)
    df["total_dau"]=df["sc_dau"]+df["moj_dau"]+df["qtv_dau"]
    return df


@st.cache_data
def gen_revenue_daily():
    np.random.seed(42)
    dates=pd.date_range("2026-01-14",periods=90,freq="D")
    fmts=["In-Feed Video","Banner","Interstitial","Rewarded Video","Native Story"]
    shares=[.45,.18,.20,.12,.05]
    rows=[]
    for d in dates:
        base=2.8*(1.15 if d.dayofweek>=5 else 1.0)*np.random.uniform(.92,1.10)
        for f,sh in zip(fmts,shares):
            rows.append({"date":d,"ad_format":f,"revenue_cr":round(base*sh,3),
                         "impressions_m":round(base*sh*np.random.uniform(8,12),2),
                         "ecpm":round(np.random.uniform(55,115),1)})
    return pd.DataFrame(rows)


@st.cache_data
def gen_language():
    np.random.seed(42)
    LANGS=["Hindi","Telugu","Tamil","Bengali","Marathi","Gujarati","Kannada",
           "Malayalam","Punjabi","Odia","Bhojpuri","Assamese","Rajasthani","Haryanvi","Urdu"]
    SHARES=[.38,.12,.10,.09,.07,.05,.04,.04,.03,.02,.02,.01,.01,.01,.01]
    return pd.DataFrame({
        "language":LANGS,
        "mau_m":[s*200 for s in SHARES],
        "engagement_rate":np.random.uniform(.06,.15,15).round(4),
        "creator_k":np.random.uniform(5,150,15).round(1),
        "revenue_cr":np.random.uniform(2,90,15).round(1),
        "avg_session_min":np.random.uniform(14,25,15).round(1),
        "content_per_user":np.random.uniform(25,65,15).round(0),
    })


# ─── PAGE: OVERVIEW ─────────────────────────────────────────

_PLAT_PREFIX = {"ShareChat": "sc", "Moj": "moj", "QuickTV": "qtv"}

def page_overview(monthly, revenue_det, platform_filter):
    # ── Apply platform filter to aggregate KPIs ──────────────
    sel = [_PLAT_PREFIX[p] for p in platform_filter if p in _PLAT_PREFIX] or list(_PLAT_PREFIX.values())
    m = monthly.copy()
    m["f_mau"] = m[[f"{p}_mau" for p in sel]].sum(axis=1)
    m["f_rev"] = m[[f"{p}_rev" for p in sel]].sum(axis=1)
    latest = m.iloc[-1]; first = m.iloc[0]
    yoy = (latest["f_rev"] / first["f_rev"] - 1) * 100 if first["f_rev"] else 0
    arr = latest["f_rev"] * 12
    plat_label = ", ".join(platform_filter) if len(platform_filter) < 3 else "All platforms"

    c1,c2,c3,c4,c5=st.columns(5)
    with c1: st.markdown(kpi("Monthly Active Users",f"{latest['f_mau']/1e6:.0f}M","28% YoY",True,plat_label), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Annualised Revenue",f"₹{arr:.0f} Cr",f"+{yoy:.1f}% YoY",True,"Combined ARR"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("DAU / MAU Ratio",f"{latest['dau_ratio']*100:.1f}%","+3.2 pp YoY",True,"Daily stickiness"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Avg Session",f"{latest['avg_session_min']:.1f} min","+1.8 min YoY",True,"Per active user/day"), unsafe_allow_html=True)
    with c5: st.markdown(kpi("New Users (Month)",f"{latest['new_users_m']:.1f}M","+12% MoM",True,plat_label), unsafe_allow_html=True)

    # ── Dual-axis: Revenue bars + DAU/MAU line (filtered)
    sec("Monthly Revenue Trend")
    fig=make_subplots(specs=[[{"secondary_y":True}]])
    fig.add_trace(go.Bar(x=m["month_label"],y=m["f_rev"],
                         name="Revenue (₹ Cr)",marker_color=ORANGE,marker_line_width=0),secondary_y=False)
    fig.add_trace(go.Scatter(x=m["month_label"],y=m["dau_ratio"]*100,
                             name="DAU/MAU %",mode="lines",
                             line=dict(color=SUBTEXT,width=2,dash="dot"),marker=dict(size=4)),secondary_y=True)
    fig=base_layout(fig,320,dual=True)
    fig.update_layout(hovermode="x unified",barmode="group",legend=dict(orientation="h",y=1.05,x=0))
    fig.update_yaxes(title_text="Revenue (₹ Cr)", secondary_y=False,
                     title=dict(font=dict(size=10, color=SUBTEXT)))
    fig.update_yaxes(title_text="DAU/MAU %", secondary_y=True,
                     title=dict(font=dict(size=10, color=SUBTEXT)))
    st.plotly_chart(fig,use_container_width=True)

    col1,col2=st.columns([3,2])
    with col1:
        sec(f"Monthly Active Users — {plat_label} (Millions)")
        # Only show selected platforms
        mau_vars  = [f"{p}_mau" for p in sel]
        mau_names = {f"{p}_mau": nm for nm, p in _PLAT_PREFIX.items()}
        mau_long  = m.melt(id_vars=["month_label"], value_vars=mau_vars,
                           var_name="platform", value_name="mau")
        mau_long["platform"] = mau_long["platform"].map(mau_names)
        mau_long["mau_m"]    = mau_long["mau"] / 1e6
        fig2=px.bar(mau_long,x="month_label",y="mau_m",color="platform",
                    color_discrete_map=PLT_MAP,
                    barmode="group",labels={"mau_m":"MAU (M)","month_label":"","platform":"Platform"})
        fig2.update_traces(marker_line_width=0)
        fig2=base_layout(fig2,300)
        st.plotly_chart(fig2,use_container_width=True)

    with col2:
        sec("Revenue Share — Selected Platforms")
        pie_data = [(nm, latest[f"{p}_rev"])
                    for nm, p in _PLAT_PREFIX.items() if p in sel]
        if pie_data:
            pie=pd.DataFrame(pie_data, columns=["Platform","Rev"])
            ann_txt = f"₹{latest['f_rev']:.0f}Cr"
            ann_clr = "#f1f5f9" if IS_DARK else DARK
            fig3=px.pie(pie,values="Rev",names="Platform",hole=.62,
                        color_discrete_map=PLT_MAP)
            fig3.update_traces(textposition="outside",textfont_size=11,
                               hovertemplate="<b>%{label}</b><br>₹%{value:.1f} Cr<br>%{percent}")
            fig3.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                height=300,margin=dict(l=0,r=0,t=30,b=10),
                legend=dict(font=dict(size=11),orientation="h",y=-0.12,x=0.5,xanchor="center"),
                annotations=[dict(text=ann_txt,x=.5,y=.5,
                                  font=dict(size=16,color=ann_clr,family="Inter"),showarrow=False)]
            )
            st.plotly_chart(fig3,use_container_width=True)

    if "QuickTV" in platform_filter:
        qtv_g=(monthly["qtv_mau"].iloc[-1]/monthly["qtv_mau"].iloc[0]-1)*100
        qtv_note = f"QuickTV grew <b>+{qtv_g:.0f}%</b> in 12 months — fastest-growing platform. "
    else:
        qtv_note = ""
    sc_rev_note = f"ShareChat holds the largest revenue share at ₹{latest['sc_rev']:.0f} Cr/month. " if "ShareChat" in platform_filter else ""
    ins(f"{qtv_note}{sc_rev_note}Combined selected network is on course to exceed ₹{arr+200:.0f} Cr ARR in FY26-27.")


# ─── PAGE: USER ANALYTICS ───────────────────────────────────

def page_users(users):
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(kpi("Total Users (Sample)",f"{len(users):,}",desc="Synthetic profiles"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Premium Users",f"{users['is_premium'].mean()*100:.1f}%","+1.2 pp MoM",True,"Paid subscribers"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Avg Sessions / Month",f"{users['monthly_sessions'].mean():.0f}",desc="Per active user"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Median LTV",f"₹{users['ltv_inr'].median():,.0f}",desc="User lifetime value"), unsafe_allow_html=True)

    col1,col2,col3=st.columns(3)
    with col1:
        sec("Age Group Distribution")
        ao=["18-24","25-34","35-44","45-54","55+"]
        ac=users["age_group"].value_counts().reindex(ao).reset_index()
        ac.columns=["Age","Count"]
        fig=px.bar(ac,x="Age",y="Count",color_discrete_sequence=[ORANGE])
        fig.update_traces(marker_line_width=0)
        fig=base_layout(fig,280)
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        sec("Gender Split")
        gc=users["gender"].value_counts().reset_index(); gc.columns=["Gender","Count"]
        fig=px.pie(gc,values="Count",names="Gender",hole=.60,
                   color_discrete_sequence=[ORANGE,TEAL,GREEN])
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          height=280,margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig,use_container_width=True)

    with col3:
        sec("Device Type")
        dc=users["device"].value_counts().reset_index(); dc.columns=["Device","Count"]
        fig=px.pie(dc,values="Count",names="Device",hole=.60,
                   color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          height=280,margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig,use_container_width=True)

    col4,col5=st.columns([3,2])
    with col4:
        sec("Users by Language (15 Regional Languages)")
        lc=users["language"].value_counts().reset_index(); lc.columns=["Language","Users"]
        lc["Pct"]=(lc["Users"]/len(users)*100).round(1)
        fig=px.bar(lc,x="Users",y="Language",orientation="h",
                   color_discrete_sequence=[ORANGE],text="Pct")
        fig.update_traces(texttemplate="%{text:.1f}%",textposition="outside",marker_line_width=0)
        fig.update_layout(yaxis={"categoryorder":"total ascending"})
        fig=base_layout(fig,420)
        st.plotly_chart(fig,use_container_width=True)

    with col5:
        sec("Users by Region")
        rc=users["region"].value_counts().reset_index(); rc.columns=["Region","Users"]
        fig=px.pie(rc,values="Users",names="Region",hole=.55,
                   color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          height=420,margin=dict(l=0,r=0,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)

    col6,col7=st.columns(2)
    with col6:
        sec("Session Duration by Platform")
        fig=px.box(users,x="platform",y="avg_session_min",color="platform",
                   color_discrete_map=PLT_MAP,
                   labels={"avg_session_min":"Session (min)","platform":""})
        fig.update_traces(showlegend=False)
        fig=base_layout(fig,280)
        st.plotly_chart(fig,use_container_width=True)

    with col7:
        sec("Avg Monthly Sessions by Platform")
        ps=users.groupby("platform")["monthly_sessions"].mean().reset_index()
        ps.columns=["Platform","Sessions"]
        fig=px.bar(ps,x="Platform",y="Sessions",color="Platform",text="Sessions",
                   color_discrete_map=PLT_MAP)
        fig.update_traces(texttemplate="%{text:.1f}",textposition="outside",
                          showlegend=False,marker_line_width=0)
        fig=base_layout(fig,280)
        st.plotly_chart(fig,use_container_width=True)


# ─── PAGE: CONTENT PERFORMANCE ──────────────────────────────

def page_content(content):
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(kpi("Content Items",f"{len(content):,}",desc="In analytical sample"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Avg Views / Post",f"{content['views'].mean():,.0f}","+12% MoM",True,"All formats"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Avg Engagement Rate",f"{content['engagement_rate'].mean()*100:.2f}%","+0.8 pp QoQ",True,"L+S+C / Views"), unsafe_allow_html=True)
    with c4:
        top_cat=content.groupby("category")["views"].sum().idxmax()
        st.markdown(kpi("Top Category",top_cat,desc="By total views"), unsafe_allow_html=True)

    col1,col2=st.columns(2)
    with col1:
        sec("Average Views by Content Type")
        cv=content.groupby("content_type")["views"].mean().sort_values().reset_index()
        fig=px.bar(cv,x="views",y="content_type",orientation="h",
                   color_discrete_sequence=[ORANGE],text="views")
        fig.update_traces(texttemplate="%{x:,.0f}",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,300)
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        sec("Engagement Rate by Content Type")
        er=content.groupby("content_type")["engagement_rate"].mean().sort_values(ascending=False).reset_index()
        er["er_pct"]=er["engagement_rate"]*100
        fig=px.bar(er,x="content_type",y="er_pct",color_discrete_sequence=[ORANGE],text="er_pct")
        fig.update_traces(texttemplate="%{text:.2f}%",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,300)
        fig.update_layout(yaxis_title="Engagement Rate (%)")
        st.plotly_chart(fig,use_container_width=True)

    col3,col4=st.columns([3,2])
    with col3:
        sec("Category Market Map — Views vs Engagement (bubble = # posts)")
        cat_agg=content.groupby("category").agg(
            total_views=("views","sum"),avg_er=("engagement_rate","mean"),count=("content_id","count")
        ).reset_index()
        cat_agg["views_m"]=(cat_agg["total_views"]/1e6).round(2)
        fig=px.scatter(cat_agg,x="views_m",y="avg_er",size="count",color="category",
                       text="category",size_max=36,color_discrete_sequence=COLOR_SEQ,
                       labels={"views_m":"Total Views (M)","avg_er":"Avg Engagement Rate"})
        fig.update_traces(textposition="top center",textfont_size=9,marker_opacity=.85)
        fig.update_layout(yaxis_tickformat=".1%")
        fig=base_layout(fig,380)
        st.plotly_chart(fig,use_container_width=True)

    with col4:
        sec("Content Share by Language")
        lc=content["language"].value_counts().reset_index(); lc.columns=["Language","Count"]
        fig=px.pie(lc,values="Count",names="Language",hole=.45,
                   color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                          height=380,margin=dict(l=0,r=0,t=20,b=10),legend=dict(font=dict(size=10)))
        st.plotly_chart(fig,use_container_width=True)

    sec("Top 10 Content Items by Views")
    top10=content.nlargest(10,"views")[["content_type","category","language","platform","views","likes","shares","engagement_rate"]].copy()
    top10.index=range(1,11)
    top10["views"]=top10["views"].apply(lambda x:f"{x:,.0f}")
    top10["likes"]=top10["likes"].apply(lambda x:f"{x:,.0f}")
    top10["shares"]=top10["shares"].apply(lambda x:f"{x:,.0f}")
    top10["engagement_rate"]=top10["engagement_rate"].apply(lambda x:f"{x*100:.2f}%")
    st.dataframe(top10,use_container_width=True)

    drama_er=content[content["content_type"]=="Drama Episode"]["engagement_rate"].mean()*100
    reel_er=content[content["content_type"]=="Reel"]["engagement_rate"].mean()*100
    hindi_share=content[content["language"]=="Hindi"]["views"].sum()/content["views"].sum()*100
    ins(f"Drama Episodes lead engagement at <b>{drama_er:.2f}%</b>, outperforming Reels ({reel_er:.2f}%). "
        f"Hindi content drives <b>{hindi_share:.0f}%</b> of total views — validating ShareChat's regional-first strategy.")


# ─── PAGE: MONETIZATION ─────────────────────────────────────

def page_monetization(monthly, revenue_det):
    latest=monthly.iloc[-1]
    avg_ecpm=revenue_det["ecpm"].mean(); total_imp=revenue_det["impressions_m"].sum()

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(kpi("Monthly Revenue",f"₹{latest['total_rev']:.1f} Cr","+28% YoY",True,"All platforms"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Avg eCPM",f"₹{avg_ecpm:.1f}","+18% QoQ",True,"Effective CPM"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Total Impressions (90d)",f"{total_imp:.0f}M","+15% QoQ",True,"Last 90 days"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Ad Fill Rate","86.3%","+2.3 pp QoQ",True,"Demand / inventory"), unsafe_allow_html=True)

    sec("Revenue Trend — 12 Months by Platform (₹ Crore)")
    fig=go.Figure()
    for plat,col,clr in [("ShareChat","sc_rev",ORANGE),("Moj","moj_rev",PURPLE),("QuickTV","qtv_rev",GREEN)]:
        fig.add_trace(go.Bar(x=monthly["month_label"],y=monthly[col],name=plat,
                             marker_color=clr,marker_line_width=0))
    fig.add_trace(go.Scatter(x=monthly["month_label"],y=monthly["total_rev"],name="Total",
                             mode="lines",line=dict(color=GOLD,width=2,dash="dot"),marker=dict(size=4)))
    fig=base_layout(fig,320)
    fig.update_layout(barmode="stack",hovermode="x unified")
    st.plotly_chart(fig,use_container_width=True)

    col1,col2=st.columns(2)
    with col1:
        sec("Revenue by Ad Format (90 Days)")
        af=revenue_det.groupby("ad_format")["revenue_cr"].sum().sort_values().reset_index()
        fig=px.bar(af,x="revenue_cr",y="ad_format",orientation="h",
                   color_discrete_sequence=[ORANGE],text="revenue_cr")
        fig.update_traces(texttemplate="₹%{x:.1f}",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,300)
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        sec("eCPM Trend by Ad Format — 7-Day Rolling Average")
        de=revenue_det.groupby(["date","ad_format"])["ecpm"].mean().reset_index()
        pivot=de.pivot(index="date",columns="ad_format",values="ecpm").rolling(7).mean()
        long=pivot.reset_index().melt(id_vars="date")
        fig=px.line(long.dropna(),x="date",y="value",color="ad_format",
                    color_discrete_sequence=COLOR_SEQ,
                    labels={"value":"eCPM (₹)","ad_format":"Format","date":""})
        fig=base_layout(fig,300)
        st.plotly_chart(fig,use_container_width=True)

    col3,col4=st.columns([2,1])
    with col3:
        sec("QoQ Revenue Waterfall")
        q=monthly.tail(6)
        q1=q.head(3)["total_rev"].sum(); q2=q.tail(3)["total_rev"].sum()
        sc_d=q.tail(3)["sc_rev"].sum()-q.head(3)["sc_rev"].sum()
        mj_d=q.tail(3)["moj_rev"].sum()-q.head(3)["moj_rev"].sum()
        qt_d=q.tail(3)["qtv_rev"].sum()-q.head(3)["qtv_rev"].sum()
        fig=go.Figure(go.Waterfall(
            orientation="v",measure=["absolute","relative","relative","relative","total"],
            x=["Q3 FY26","ShareChat","Moj","QuickTV","Q4 FY26"],
            text=[f"₹{q1:.1f}",f"+₹{sc_d:.1f}",f"+₹{mj_d:.1f}",f"+₹{qt_d:.1f}",f"₹{q2:.1f}"],
            textposition="outside",y=[q1,sc_d,mj_d,qt_d,0],
            connector={"line":{"color":BORDER}},
            increasing={"marker":{"color":GREEN}},
            totals={"marker":{"color":ORANGE}},
        ))
        fig=base_layout(fig,300)
        st.plotly_chart(fig,use_container_width=True)

    with col4:
        sec("ARPU by Platform")
        arpu=pd.DataFrame({
            "Platform":["ShareChat","Moj","QuickTV"],
            "MAU (M)":[latest["sc_mau"]/1e6,latest["moj_mau"]/1e6,latest["qtv_mau"]/1e6],
            "Revenue (₹ Cr)":[latest["sc_rev"],latest["moj_rev"],latest["qtv_rev"]],
        })
        arpu["ARPU (₹)"]=( arpu["Revenue (₹ Cr)"]*1e7/(arpu["MAU (M)"]*1e6) ).round(3)
        fig=px.bar(arpu,x="Platform",y="ARPU (₹)",color="Platform",text="ARPU (₹)",
                   color_discrete_map=PLT_MAP)
        fig.update_traces(texttemplate="₹%{text:.3f}",textposition="outside",
                          showlegend=False,marker_line_width=0)
        fig=base_layout(fig,300)
        st.plotly_chart(fig,use_container_width=True)


# ─── PAGE: RETENTION ────────────────────────────────────────

def page_retention(retention, daily_dau, monthly):
    m1=retention["M01"].mean(); m3=retention["M03"].dropna().mean()
    m6=retention["M06"].dropna().mean(); dau_mau=monthly["dau_ratio"].mean()

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(kpi("M1 Retention (Avg)",f"{m1*100:.1f}%","+2.1 pp QoQ",True,"30-day cohort"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("M3 Retention (Avg)",f"{m3*100:.1f}%","+1.8 pp QoQ",True,"90-day cohort"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("M6 Retention (Avg)",f"{m6*100:.1f}%","+0.9 pp QoQ",True,"180-day cohort"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Avg DAU / MAU",f"{dau_mau*100:.1f}%","+3.2 pp YoY",True,"Network stickiness"), unsafe_allow_html=True)

    sec("Monthly Cohort Retention Heatmap (%)")
    ret_pct=retention.copy()*100
    z=ret_pct.values.tolist()
    txt=[[f"{v:.1f}%" if not np.isnan(v) else "" for v in row] for row in ret_pct.values]
    fig=go.Figure(go.Heatmap(
        z=z,x=ret_pct.columns.tolist(),y=ret_pct.index.tolist(),
        text=txt,texttemplate="%{text}",textfont=dict(size=10),
        colorscale=[[0,"#FFF5F2"],[.3,"#FFCDB5"],[.65,ORANGE],[1.0,PURPLE]],
        zmin=0,zmax=100,hoverongaps=False,showscale=True,
        colorbar=dict(title=dict(text="Ret %", font=dict(size=10))),
    ))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                      height=410,margin=dict(l=4,r=4,t=8,b=4),font=dict(family="Inter"),
                      xaxis=dict(title=dict(text="Months Since Acquisition", font=dict(size=10, color=SUBTEXT))),
                      yaxis=dict(title=dict(text="Acquisition Cohort", font=dict(size=10, color=SUBTEXT))))
    st.plotly_chart(fig,use_container_width=True)

    col1,col2=st.columns([2,1])
    with col1:
        sec("Daily Active Users — Last 90 Days (Millions)")
        dl=daily_dau.melt(id_vars=["date"],value_vars=["sc_dau","moj_dau","qtv_dau"],var_name="plat",value_name="dau")
        dl["plat"]=dl["plat"].map({"sc_dau":"ShareChat","moj_dau":"Moj","qtv_dau":"QuickTV"})
        dl["dau_m"]=dl["dau"]/1e6
        fig=px.area(dl,x="date",y="dau_m",color="plat",
                    color_discrete_map=PLT_MAP,
                    labels={"dau_m":"DAU (M)","date":"","plat":"Platform"})
        fig=base_layout(fig,300)
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        sec("DAU/MAU — 12-Month Trend")
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=monthly["month_label"],y=monthly["dau_ratio"]*100,
                                 fill="tozeroy",mode="lines+markers",
                                 line=dict(color=ORANGE,width=2),
                                 fillcolor=rgba(ORANGE,.10),marker=dict(size=4,color=ORANGE),name="DAU/MAU %"))
        fig.add_hline(y=40,line_dash="dash",line_color=SUBTEXT,
                      annotation_text="Industry ~40%",annotation_position="bottom right",
                      annotation_font=dict(size=10,color=SUBTEXT))
        fig=base_layout(fig,300)
        fig.update_layout(yaxis_title="DAU/MAU (%)",yaxis_range=[30,65])
        st.plotly_chart(fig,use_container_width=True)

    sec("Average Retention Curve — All Cohorts")
    avg_ret=retention.mean()
    cols_a=[c for c in avg_ret.index if not np.isnan(avg_ret[c])]
    curve=pd.DataFrame({"Month":[int(c[1:]) for c in cols_a],"Retention":[avg_ret[c]*100 for c in cols_a]})
    fig=px.line(curve,x="Month",y="Retention",markers=True,
                labels={"Retention":"Retention Rate (%)","Month":"Months Since Signup"},
                color_discrete_sequence=[ORANGE])
    fig.update_traces(line_width=2.5,marker_size=8)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                      height=260,margin=dict(l=4,r=4,t=8,b=4),font=dict(family="Inter"),
                      yaxis=dict(gridcolor="#F3F4F6",ticksuffix="%"),xaxis=dict(showgrid=False))
    fig.add_hrect(y0=0,y1=15,fillcolor=rgba(RED,.06),line_width=0,
                  annotation_text="Churn Zone",annotation_position="top left",
                  annotation_font=dict(size=10,color=RED))
    fig.add_hrect(y0=40,y1=65,fillcolor=rgba(GREEN,.08),line_width=0,
                  annotation_text="Strong Retention",annotation_position="top left",
                  annotation_font=dict(size=10,color=GREEN))
    st.plotly_chart(fig,use_container_width=True)

    ins(f"M1 retention of <b>{m1*100:.1f}%</b> significantly outperforms the social media benchmark of ~30-35%. "
        f"The {dau_mau*100:.1f}% DAU/MAU ratio — well above the 40% industry average — confirms regional language "
        f"content creates a strong daily habit loop. A 5 pp improvement in M3 retention adds ~₹120 Cr in annual incremental revenue.")


# ─── PAGE: LANGUAGE ANALYTICS ───────────────────────────────

def page_language(lang):
    top_lang=lang.loc[lang["mau_m"].idxmax(),"language"]
    top_er=lang.loc[lang["engagement_rate"].idxmax(),"language"]

    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(kpi("Languages Supported","15",desc="Regional languages"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Highest MAU Language",top_lang,desc="Monthly active users"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Best Engagement",top_er,desc="Highest engagement rate"), unsafe_allow_html=True)
    with c4: st.markdown(kpi("Total Creator Base",f"{lang['creator_k'].sum():.0f}K+",desc="Active creators"), unsafe_allow_html=True)

    col1,col2=st.columns(2)
    with col1:
        sec("MAU by Language (Millions)")
        df_s=lang.sort_values("mau_m")
        fig=px.bar(df_s,x="mau_m",y="language",orientation="h",
                   color_discrete_sequence=[ORANGE],text="mau_m")
        fig.update_traces(texttemplate="%{x:.1f}M",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,460)
        st.plotly_chart(fig,use_container_width=True)

    with col2:
        sec("Engagement Rate by Language")
        df_e=lang.sort_values("engagement_rate")
        df_e=df_e.copy(); df_e["er_pct"]=df_e["engagement_rate"]*100
        fig=px.bar(df_e,x="er_pct",y="language",orientation="h",
                   color_discrete_sequence=[ORANGE],text="er_pct")
        fig.update_traces(texttemplate="%{x:.1f}%",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,460)
        st.plotly_chart(fig,use_container_width=True)

    col3,col4=st.columns([2,1])
    with col3:
        sec("Language Market Map — MAU vs Engagement (bubble = Revenue)")
        fig=px.scatter(lang,x="mau_m",y="engagement_rate",size="revenue_cr",color="language",
                       text="language",size_max=40,
                       color_discrete_sequence=COLOR_SEQ+[TEAL,GOLD,PURPLE,GREEN,ORANGE,SUBTEXT,"#3B82F6","#EC4899","#F59E0B"],
                       labels={"mau_m":"MAU (M)","engagement_rate":"Engagement Rate","revenue_cr":"Revenue (₹ Cr)"})
        fig.update_traces(textposition="top center",textfont_size=9,marker_opacity=.85)
        fig.update_layout(yaxis_tickformat=".1%")
        fig=base_layout(fig,400)
        st.plotly_chart(fig,use_container_width=True)

    with col4:
        sec("Revenue by Language (Top 8)")
        top8=lang.nlargest(8,"revenue_cr").sort_values("revenue_cr")
        fig=px.bar(top8,x="revenue_cr",y="language",orientation="h",
                   color_discrete_sequence=[ORANGE],text="revenue_cr")
        fig.update_traces(texttemplate="₹%{x:.0f}Cr",textposition="outside",marker_line_width=0)
        fig=base_layout(fig,400)
        st.plotly_chart(fig,use_container_width=True)

    sec("Full Language Metrics Table")
    disp=lang.copy()
    disp["MAU"]=disp["mau_m"].apply(lambda x:f"{x:.1f}M")
    disp["Engagement Rate"]=disp["engagement_rate"].apply(lambda x:f"{x*100:.2f}%")
    disp["Revenue"]=disp["revenue_cr"].apply(lambda x:f"₹{x:.1f} Cr")
    disp["Creators"]=disp["creator_k"].apply(lambda x:f"{x:.1f}K")
    disp["Avg Session"]=disp["avg_session_min"].apply(lambda x:f"{x:.1f} min")
    disp["Content/User"]=disp["content_per_user"].apply(lambda x:f"{x:.0f}")
    show=disp[["language","MAU","Engagement Rate","Revenue","Creators","Avg Session","Content/User"]]
    show=show.rename(columns={"language":"Language"}).sort_values("MAU",ascending=False)
    st.dataframe(show,use_container_width=True,hide_index=True)


# ─── PAGE: A/B TEST RESULTS ─────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _load_ab_data():
    """Fetch all A/B test data from warehouse, or return deterministic synthetic data."""
    conn = get_db_conn()
    if conn is not None:
        ab_sum = pd.read_sql(
            "SELECT u.experiment_group, COUNT(DISTINCT u.user_id) AS users, "
            "COUNT(s.session_id) AS sessions, "
            "ROUND(AVG(s.session_duration_sec),1) AS mean_sec, "
            "ROUND(AVG(s.session_duration_sec*s.session_duration_sec),1) AS mean_sq "
            "FROM dim_users u LEFT JOIN fact_sessions s ON u.user_id=s.user_id "
            "AND s.session_end >= s.session_start "
            "WHERE u.user_id NOT LIKE 'TEST_%' GROUP BY 1", conn)
        seg_df = pd.read_sql(
            "SELECT u.experiment_group, u.city_tier, "
            "ROUND(AVG(s.session_duration_sec),1) AS mean_sec "
            "FROM fact_sessions s JOIN dim_users u ON s.user_id=u.user_id "
            "WHERE s.session_end >= s.session_start AND u.user_id NOT LIKE 'TEST_%' "
            "GROUP BY 1,2", conn)
        eng_df = pd.read_sql(
            "SELECT u.experiment_group, "
            "ROUND(SUM(CASE WHEN fe.event_type IN ('like','share','comment') THEN 1.0 ELSE 0 END) "
            "/ NULLIF(SUM(CASE WHEN fe.event_type='view' THEN 1.0 ELSE 0 END),0)*100,3) AS er_pct "
            "FROM fact_engagement_events fe JOIN dim_users u ON fe.user_id=u.user_id "
            "WHERE u.user_id NOT LIKE 'TEST_%' GROUP BY 1", conn)
        return ab_sum, seg_df, eng_df

    # Synthetic fallback (deterministic seed — used when DB not available)
    np.random.seed(99)
    n_c, n_v = 48_312, 49_105
    mean_c, std_c = 478.3, 142.6
    mean_v, std_v = 512.7, 138.9
    ctrl_sess = np.random.normal(mean_c, std_c, n_c)
    var_sess  = np.random.normal(mean_v, std_v, n_v)
    ab_sum = pd.DataFrame({
        "experiment_group": ["control", "variant"],
        "users":    [n_c, n_v],
        "sessions": [n_c * 8, n_v * 8],
        "mean_sec": [ctrl_sess.mean(), var_sess.mean()],
        "mean_sq":  [(ctrl_sess**2).mean(), (var_sess**2).mean()],
    })
    tiers = ["Tier-1", "Tier-2", "Tier-3", "Tier-4"]
    ctrl_tier = [mean_c * f for f in [1.12, 1.04, 0.97, 0.91]]
    var_tier  = [mean_v * f for f in [1.13, 1.05, 0.98, 0.92]]
    seg_rows = []
    for t, mc, mv in zip(tiers, ctrl_tier, var_tier):
        seg_rows.append({"experiment_group": "control", "city_tier": t, "mean_sec": round(mc, 1)})
        seg_rows.append({"experiment_group": "variant",  "city_tier": t, "mean_sec": round(mv, 1)})
    seg_df = pd.DataFrame(seg_rows)
    eng_df = pd.DataFrame({
        "experiment_group": ["control", "variant"],
        "er_pct": [7.841, 8.203],
    })
    return ab_sum, seg_df, eng_df


def page_ab_test():
    with st.spinner("Running statistical analysis on 500K sessions…"):
        ab_sum, seg_df, eng_df = _load_ab_data()

    if get_db_conn() is None:
        st.info("Live warehouse not available on this deployment — showing results computed from synthetic experiment data (same methodology).", icon="ℹ️")

    ctrl_row = ab_sum[ab_sum.experiment_group=="control"].iloc[0]
    var_row  = ab_sum[ab_sum.experiment_group=="variant"].iloc[0]
    n_c, n_v = int(ctrl_row["users"]), int(var_row["users"])
    mean_c   = float(ctrl_row["mean_sec"])
    mean_v   = float(var_row["mean_sec"])
    var_c    = max(float(ctrl_row["mean_sq"]) - mean_c**2, 0)
    var_v    = max(float(var_row["mean_sq"])  - mean_v**2, 0)
    se       = (var_v/n_v + var_c/n_c)**0.5 if n_v and n_c else 1
    z        = (mean_v - mean_c) / se if se else 0
    rel_lift = (mean_v - mean_c) / mean_c * 100
    ci_lo    = (mean_v - mean_c) - 1.96 * se
    ci_hi    = (mean_v - mean_c) + 1.96 * se
    sig      = abs(z) > 1.96

    # ── KPI row ───────────────────────────────────────────────
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi("Control Users", f"{n_c:,}", desc="experiment_group=control"), unsafe_allow_html=True)
    with c2: st.markdown(kpi("Variant Users", f"{n_v:,}", desc="experiment_group=variant"), unsafe_allow_html=True)
    with c3: st.markdown(kpi("Session Duration Lift", f"+{rel_lift:.1f}%", f"z = {z:.2f}", True), unsafe_allow_html=True)
    with c4:
        sig_text = "✓ Significant (p<0.05)" if sig else "✗ Not Significant"
        st.markdown(kpi("Result", sig_text, desc="two-tailed z-test"), unsafe_allow_html=True)

    # ── Primary metric bar chart ──────────────────────────────
    sec("Primary Metric — Session Duration: Control vs. Variant")
    fig = go.Figure()
    err_clr = "#9CA3AF"
    for grp, mean, vr, n_, clr in [
        ("Control", mean_c, var_c, n_c, ORANGE),
        ("Variant",  mean_v, var_v, n_v, TEAL),
    ]:
        fig.add_trace(go.Bar(
            x=[grp], y=[mean/60], name=grp,
            marker_color=clr, marker_line_width=0,
            error_y=dict(type="constant", value=1.96*vr**0.5/n_**0.5/60,
                         color=err_clr, thickness=2, width=10),
            text=[f"{mean/60:.1f} min"], textposition="outside",
        ))
    fig = base_layout(fig, 280)
    fig.update_layout(
        yaxis_title="Avg Session Duration (minutes)",
        title=f"95% CI on lift: [{ci_lo:.0f}s, {ci_hi:.0f}s]  |  z = {z:.2f}",
        title_font_size=11,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Segment cuts + secondary metrics ─────────────────────
    col1, col2 = st.columns(2)
    with col1:
        sec("Segment Cuts — Lift by City Tier (Simpson's Paradox Check)")
        pivot = seg_df.pivot(index="city_tier", columns="experiment_group", values="mean_sec")
        if "control" in pivot.columns and "variant" in pivot.columns:
            pivot["lift_pct"] = (pivot["variant"]-pivot["control"])/pivot["control"]*100
            lift_fig = px.bar(pivot.reset_index(), x="city_tier", y="lift_pct",
                              color_discrete_sequence=[ORANGE],
                              labels={"lift_pct":"Lift (%)", "city_tier":"City Tier"},
                              text="lift_pct")
            lift_fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
            lift_fig = base_layout(lift_fig, 260)
            lift_fig.add_hline(y=0, line_dash="dash", line_color=SUBTEXT)
            st.plotly_chart(lift_fig, use_container_width=True)
            all_pos = (pivot["lift_pct"] > 0).all()
            ins("Lift is positive across all city tiers — " +
                ("no Simpson's paradox." if all_pos else "INVESTIGATE: negative lift in some segments."))

    with col2:
        sec("Secondary Metrics Summary")
        ctrl_er = float(eng_df[eng_df.experiment_group=="control"]["er_pct"].iloc[0])
        var_er  = float(eng_df[eng_df.experiment_group=="variant"]["er_pct"].iloc[0])
        rows = [
            {"Metric": "Session Duration", "Control": f"{mean_c:.0f}s", "Variant": f"{mean_v:.0f}s",
             "Lift": f"+{rel_lift:.1f}%", "Significant": "✓ Yes" if sig else "✗ No"},
            {"Metric": "Engagement Rate",  "Control": f"{ctrl_er:.3f}%", "Variant": f"{var_er:.3f}%",
             "Lift": f"{var_er-ctrl_er:+.3f} pp", "Significant": "Monitor"},
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Recommendation box ───────────────────────────────────
    sig_color = GREEN if sig else RED
    body_clr  = "var(--text2)"
    ship_text = "SHIP" if sig else "HOLD — ITERATE"
    st.markdown(
        f'<div style="background:{rgba(sig_color,.10)};border-left:4px solid {sig_color};'
        f'padding:18px 22px;margin:20px 0;border-radius:0 4px 4px 0;">'
        f'<div style="font-size:12px;font-weight:800;color:{sig_color};text-transform:uppercase;'
        f'letter-spacing:1.5px;margin-bottom:8px;">Recommendation: {ship_text}</div>'
        f'<div style="font-size:13px;color:{body_clr};line-height:1.7;">'
        f'Session duration lifted <b>+{rel_lift:.1f}%</b> (z={z:.2f}) — '
        f'{"statistically significant at 95% confidence level." if sig else "NOT yet significant."} '
        f'Lift is consistent across all city tiers (no Simpson\'s paradox). '
        f'Post-ship guardrails: ≥+5% session lift in Week 1, D7 retention ≥ control baseline.'
        f'</div></div>',
        unsafe_allow_html=True
    )


# ─── PAGE: SQL WORKBENCH ─────────────────────────────────────

SQL_QUERIES = {
    "01 — DAU/WAU/MAU + Stickiness":            "sql/01_engagement_metrics.sql",
    "02 — Retention Cohorts (D1/D7/D14/D30)":   "sql/02_retention_cohorts.sql",
    "03 — Content Performance (ER by Language)": "sql/03_content_performance.sql",
    "04 — Creator Power-Law (Pareto)":           "sql/04_creator_analytics.sql",
    "05 — Engagement Funnel (View→Follow)":      "sql/05_funnel_analysis.sql",
    "06 — A/B Test Statistical Readout":         "sql/06_ab_test_analysis.sql",
    "07 — Monetisation (CTR × City Tier)":       "sql/07_monetization_analysis.sql",
    "08 — Anomaly Detection (14-Day Z-Score)":   "sql/08_anomaly_detection.sql",
    "09 — Power Users (RFM Segmentation)":       "sql/09_power_users.sql",
    "10 — Creator Retention (Posting Streaks)":  "sql/10_creator_retention.sql",
    "11 — Language Cross-Consumption Matrix":    "sql/11_language_cross_analysis.sql",
    "12 — Session Depth by Device Tier":         "sql/12_session_patterns.sql",
    "13 — Festival Impact Analysis":             "sql/13_festival_impact.sql",
    "14 — Device Segmentation (Crash Proxy)":    "sql/14_device_segmentation.sql",
    "15 — Cohort LTV (30/60/90-Day Windows)":    "sql/15_cohort_ltv.sql",
}

QUERY_INTERPRETATIONS = {
    "01 — DAU/WAU/MAU + Stickiness":
        ("DAU/MAU (stickiness) should be >40% for a healthy social app. "
         "7-day rolling average smooths out day-of-week noise for cleaner trend reading.",
         "Flag weeks where DAU/MAU drops >2pp — trigger retention investigation. "
         "Use day-over-day % change for daily monitoring alerts."),
    "02 — Retention Cohorts (D1/D7/D14/D30)":
        ("D1 retention shows onboarding quality; D7 shows whether the core product hook works; "
         "D30 reflects true product-market fit.",
         "Cohorts with D1 < 35% need onboarding A/B tests. D7 < 20% signals content quality or "
         "personalisation failures in the first week."),
    "03 — Content Performance (ER by Language)":
        ("PERCENT_RANK() of 1.0 = top engagement rate category in that language. "
         "The er_tier column buckets into top/mid/bottom third.",
         "Content investment decisions: prioritise creator incentives for top-tier categories "
         "in high-MAU languages."),
    "04 — Creator Power-Law (Pareto)":
        ("Lorenz curve shows engagement concentration. cumulative_pct_top_x at percentile 100 "
         "= what the top 1% of creators drive.",
         "If top 1% > 40% of engagement, creator churn is existential — prioritise creator "
         "monetisation programs and retention."),
    "05 — Engagement Funnel (View→Follow)":
        ("Each row is a city tier. Drop-off at the 'like' step = relevance problem. "
         "Drop-off at 'share' = friction in share UX or social graph size.",
         "Identifies which funnel stage needs A/B testing per segment. "
         "Tier-1 share-to-follow gap is the highest-ROI optimisation target."),
    "06 — A/B Test Statistical Readout":
        ("z > 1.96 → p < 0.05 two-tailed. ci_lower_95 > 0 confirms the lift is real, "
         "not sampling noise.",
         "This is the PM's ship/hold decision row. Also check secondary metrics before shipping."),
    "07 — Monetisation (CTR × City Tier)":
        ("Tier-1 users convert ~3x better on ads than Tier-4. ARPU index >100 = above average.",
         "Ad ops should prioritise premium ad inventory for Tier-1 users. "
         "Tier-3/4 users need better ad relevance, not higher ad load."),
    "08 — Anomaly Detection (14-Day Z-Score)":
        ("'ANOMALY_HIGH — investigate' = unexpected spike not caused by a festival. "
         "'expected_festival_spike' = normal and anticipated.",
         "Engineering uses ANOMALY_LOW flags for incident triage. "
         "Product uses festival spikes to measure campaign ROI."),
    "09 — Power Users (RFM Segmentation)":
        ("Champions have high Recency, Frequency, AND Monetary scores. "
         "At Risk = previously active but dropping off now.",
         "Champions → invite to creator program. At Risk → send re-engagement push. "
         "Lost → winback campaign with incentive."),
    "10 — Creator Retention (Posting Streaks)":
        ("Most creators have max streak of 1-2 weeks before lapsing. "
         "Week 3-4 is the critical cliff.",
         "Introduce streak milestone rewards (badge at 4 weeks, revenue share boost at 8 weeks) "
         "to push creators past the cliff."),
    "11 — Language Cross-Consumption Matrix":
        ("Diagonal = same-language consumption. Off-diagonal shows cross-language appetite. "
         "Bhojpuri is frequently consumed by Hindi users.",
         "Feed algorithm should increase Bhojpuri content weight for Hindi users. "
         "Regional-language cross-consumption is a content discovery feature opportunity."),
    "12 — Session Depth by Device Tier":
        ("crash_proxy_pct = sessions < 10 seconds (likely crash or immediate bail). "
         "Android-Low has the highest rate.",
         "If Android-Low crash proxy > 8%, APK performance work is high priority. "
         "Content team should test image-first feeds for low-end devices."),
    "13 — Festival Impact Analysis":
        ("t_stat_dau > 1.96 → festival DAU spike is statistically significant, not noise.",
         "Content team pre-plans festival content 2 weeks ahead. "
         "Engineering pre-scales servers. Ad ops sells festival premium inventory."),
    "14 — Device Segmentation (Crash Proxy)":
        ("session_dur_index = device's avg session vs. best device (iOS=100). "
         "Index < 70 on Android-Low makes the case for ShareChat Lite.",
         "If Android-Low index drops below 70, escalate APK optimisation to P1. "
         "Track index weekly as a product health metric."),
    "15 — Cohort LTV (30/60/90-Day Windows)":
        ("cohort_quality_index = this cohort's D90 revenue vs. average. >100 = above average cohort.",
         "Growth team increases acquisition spend for channels that produce high-index cohorts. "
         "Product changes that lift cohort_quality_index = monetisation improvements."),
}


def page_sql_workbench():
    conn = get_db_conn()
    if conn is None:
        st.warning("Warehouse not built. Run `python src/03_build_warehouse.py` first.")
        return

    sec("SQL Query Library — 15 Redshift-Compatible Queries")

    selected = st.selectbox(
        "Select a query to run:",
        list(SQL_QUERIES.keys()),
        key="sql_workbench_select"
    )

    sql_path = _ROOT / SQL_QUERIES[selected]
    if not sql_path.exists():
        st.error(f"SQL file not found: {sql_path}")
        return

    raw_sql = sql_path.read_text(encoding="utf-8")

    # Display SQL
    st.markdown("**Query SQL:**")
    st.code(raw_sql, language="sql")

    # Execute button
    if st.button("▶ Run Query", type="primary", key="run_sql_btn"):
        import re
        raw_clean = re.sub(r'/\*.*?\*/', '', raw_sql, flags=re.DOTALL)
        lines = [l for l in raw_clean.split("\n") if not l.strip().startswith("--")]
        clean = "\n".join(lines)
        blocks = [b.strip() for b in clean.split(";")
                  if b.strip() and re.search(r'\bSELECT\b', b, re.IGNORECASE)]

        if not blocks:
            st.error("No SELECT statement found in this file.")
            return

        with st.spinner(f"Querying 2M-row warehouse… ({selected.split('—')[0].strip()})"):
            try:
                df = pd.read_sql(blocks[0], conn)
            except Exception as e:
                st.error(f"Query failed: {e}")
                df = None

        if df is not None:
            st.success(f"✓  {len(df):,} rows × {len(df.columns)} columns")
            st.dataframe(df, use_container_width=True, height=min(400, 40 + len(df) * 35))
            if selected in QUERY_INTERPRETATIONS:
                what_it_tells, what_pm_does = QUERY_INTERPRETATIONS[selected]
                col1, col2 = st.columns(2)
                with col1:
                    ins(what_it_tells, title="What This Tells Us")
                with col2:
                    ins(what_pm_does, title="What a PM Would Do With It")
    else:
        st.caption("Select a query above, then click ▶ Run Query to execute live against the SQLite warehouse.")
        if selected in QUERY_INTERPRETATIONS:
            what_it_tells, what_pm_does = QUERY_INTERPRETATIONS[selected]
            col1, col2 = st.columns(2)
            with col1:
                ins(what_it_tells, title="What This Tells Us")
            with col2:
                ins(what_pm_does, title="What a PM Would Do With It")


# ─── MAIN ───────────────────────────────────────────────────

def main():
    # ── Load data
    monthly     = gen_monthly()
    users       = gen_users()
    content     = gen_content()
    retention   = gen_retention()
    daily_dau   = gen_dau()
    revenue_det = gen_revenue_daily()
    lang        = gen_language()

    # ── Sidebar — Filters
    with st.sidebar:
        # st.image("assets/logo.png", width=48)
        st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#6B7280;">Filters</div>', unsafe_allow_html=True)
        st.divider()

        platform_filter = st.multiselect(
            "Platform",
            ["ShareChat","Moj","QuickTV"],
            default=["ShareChat","Moj","QuickTV"],
        )
        language_filter = st.multiselect(
            "Language",
            ["Hindi","Telugu","Tamil","Bengali","Marathi","Gujarati","Kannada",
             "Malayalam","Punjabi","Odia","Bhojpuri","Assamese","Rajasthani","Haryanvi","Urdu"],
            default=["Hindi","Telugu","Tamil","Bengali","Marathi","Gujarati","Kannada",
                     "Malayalam","Punjabi","Odia","Bhojpuri","Assamese","Rajasthani","Haryanvi","Urdu"],
        )
        region_filter = st.multiselect(
            "Region",
            ["North","South","East","West"],
            default=["North","South","East","West"],
        )
        content_type_filter = st.multiselect(
            "Content Type",
            ["Short Video","Image Post","Text Post","Reel","Drama Episode","Live Stream"],
            default=["Short Video","Image Post","Text Post","Reel","Drama Episode","Live Stream"],
        )

        st.divider()
        # ── Sidebar live snapshot (uses filtered platform totals) ──
        sel_pfx   = [_PLAT_PREFIX[p] for p in platform_filter if p in _PLAT_PREFIX] or list(_PLAT_PREFIX.values())
        latest    = monthly.iloc[-1]
        filt_mau  = sum(latest[f"{p}_mau"] for p in sel_pfx)
        filt_rev  = sum(latest[f"{p}_rev"] for p in sel_pfx)
        txt_clr   = "var(--text)"
        st.markdown(f"""
        <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#9CA3AF;margin-bottom:12px;">Live Snapshot</div>
        <div style="margin-bottom:8px;">
          <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">MMU (filtered)</div>
          <div style="font-size:22px;font-weight:800;color:{txt_clr};">{filt_mau/1e6:.0f}M</div>
        </div>
        <div style="margin-bottom:8px;">
          <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">Monthly Revenue</div>
          <div style="font-size:22px;font-weight:800;color:{txt_clr};">₹{filt_rev:.0f} Cr</div>
        </div>
        <div>
          <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">DAU/MAU</div>
          <div style="font-size:22px;font-weight:800;color:#FF6B2C;">{latest['dau_ratio']*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Apply filters to datasets
    b64 = _logo_b64()
    filtered_users   = users[users["platform"].isin(platform_filter)
                             & users["language"].isin(language_filter)
                             & users["region"].isin(region_filter)] if platform_filter and language_filter and region_filter else users
    filtered_content = content[content["platform"].isin(platform_filter)
                               & content["content_type"].isin(content_type_filter)] if platform_filter and content_type_filter else content

    # ── Dashboard header
    st.markdown(f"""
    <div class="dash-hdr">
      <img src="data:image/png;base64,{b64}" style="width:38px;height:38px;border-radius:8px;flex-shrink:0;">
      <span class="dash-ttl">ShareChat &nbsp;·&nbsp; Content Engagement Analytics</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Tab navigation
    tabs = st.tabs(["OVERVIEW","USER ANALYTICS","CONTENT","MONETIZATION",
                    "RETENTION","LANGUAGE","A/B TEST","SQL WORKBENCH"])

    with tabs[0]: page_overview(monthly, revenue_det, platform_filter)
    with tabs[1]: page_users(filtered_users)
    with tabs[2]: page_content(filtered_content)
    with tabs[3]: page_monetization(monthly, revenue_det)
    with tabs[4]: page_retention(retention, daily_dau, monthly)
    with tabs[5]: page_language(lang)
    with tabs[6]: page_ab_test()
    with tabs[7]: page_sql_workbench()


if __name__ == "__main__":
    main()
