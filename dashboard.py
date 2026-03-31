import streamlit as st
import pandas as pd
from supabase import create_client

SB_URL = "https://zyavazsdrewokhgectqn.supabase.co"
SB_KEY = "sb_publishable_Vp6ltRkVEi8b2RIHZjnzOQ_6QeCqQCS"
sb = create_client(SB_URL, SB_KEY)

st.set_page_config(page_title="MasloJobs Dashboard", layout="wide", page_icon="🟢")
st.title("🟢 MasloJobs Pipeline Dashboard")

st.header("📋 Pipeline Log")
try:
    log = open("/home/laura/tech-jobs-scraper/pipeline.log").readlines()[-50:]
    errors = [l for l in log if "ERROR" in l or "FAIL" in l]
    warns = [l for l in log if "WARN" in l or "SKIP" in l]
    if errors:
        st.error(f"🚨 {len(errors)} ERRORS detected")
        for e in errors:
            st.code(e.strip())
    elif warns:
        st.warning(f"⚠️ {len(warns)} warnings")
        for w in warns[:5]:
            st.code(w.strip())
    else:
        st.success("✅ Last run clean — no errors")
    st.text_area("Log", "".join(log), height=150)
except Exception:
    st.warning("No log file yet — run pipeline first")

jobs = sb.table("tech_jobs_emea").select("*").execute().data
df = pd.DataFrame(jobs) if jobs else pd.DataFrame()

st.header("🔍 Data Quality")
if not df.empty:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Jobs", len(df))
    c2.metric("With Estimate", int(df["market_estimate"].notna().sum()) if "market_estimate" in df.columns else 0)
    c3.metric("With Industry", int(df["industry"].notna().sum()) if "industry" in df.columns else 0)
    c4.metric("With Logo", int(df["company_logo_url"].notna().sum()) if "company_logo_url" in df.columns else 0)
    c5.metric("With Employees", int(df["num_employees"].notna().sum()) if "num_employees" in df.columns else 0)

    st.subheader("⚠️ Missing Data Warnings")
    checks = {
        "industry": "industry",
        "num_employees": "employee count",
        "market_estimate": "salary estimate",
        "company_logo_url": "company logo",
    }
    any_issues = False
    for col, label in checks.items():
        if col in df.columns:
            n = int(df[col].isna().sum())
            if n > 0:
                st.warning(f"⚠️ {n} jobs missing {label}")
                any_issues = True
    if not any_issues:
        st.success("✅ All key fields populated!")

    st.header("⭐ Spotlight Candidates")
    st.caption("Jobs with posted salary OR startup size — prime candidates for spotlight")
    has_salary = pd.Series([False] * len(df))
    is_startup = pd.Series([False] * len(df))
    if "salary" in df.columns:
        has_salary = df["salary"].notna() & ~df["salary"].isin(["", "Not posted"])
    if "num_employees" in df.columns:
        is_startup = df["num_employees"].astype(str).str.contains("1-10|11-50", na=False)
    spot_df = df[has_salary | is_startup]
    if len(spot_df) > 0:
        st.success(f"⭐ {len(spot_df)} spotlight candidates found")
        show = [c for c in ["title","company","location","salary","market_estimate","num_employees","industry"] if c in spot_df.columns]
        st.dataframe(spot_df[show].head(20), use_container_width=True)
    else:
        st.info("No spotlight candidates yet — run pipeline to populate")

    st.header("🌍 Jobs by City")
    if "location" in df.columns:
        counts = {c: int(df["location"].str.contains(c, case=False, na=False).sum()) for c in ["London","Berlin","Paris","Amsterdam","Barcelona","Madrid","Dublin"]}
        st.bar_chart({k: v for k, v in counts.items() if v > 0})

    st.header("📋 Recent Jobs")
    rcols = [c for c in ["title","company","location","level","industry","salary","market_estimate","scraped_at"] if c in df.columns]
    st.dataframe(df.sort_values("scraped_at", ascending=False).head(20)[rcols], use_container_width=True)

else:
    st.info("No jobs yet — run pipeline first")

st.header("⏰ Automation")
st.success("✅ Cron active: every 6 hours — scrape → enrich → publish")
st.code("tail -f ~/tech-jobs-scraper/pipeline.log")
