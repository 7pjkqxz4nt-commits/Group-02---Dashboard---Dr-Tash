import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

st.set_page_config(layout="wide")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- LOGIN ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == "admin" and p == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()

# ---------------- FILE ----------------
file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])

df = pd.DataFrame()

if file:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")

# ---------------- SESSION FILTER ----------------
if "risk_filter" not in st.session_state:
    st.session_state.risk_filter = None

if "hazard_filter" not in st.session_state:
    st.session_state.hazard_filter = None

# ---------------- APPLY FILTER ----------------
df_filtered = df.copy()

if st.session_state.risk_filter:
    df_filtered = df_filtered[df_filtered["Risk"].isin(st.session_state.risk_filter)]

if st.session_state.hazard_filter:
    df_filtered = df_filtered[df_filtered["Hazard Type"].isin(st.session_state.hazard_filter)]

# ---------------- KPI ----------------
def detect(keys):
    for col in df.columns:
        for k in keys:
            if k.lower() in col.lower():
                return col
    return None

def safe(col):
    return pd.to_numeric(df_filtered[col], errors="coerce").sum() if col else 0

hours = detect(["hours"])
incidents = detect(["incident"])
lti = detect(["lost time"])
lost_days = detect(["lost days"])

H = safe(hours)
R = safe(incidents)
LTI = safe(lti)
LD = safe(lost_days)

TRIR = (R*200000)/H if H else 0
LTIFR = (LTI*1000000)/H if H else 0
SR = (LD*200000)/H if H else 0

# ---------------- DASHBOARD ----------------
st.title("🛡️ OSHE Master Dashboard")

c1,c2,c3 = st.columns(3)
c1.metric("TRIR", round(TRIR,2))
c2.metric("LTIFR", round(LTIFR,2))
c3.metric("Severity", round(SR,2))

# ---------------- RISK CHART ----------------
st.subheader("📊 Risk Distribution (Click to Filter)")

if "Risk" in df.columns:

    risk_counts = df["Risk"].value_counts().reset_index()
    risk_counts.columns = ["Risk","Count"]

    fig = px.bar(risk_counts, x="Risk", y="Count")

    selected = st.plotly_chart(fig, use_container_width=True)

    selected_risk = st.multiselect(
        "Select Risk (simulate click)",
        options=risk_counts["Risk"].tolist()
    )

    if selected_risk:
        st.session_state.risk_filter = selected_risk

# ---------------- HAZARD CHART ----------------
st.subheader("📊 Hazard Distribution (Click to Filter)")

if "Hazard Type" in df.columns:

    hazard_counts = df["Hazard Type"].value_counts().reset_index()
    hazard_counts.columns = ["Hazard","Count"]

    fig2 = px.bar(hazard_counts, x="Hazard", y="Count")
    st.plotly_chart(fig2, use_container_width=True)

    selected_hazard = st.multiselect(
        "Select Hazard",
        options=hazard_counts["Hazard"].tolist()
    )

    if selected_hazard:
        st.session_state.hazard_filter = selected_hazard

# ---------------- RESET ----------------
if st.button("🔄 Reset Filters"):
    st.session_state.risk_filter = None
    st.session_state.hazard_filter = None

# ---------------- AI ----------------
st.subheader("🤖 AI Assistant")

q = st.text_input("Ask about filtered data")

if q and not df_filtered.empty:
    sample = df_filtered.head(50).to_csv(index=False)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role":"user","content":f"Analyze:\n{sample}\nQuestion:{q}"}]
    )

    st.write(response.choices[0].message.content)

# ---------------- DATA PREVIEW ----------------
st.subheader("📄 Filtered Data")
st.dataframe(df_filtered.head(50))
