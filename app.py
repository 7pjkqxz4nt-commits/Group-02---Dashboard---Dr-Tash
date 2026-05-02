import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import tempfile

st.set_page_config(layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {background: linear-gradient(to right,#203a43,#2c5364);color:white;}
.card {background:white;color:black;padding:20px;border-radius:12px;margin-bottom:15px;}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("""
    <div style="text-align:center;margin-top:100px;background:white;color:black;padding:30px;border-radius:15px;width:400px;margin:auto;">
    <img src="https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png" width="80">
    <h2>OSHE Master</h2>
    <p>HSE Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == "admin" and p == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid login")
    st.stop()

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.title("📊 Filters")

file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])

df = pd.DataFrame()

if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    df.columns = df.columns.str.strip()

    # Filters
    if "Location" in df.columns:
        loc = st.sidebar.multiselect("Location", df["Location"].unique())
        if loc:
            df = df[df["Location"].isin(loc)]

    if "Risk" in df.columns:
        risk = st.sidebar.multiselect("Risk", df["Risk"].unique())
        if risk:
            df = df[df["Risk"].isin(risk)]

# ---------------- HEADER ----------------
st.title("🛡️ HSE KPI Dashboard")

# ---------------- KPIs ----------------
if not df.empty:

    H = df.get("Hours Worked", pd.Series([0])).sum()
    R = df.get("Recordable Incidents", pd.Series([0])).sum()
    LTI = df.get("Lost Time Injuries", pd.Series([0])).sum()
    Lost_days = df.get("Lost Days", pd.Series([0])).sum()

    TRIR = (R * 200000) / H if H else 0
    LTIFR = (LTI * 1000000) / H if H else 0
    SR = (Lost_days * 200000) / H if H else 0

    def benchmark(val, good, avg):
        if val <= good: return "🟢 Good"
        elif val <= avg: return "🟡 Avg"
        else: return "🔴 Poor"

    col1,col2,col3 = st.columns(3)
    col1.metric("TRIR", round(TRIR,2), benchmark(TRIR,1,3))
    col2.metric("LTIFR", round(LTIFR,2), benchmark(LTIFR,0.5,1.5))
    col3.metric("Severity Rate", round(SR,2), benchmark(SR,50,200))

# ---------------- CHARTS ----------------
if not df.empty:

    st.subheader("📈 Charts")

    if "Risk" in df.columns:
        fig = px.histogram(df, x="Risk", color="Risk")
        st.plotly_chart(fig, use_container_width=True)

    if "Hazard Type" in df.columns:
        fig2 = px.pie(df, names="Hazard Type")
        st.plotly_chart(fig2, use_container_width=True)

# ---------------- AI ASSISTANT ----------------
st.subheader("🤖 AI Assistant")

question = st.text_input("Ask about your data")

if question and not df.empty:
    if "Risk" in df.columns:
        high = df["Risk"].astype(str).str.contains("high", case=False).sum()
        st.write(f"High risk cases: {high}")

    if "Hazard Type" in df.columns:
        st.write("Most common hazard:", df["Hazard Type"].mode()[0])

# ---------------- PDF REPORT ----------------
if not df.empty and st.button("📄 Generate PDF Report"):

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200,10,"HSE Report",ln=True)

    pdf.cell(200,10,f"TRIR: {round(TRIR,2)}",ln=True)
    pdf.cell(200,10,f"LTIFR: {round(LTIFR,2)}",ln=True)
    pdf.cell(200,10,f"Severity Rate: {round(SR,2)}",ln=True)

    file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    pdf.output(file_path)

    with open(file_path, "rb") as f:
        st.download_button("Download Report", f, "HSE_Report.pdf")
