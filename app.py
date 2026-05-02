import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="OSHE Master", layout="wide")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def ask_ai(prompt):
    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}]
        )
        return res.choices[0].message.content
    except:
        return "⚠️ AI unavailable"

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {background:#f4f6f9;}

.kpi-card {
    background:white;
    padding:20px;
    border-radius:12px;
    box-shadow:0px 2px 8px rgba(0,0,0,0.08);
    text-align:center;
}

.header-box {
    background:white;
    padding:15px;
    border-radius:10px;
    box-shadow:0px 2px 6px rgba(0,0,0,0.08);
    margin-bottom:15px;
}
</style>
""", unsafe_allow_html=True)

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
st.sidebar.image("https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png", width=120)

st.sidebar.markdown("## 📂 Upload Data")
file = st.sidebar.file_uploader("", type=["csv","xlsx"])

# ---------------- LOAD DATA ----------------
df = pd.DataFrame()

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")

# ---------------- FILTER STATE ----------------
if "risk_filter" not in st.session_state:
    st.session_state.risk_filter = []

if "hazard_filter" not in st.session_state:
    st.session_state.hazard_filter = []

# ---------------- FILTER UI ----------------
if not df.empty:

    st.sidebar.markdown("### 🎛 Filters")

    risk_options = df["Risk"].dropna().unique() if "Risk" in df.columns else []
    hazard_options = df["Hazard Type"].dropna().unique() if "Hazard Type" in df.columns else []

    st.session_state.risk_filter = st.sidebar.multiselect(
        "Select Risk", risk_options, default=st.session_state.risk_filter
    )

    st.session_state.hazard_filter = st.sidebar.multiselect(
        "Select Hazard", hazard_options, default=st.session_state.hazard_filter
    )

    if st.sidebar.button("🔄 Reset Filters"):
        st.session_state.risk_filter = []
        st.session_state.hazard_filter = []
        st.rerun()

# ---------------- APPLY FILTER ----------------
df_filtered = df.copy()

if "Risk" in df.columns and st.session_state.risk_filter:
    df_filtered = df_filtered[df_filtered["Risk"].isin(st.session_state.risk_filter)]

if "Hazard Type" in df.columns and st.session_state.hazard_filter:
    df_filtered = df_filtered[df_filtered["Hazard Type"].isin(st.session_state.hazard_filter)]

# ---------------- HEADER ----------------
col_logo, col_title = st.columns([1,4])

with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png", width=80)

with col_title:
    st.title("🛡️ OSHE Master Dashboard")
    st.markdown("### HSE KPI Monitoring System")

# ---------------- INFO BOX ----------------
st.markdown("""
<div class="header-box">
<b>Alexandria University</b><br>
Supervisor: Dr. Mohamed Tash<br><br>

<b>Team - Group 01</b><br>
Dina Mohamed<br>
Samar Zaiton<br>
Mohamed Gamal<br>
Ahmed Badawy<br>
Hazem Hashem<br>
Ahmed Abd Elrheem<br>
Mohamed Abd Elrazek<br>
Amir Salem
</div>
""", unsafe_allow_html=True)

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

# KPI CARDS
c1,c2,c3 = st.columns(3)

c1.markdown(f'<div class="kpi-card"><h4>TRIR</h4><h2>{round(TRIR,2)}</h2></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-card"><h4>LTIFR</h4><h2>{round(LTIFR,2)}</h2></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-card"><h4>Severity</h4><h2>{round(SR,2)}</h2></div>', unsafe_allow_html=True)

# ---------------- GAUGES ----------------
def gauge(v,t,m):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        title={'text':t},
        gauge={
            'axis':{'range':[0,m]},
            'steps':[
                {'range':[0,m*0.3],'color':'green'},
                {'range':[m*0.3,m*0.7],'color':'yellow'},
                {'range':[m*0.7,m],'color':'red'}
            ]
        }
    ))

g1,g2,g3 = st.columns(3)
g1.plotly_chart(gauge(TRIR,"TRIR",5), use_container_width=True)
g2.plotly_chart(gauge(LTIFR,"LTIFR",3), use_container_width=True)
g3.plotly_chart(gauge(SR,"Severity",300), use_container_width=True)

# ---------------- CHARTS ----------------
colA, colB = st.columns(2)

if "Hazard Type" in df_filtered.columns:
    colA.plotly_chart(px.pie(df_filtered, names="Hazard Type", title="Hazard Distribution"),
                      use_container_width=True)

if "Risk" in df_filtered.columns:
    colB.plotly_chart(px.histogram(df_filtered, x="Risk", title="Risk Distribution"),
                      use_container_width=True)

# ---------------- AI ----------------
st.subheader("🤖 AI Assistant")

q = st.text_input("Ask about your data")

if q and not df_filtered.empty:
    sample = df_filtered.head(50).to_csv(index=False)
    st.success(ask_ai(f"Analyze:\n{sample}\nQuestion:{q}"))
