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
        return "⚠️ AI unavailable or quota exceeded"

# ---------------- STYLE (POWER BI LOOK) ----------------
st.markdown("""
<style>
.stApp {
    background-color: #f4f6f9;
}

/* KPI Cards */
.kpi-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}

/* Section Titles */
h1, h2, h3 {
    color: #1f4e79;
}

/* Remove extra padding */
.block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "1234":
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
    try:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")
        st.sidebar.success("Data loaded")
    except Exception as e:
        st.error(e)
        st.stop()

# ---------------- FILTERS ----------------
df_filtered = df.copy()

if not df.empty:

    st.sidebar.markdown("### 🎛 Filters")

    if "Risk" in df.columns:
        risk = st.sidebar.multiselect("Risk", df["Risk"].dropna().unique())
        if risk:
            df_filtered = df_filtered[df_filtered["Risk"].isin(risk)]

    if "Hazard Type" in df.columns:
        haz = st.sidebar.multiselect("Hazard", df["Hazard Type"].dropna().unique())
        if haz:
            df_filtered = df_filtered[df_filtered["Hazard Type"].isin(haz)]

    st.sidebar.markdown(f"📊 Records: {len(df_filtered)}")

# ---------------- KPI FUNCTIONS ----------------
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
    "📊 Executive Dashboard",
    "📈 Analysis",
    "🤖 AI Insights"
])

# ================= TAB 1 =================
with tab1:

    st.subheader("📊 KPI Overview")

    col1, col2, col3 = st.columns(3)

    col1.markdown(f"""
    <div class="kpi-card">
        <h4>TRIR</h4>
        <h2>{round(TRIR,2)}</h2>
    </div>
    """, unsafe_allow_html=True)

    col2.markdown(f"""
    <div class="kpi-card">
        <h4>LTIFR</h4>
        <h2>{round(LTIFR,2)}</h2>
    </div>
    """, unsafe_allow_html=True)

    col3.markdown(f"""
    <div class="kpi-card">
        <h4>Severity</h4>
        <h2>{round(SR,2)}</h2>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Gauges
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

    g1, g2, g3 = st.columns(3)
    g1.plotly_chart(gauge(TRIR,"TRIR",5), use_container_width=True)
    g2.plotly_chart(gauge(LTIFR,"LTIFR",3), use_container_width=True)
    g3.plotly_chart(gauge(SR,"Severity",300), use_container_width=True)

# ================= TAB 2 =================
with tab2:

    st.subheader("📈 Data Analysis")

    colA, colB = st.columns(2)

    if "Hazard Type" in df_filtered.columns:
        with colA:
            st.plotly_chart(px.pie(df_filtered, names="Hazard Type", title="Hazard Distribution"),
                            use_container_width=True)

    if "Risk" in df_filtered.columns:
        with colB:
            st.plotly_chart(px.histogram(df_filtered, x="Risk", title="Risk Distribution"),
                            use_container_width=True)

    if "Location" in df_filtered.columns and "Hazard Type" in df_filtered.columns:
        heat = pd.crosstab(df_filtered["Location"], df_filtered["Hazard Type"])
        st.plotly_chart(px.imshow(heat, text_auto=True, title="Risk Heatmap"),
                        use_container_width=True)

# ================= TAB 3 =================
with tab3:

    st.subheader("🤖 AI Assistant")

    q = st.text_input("Ask about your data")

    if q and not df_filtered.empty:
        sample = df_filtered.head(50).to_csv(index=False)
        answer = ask_ai(f"Analyze:\n{sample}\nQuestion:{q}")
        st.success(answer)
