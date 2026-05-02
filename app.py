import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
from openai import OpenAI
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="OSHE Master", layout="wide")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}]
        )
        return res.choices[0].message.content, True
    except:
        return "⚠️ AI unavailable", False

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

# ---------------- SIDEBAR ----------------
file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])

# ---------------- LOAD DATA ----------------
df = pd.DataFrame()

if file:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")

# ---------------- SESSION FILTERS (DRILL DOWN) ----------------
if "selected_risk" not in st.session_state:
    st.session_state.selected_risk = None

if "selected_hazard" not in st.session_state:
    st.session_state.selected_hazard = None

# ---------------- BASE FILTER ----------------
df_filtered = df.copy()

# Apply drill-down filters
if st.session_state.selected_risk:
    df_filtered = df_filtered[df_filtered["Risk"] == st.session_state.selected_risk]

if st.session_state.selected_hazard:
    df_filtered = df_filtered[df_filtered["Hazard Type"] == st.session_state.selected_hazard]

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
date_col = detect(["date"])

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

# ---------------- GAUGE ----------------
def gauge(v,t,m):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        title={'text':t},
        gauge={'axis':{'range':[0,m]},
               'steps':[{'range':[0,m*0.3],'color':'green'},
                        {'range':[m*0.3,m*0.7],'color':'yellow'},
                        {'range':[m*0.7,m],'color':'red'}]}
    ))

g1,g2,g3 = st.columns(3)
g1.plotly_chart(gauge(TRIR,"TRIR",5),use_container_width=True)
g2.plotly_chart(gauge(LTIFR,"LTIFR",3),use_container_width=True)
g3.plotly_chart(gauge(SR,"Severity",300),use_container_width=True)

# ---------------- DRILL-DOWN CHART ----------------
st.subheader("📊 Risk Drill-Down")

if "Risk" in df.columns:

    risk_counts = df["Risk"].value_counts().reset_index()
    risk_counts.columns = ["Risk","Count"]

    fig = px.bar(risk_counts, x="Risk", y="Count")

    selected = st.plotly_chart(fig, use_container_width=True)

    # Buttons for drill-down (Streamlit limitation workaround)
    for r in risk_counts["Risk"]:
        if st.button(f"Filter: {r}"):
            st.session_state.selected_risk = r

# ---------------- HAZARD DRILL ----------------
st.subheader("📊 Hazard Drill-Down")

if "Hazard Type" in df.columns:

    haz_counts = df["Hazard Type"].value_counts().reset_index()
    haz_counts.columns = ["Hazard","Count"]

    fig2 = px.bar(haz_counts, x="Hazard", y="Count")
    st.plotly_chart(fig2, use_container_width=True)

    for h in haz_counts["Hazard"]:
        if st.button(f"Hazard: {h}"):
            st.session_state.selected_hazard = h

# ---------------- RESET ----------------
if st.button("🔄 Reset Filters"):
    st.session_state.selected_risk = None
    st.session_state.selected_hazard = None

# ---------------- AI ----------------
st.subheader("🤖 AI")

q = st.text_input("Ask")

if q and not df_filtered.empty:
    sample=df_filtered.head(50).to_csv(index=False)
    ans,ok=ask_ai("Analyze:\n"+sample+"\nQ:"+q)
    st.write(ans)

# ---------------- ROOT CAUSE ----------------
if "Risk" in df_filtered.columns:
    hr=df_filtered[df_filtered["Risk"].astype(str).str.contains("high",case=False)]
    if len(hr)>0:
        if st.button("Analyze Root Cause"):
            ans,_=ask_ai(hr.head(30).to_csv(index=False))
            st.write(ans)

# ---------------- PDF ----------------
if st.button("📄 Report"):
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial",size=10)
    pdf.multi_cell(0,6,"HSE Report Generated")
    path=tempfile.NamedTemporaryFile(delete=False).name
    pdf.output(path)
    with open(path,"rb") as f:
        st.download_button("Download",f,"report.pdf")
