import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, timezone
import time

SB_URL = "https://zyavazsdrewokhgectqn.supabase.co"
SB_KEY = "sb_publishable_Vp6ltRkVEi8b2RIHZjnzOQ_6QeCqQCS"
sb = create_client(SB_URL, SB_KEY)

st.set_page_config(page_title="MasloJobs Dashboard", layout="wide", page_icon="🟢")
st.title("🟢 MasloJobs Pipeline Dashboard")

# ── 8-HOUR COUNTDOWN ─────────────────────────────────────────────────────────
st.header("⏰ Next Automated Scrape")
now = datetime.now(timezone.utc)
hours_since_midnight = now.hour + now.minute/60 + now.second/3600
last_run_hour = (int(hours_since_midnight / 8)) * 8
next_run_hour = last_run_hour + 8
if next_run_hour >= 24:
    next_run_hour = next_run_hour - 24
next_run = now.replace(hour=int(next_run_hour), minute=0, second=0, microsecond=0)
if next_run < now:
    next_run = next_run.replace(hour=int(next_run_hour))
diff = next_run - now
hours_left = int(diff.seconds // 3600)
mins_left = int((diff.seconds % 3600) // 60)
secs_left = int(diff.seconds % 60)
st.info(f"🕐 Next scrape in: **{hours_left}h {mins_left}m {secs_left}s** — runs every 8 hours automatically")
st.caption(f"Runs at 00:00, 08:00, 16:00 UTC | Current UTC time: {now.strftime('%H:%M:%S')}")

# ── PIPELINE LOG ─────────────────────────────────────────────────────────────
st.header("📋 Pipeline Log")
try:
    log = open("/home/laura/tech-jobs-scraper/pipeline.log").readlines()[-50:]
    errors = [l for l in log if "ERROR" in l or "FAIL" in l]
    warns = [l for l in log if "WARN" in l or "SKIP" in l]
    if errors:
        st.error(f"🚨 {len(errors)} ERRORS in last run")
        for e in errors: st.code(e.strip())
    elif warns:
        st.warning(f"⚠️ {len(warns)} warnings")
    else:
        st.success("✅ Last run clean")
    st.text_area("Log", "".join(log), height=150)
except:
    st.warning("No log yet — run pipeline first")

# ── LOAD DATA ────────────────────────────────────────────────────────────────
jobs = sb.table("tech_jobs_emea").select("*").execute().data
df = pd.DataFrame(jobs) if jobs else pd.DataFrame()

# ── DATA QUALITY ─────────────────────────────────────────────────────────────
st.header("🔍 Data Quality")
if not df.empty:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total Jobs", len(df))
    c2.metric("With Estimate", int(df["market_estimate"].notna().sum()) if "market_estimate" in df.columns else 0)
    c3.metric("With Industry", int(df["Industry"].notna().sum()) if "Industry" in df.columns else 0)
    c4.metric("With Logo", int(df["company_logo_url"].notna().sum()) if "company_logo_url" in df.columns else 0)
    c5.metric("With Employees", int(df["num_employees"].notna().sum()) if "num_employees" in df.columns else 0)

    st.subheader("⚠️ Missing Data Warnings")
    checks = {"Industry":"industry","num_employees":"employee count","market_estimate":"salary estimate","company_logo_url":"company logo"}
    any_issues = False
    for col,label in checks.items():
        if col in df.columns:
            n = int(df[col].isna().sum())
            if n > 0:
                st.warning(f"⚠️ {n} jobs missing {label}")
                any_issues = True
    if not any_issues:
        st.success("✅ All key fields populated!")

    # ── SPOTLIGHT CANDIDATES ─────────────────────────────────────────────────
    st.header("⭐ Spotlight Candidates")
    st.caption("Jobs with posted salary OR startup size (≤50 employees) — highest value listings")

    has_salary = pd.Series([False]*len(df))
    is_startup = pd.Series([False]*len(df))
    if "salary" in df.columns:
        has_salary = df["salary"].notna() & ~df["salary"].isin(["","Not posted"])
    if "num_employees" in df.columns:
        is_startup = df["num_employees"].astype(str).str.contains("1-10|11-50", na=False)

    spot_df = df[has_salary | is_startup].copy()

    if len(spot_df) > 0:
        st.success(f"⭐ {len(spot_df)} spotlight candidates found")
        for _, row in spot_df.head(10).iterrows():
            with st.expander(f"⭐ {row.get('title','N/A')} @ {row.get('company','N/A')} — {row.get('location','N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Company:** {row.get('company','N/A')}")
                    st.write(f"**Location:** {row.get('location','N/A')}")
                    st.write(f"**Level:** {row.get('level','N/A')}")
                    st.write(f"**Employees:** {row.get('num_employees','N/A')}")
                with col2:
                    st.write(f"**Posted Salary:** {row.get('salary','Not posted')}")
                    st.write(f"**Market Estimate:** {row.get('market_estimate','N/A')}")
                    st.write(f"**Industry:** {row.get('Industry','N/A')}")
                # Why spotlight?
                reasons = []
                if row.get("salary") and row.get("salary") not in ["","Not posted"]:
                    reasons.append("✅ Posts salary — rare transparency signal")
                    if row.get("market_estimate"):
                        est = str(row.get("market_estimate",""))
                        sal = str(row.get("salary",""))
                        reasons.append(f"💰 Salary vs market: {sal} vs benchmark {est}")
                if str(row.get("num_employees","")).strip() in ["1-10","11-50"]:
                    reasons.append("🚀 Early-stage startup — high growth potential")
                if row.get("Industry"):
                    reasons.append(f"🏭 Industry: {row.get('Industry')}")
                st.info("**Why spotlight?**\n" + "\n".join(reasons) if reasons else "Matches spotlight criteria")
    else:
        st.info("No spotlight candidates yet — run pipeline to populate")

    # ── CITY BREAKDOWN ────────────────────────────────────────────────────────
    st.header("🌍 Jobs by City")
    if "location" in df.columns:
        counts = {c:int(df["location"].str.contains(c,case=False,na=False).sum()) for c in ["London","Berlin","Paris","Amsterdam","Barcelona","Madrid","Dublin"]}
        st.bar_chart({k:v for k,v in counts.items() if v>0})

    # ── RECENT JOBS ───────────────────────────────────────────────────────────
    st.header("📋 Recent Jobs")
    rcols = [c for c in ["title","company","location","level","Industry","salary","market_estimate","scraped_at"] if c in df.columns]
    st.dataframe(df.sort_values("scraped_at",ascending=False).head(20)[rcols], use_container_width=True)

else:
    st.info("No jobs yet — run pipeline first")

st.header("⚙️ Automation")
st.success("✅ Windows Task Scheduler: every 8 hours — scrape → enrich → publish → maslojobs.com")
st.code("tail -f ~/tech-jobs-scraper/pipeline.log")
