import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

st.set_page_config(layout="wide")

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

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
.stApp {background:#f5f7fb;}
h1 {color:#1f4e79;}
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
st.sidebar.title("📂 Upload Data")
file = st.sidebar.file_uploader("", type=["csv","xlsx"])

# ---------------- LOAD DATA ----------------
df = pd.DataFrame()

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")

# ---------------- FILTERS ----------------
df_filtered = df.copy()

if not df.empty:

    st.sidebar.markdown("### 🎛 Filters")

    if "Risk" in df.columns:
        risk = st.sidebar.multiselect("Risk", df["Risk"].unique())
        if risk:
            df_filtered = df_filtered[df_filtered["Risk"].isin(risk)]

    if "Hazard Type" in df.columns:
        haz = st.sidebar.multiselect("Hazard", df["Hazard Type"].unique())
        if haz:
            df_filtered = df_filtered[df_filtered["Hazard Type"].isin(haz)]

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

# ---------------- HEADER ----------------
st.title("🛡️ OSHE Master Dashboard")

# ---------------- TABS ----------------
tab1, tab2, tab3 = st.tabs([
    "📊 Executive",
    "📈 Analysis",
    "🤖 AI"
])

# ================= TAB 1 =================
with tab1:

    st.subheader("📊 KPI Overview")

    c1,c2,c3 = st.columns(3)
    c1.metric("TRIR", round(TRIR,2))
    c2.metric("LTIFR", round(LTIFR,2))
    c3.metric("Severity", round(SR,2))

    # Gauges
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

# ================= TAB 2 =================
with tab2:

    st.subheader("📈 Data Analysis")

    if "Hazard Type" in df_filtered.columns:
        st.plotly_chart(px.pie(df_filtered, names="Hazard Type"), use_container_width=True)

    if "Risk" in df_filtered.columns:
        st.plotly_chart(px.histogram(df_filtered, x="Risk"), use_container_width=True)

    if "Location" in df_filtered.columns and "Hazard Type" in df_filtered.columns:
        heat = pd.crosstab(df_filtered["Location"], df_filtered["Hazard Type"])
        st.plotly_chart(px.imshow(heat, text_auto=True), use_container_width=True)

# ================= TAB 3 =================
with tab3:

    st.subheader("🤖 AI Assistant")

    q = st.text_input("Ask about your data")

    if q and not df_filtered.empty:
        sample = df_filtered.head(50).to_csv(index=False)
        st.write(ask_ai(f"Analyze:\n{sample}\nQuestion:{q}"))
