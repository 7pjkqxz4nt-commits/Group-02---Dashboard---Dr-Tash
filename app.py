import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import tempfile
from openai import OpenAI
from sklearn.linear_model import LinearRegression
import numpy as np

# ---------------- CONFIG ----------------
st.set_page_config(page_title="OSHE Master", layout="wide")

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- BRIGHT UI ----------------
st.markdown("""
<style>
.stApp {background:#f5f7fb;color:#2c3e50;}
section[data-testid="stSidebar"] {background:white;}
.card {background:white;padding:20px;border-radius:10px;margin-bottom:15px;
box-shadow:0px 2px 8px rgba(0,0,0,0.08);}
</style>
""", unsafe_allow_html=True)

# ---------------- LOGIN ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:

    st.markdown("""
    <div style="width:400px;margin:auto;margin-top:100px;background:white;
    padding:30px;border-radius:15px;text-align:center;">
    <img src="https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png" width="80">
    <h2>OSHE Master</h2>
    <p>HSE KPI Dashboard</p>
    </div>
    """, unsafe_allow_html=True)

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
file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])

st.title("🛡️ OSHE Master Dashboard")

df = pd.DataFrame()

# ---------------- LOAD DATA ----------------
if file:
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, engine="openpyxl")

        st.success("✅ Data uploaded")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.write(df.head())
        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(e)
        st.stop()

# ---------------- SMART COLUMN DETECTION ----------------
def detect_column(keywords):
    for col in df.columns:
        for k in keywords:
            if k.lower() in col.lower():
                return col
    return None

def safe_sum(col):
    return pd.to_numeric(df[col], errors="coerce").sum() if col else 0

if not df.empty:

    hours_col = detect_column(["hours"])
    incident_col = detect_column(["incident"])
    lti_col = detect_column(["lost time"])
    lost_days_col = detect_column(["lost days"])
    date_col = detect_column(["date"])

    H = safe_sum(hours_col)
    R = safe_sum(incident_col)
    LTI = safe_sum(lti_col)
    Lost_days = safe_sum(lost_days_col)

    TRIR = (R * 200000) / H if H else 0
    LTIFR = (LTI * 1000000) / H if H else 0
    SR = (Lost_days * 200000) / H if H else 0

    def benchmark(v,g,a):
        if v <= g: return "🟢 Good"
        elif v <= a: return "🟡 Avg"
        else: return "🔴 Poor"

    st.subheader("📊 KPIs")

    c1,c2,c3 = st.columns(3)
    c1.metric("TRIR", round(TRIR,2), benchmark(TRIR,1,3))
    c2.metric("LTIFR", round(LTIFR,2), benchmark(LTIFR,0.5,1.5))
    c3.metric("Severity", round(SR,2), benchmark(SR,50,200))

# ---------------- CHARTS ----------------
if not df.empty:

    st.subheader("📈 Charts")

    if "Risk" in df.columns:
        st.plotly_chart(px.histogram(df,x="Risk"), use_container_width=True)

    if "Hazard Type" in df.columns:
        st.plotly_chart(px.pie(df,names="Hazard Type"), use_container_width=True)

# ---------------- ML PREDICTION ----------------
if not df.empty and date_col and incident_col:

    temp = df.copy()
    temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
    temp = temp.dropna()

    temp["t"] = range(len(temp))

    model = LinearRegression()
    model.fit(temp[["t"]], temp[incident_col])

    pred = model.predict([[len(temp)+1]])[0]

    st.subheader("📉 Prediction")
    st.write(f"Next incidents prediction: {round(pred,2)}")

# ---------------- AI ASSISTANT ----------------
st.subheader("🤖 AI Assistant")

question = st.text_input("Ask about your data")

if question and not df.empty:

    sample = df.head(50).to_csv(index=False)

    prompt = f"""
You are an HSE expert.

KPIs:
TRIR: {TRIR}
LTIFR: {LTIFR}
Severity: {SR}

Dataset:
{sample}

Question:
{question}

Give insights and recommendations.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}]
        )
        st.write(response.choices[0].message.content)

    except Exception as e:
        st.error(e)

# ---------------- AI PDF REPORT ----------------
if not df.empty and st.button("📄 Generate AI Inspection Report"):

    with st.spinner("Generating report..."):

        sample = df.head(50).to_csv(index=False)

        prompt = f"""
Generate a professional HSE inspection report.

KPIs:
TRIR: {TRIR}
LTIFR: {LTIFR}
Severity: {SR}

Dataset:
{sample}

Include summary, findings, risks, causes, recommendations.
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role":"user","content":prompt}]
            )

            report = response.choices[0].message.content

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)

            for line in report.split("\n"):
                pdf.multi_cell(0,6,line)

            file_path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
            pdf.output(file_path)

            with open(file_path, "rb") as f:
                st.download_button("Download Report", f, "HSE_Report.pdf")

        except Exception as e:
            st.error(e)
