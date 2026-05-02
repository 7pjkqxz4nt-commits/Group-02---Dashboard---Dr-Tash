import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import tempfile
from openai import OpenAI
from sklearn.linear_model import LinearRegression

# ---------------- CONFIG ----------------
st.set_page_config(page_title="OSHE Master", layout="wide")

# ---------------- OPENAI ----------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- AI SAFE FUNCTION ----------------
def ask_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content, True
    except Exception as e:
        if "quota" in str(e).lower():
            return "⚠️ AI unavailable (quota exceeded). Showing basic insights.", False
        return f"AI Error: {e}", False

# ---------------- UI ----------------
st.markdown("""
<style>
.stApp {background:#f5f7fb;color:#2c3e50;}
.card {background:white;padding:20px;border-radius:10px;margin-bottom:15px;}
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
        st.write(df.head())

    except Exception as e:
        st.error(e)
        st.stop()

# ---------------- DETECTION ----------------
def detect_column(keys):
    for col in df.columns:
        for k in keys:
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

    st.subheader("📊 KPIs")
    c1,c2,c3 = st.columns(3)
    c1.metric("TRIR", round(TRIR,2))
    c2.metric("LTIFR", round(LTIFR,2))
    c3.metric("Severity", round(SR,2))

# ---------------- CHARTS ----------------
if not df.empty:

    st.subheader("📈 Charts")

    if "Risk" in df.columns:
        st.plotly_chart(px.histogram(df,x="Risk"), use_container_width=True)

    if "Hazard Type" in df.columns:
        st.plotly_chart(px.pie(df,names="Hazard Type"), use_container_width=True)

# ---------------- PREDICTION ----------------
if not df.empty and date_col and incident_col:

    try:
        temp = df.copy()
        temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
        temp = temp.dropna()

        if len(temp) > 2:
            temp["t"] = range(len(temp))

            model = LinearRegression()
            model.fit(temp[["t"]], temp[incident_col])

            pred = model.predict([[len(temp)+1]])[0]

            st.subheader("📉 Prediction")
            st.write(f"Next incidents: {round(pred,2)}")
    except:
        pass

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
"""

    answer, ok = ask_ai(prompt)

    if ok:
        st.success(answer)
    else:
        st.warning(answer)

        # fallback insights
        if "Risk" in df.columns:
            st.write("High risk cases:",
                     df["Risk"].astype(str).str.contains("high", case=False).sum())

# ---------------- PDF REPORT ----------------
if not df.empty and st.button("📄 Generate Report"):

    sample = df.head(50).to_csv(index=False)

    prompt = f"Generate HSE report:\n{sample}"

    report, ok = ask_ai(prompt)

    if not ok:
        report = "Basic report: Improve safety controls."

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    for line in report.split("\n"):
        pdf.multi_cell(0,6,line)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf").name
    pdf.output(path)

    with open(path,"rb") as f:
        st.download_button("Download Report", f, "report.pdf")
