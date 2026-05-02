import streamlit as st
import pandas as pd
import plotly.express as px
import re
from fpdf import FPDF
import tempfile
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="OSHE Master", layout="wide")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- STYLE ----------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(to right, #203a43, #2c5364);
    color: white;
}
section[data-testid="stSidebar"] {
    background: #1c2b36;
}
.card {
    background: white;
    color: black;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 15px;
}
.footer {
    text-align: center;
    margin-top: 40px;
    color: #ccc;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:

    st.markdown("""
    <div style="width:400px;margin:auto;margin-top:100px;
    background:white;color:black;padding:30px;border-radius:15px;text-align:center;">
    
    <img src="https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png" width="80">
    <h2>OSHE Master</h2>
    <p>HSE KPI Dashboard</p>
    """, unsafe_allow_html=True)

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "1234":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.markdown("""
    <hr>
    <b>Prepared by</b><br>
    Dina Mohamed, Samar Zaiton, Mohamed Gamal,<br>
    Ahmed Badawy, Hazem Hashem,<br>
    Ahmed Abd Elrheem, Mohamed Abd Elrazek, Amir Salem
    </div>
    """, unsafe_allow_html=True)

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png",
    width=120
)

st.sidebar.markdown("### 🛡️ OSHE Master")
st.sidebar.markdown("HSE Dashboard")

file = st.sidebar.file_uploader("📂 Upload Data", type=["csv", "xlsx"])

# ---------------- HEADER ----------------
st.title("🛡️ OSHE Master Dashboard")

df = pd.DataFrame()

# ---------------- LOAD DATA ----------------
if file:
    df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    st.success("✅ Data uploaded successfully")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📂 Data Preview")
    st.write(df.head())
    st.markdown('</div>', unsafe_allow_html=True)

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

    st.markdown('<div class="card">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("TRIR", round(TRIR,2), benchmark(TRIR,1,3))
    col2.metric("LTIFR", round(LTIFR,2), benchmark(LTIFR,0.5,1.5))
    col3.metric("Severity Rate", round(SR,2), benchmark(SR,50,200))

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- CHARTS ----------------
if not df.empty:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Charts")

    if "Risk" in df.columns:
        st.plotly_chart(px.histogram(df, x="Risk", color="Risk"), use_container_width=True)

    if "Hazard Type" in df.columns:
        st.plotly_chart(px.pie(df, names="Hazard Type"), use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- AI ASSISTANT ----------------
st.subheader("🤖 AI Assistant")

question = st.text_input("Ask about your data")

if question and not df.empty:

    sample = df.head(50).to_csv(index=False)

    prompt = f"""
You are an HSE expert.

Dataset:
{sample}

Question:
{question}

Provide insights and recommendations.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are an HSE expert."},
                {"role": "user", "content": prompt}
            ]
        )
        st.write(response.choices[0].message.content)

    except Exception as e:
        st.error(f"AI Error: {e}")

# ---------------- PDF ----------------
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

# ---------------- FOOTER ----------------
st.markdown("""
<div class="footer">
© 2026 OSHE Master – HSE Dashboard | University of Alexandria
</div>
""", unsafe_allow_html=True)
