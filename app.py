import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
from openai import OpenAI
from sklearn.linear_model import LinearRegression

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
        return res.choices[0].message.content, True
    except Exception as e:
        if "quota" in str(e).lower():
            return "⚠️ AI unavailable (quota exceeded)", False
        return str(e), False

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
file = st.sidebar.file_uploader("Upload Data", type=["csv","xlsx"])

# ---------------- LOAD DATA ----------------
df = pd.DataFrame()

if file:
    try:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")
        st.success("✅ Data uploaded")
        st.write(df.head())
    except Exception as e:
        st.error(e)
        st.stop()

# ---------------- FILTERS ----------------
df_filtered = df.copy()

if not df.empty:

    st.sidebar.markdown("### 🎛 Filters")

    # DATE
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        df_filtered[date_col] = pd.to_datetime(df_filtered[date_col], errors="coerce")
        min_d = df_filtered[date_col].min()
        max_d = df_filtered[date_col].max()

        date_range = st.sidebar.date_input("Date Range", [min_d, max_d])

        if len(date_range) == 2:
            df_filtered = df_filtered[
                (df_filtered[date_col] >= pd.to_datetime(date_range[0])) &
                (df_filtered[date_col] <= pd.to_datetime(date_range[1]))
            ]

    # LOCATION
    if "Location" in df.columns:
        loc = st.sidebar.multiselect("Location", df["Location"].unique())
        if loc:
            df_filtered = df_filtered[df_filtered["Location"].isin(loc)]

    # RISK
    if "Risk" in df.columns:
        risk = st.sidebar.multiselect("Risk", df["Risk"].unique())
        if risk:
            df_filtered = df_filtered[df_filtered["Risk"].isin(risk)]

    # HAZARD
    if "Hazard Type" in df.columns:
        haz = st.sidebar.multiselect("Hazard", df["Hazard Type"].unique())
        if haz:
            df_filtered = df_filtered[df_filtered["Hazard Type"].isin(haz)]

    st.sidebar.write(f"Records after filter: {len(df_filtered)}")

# ---------------- KPI ----------------
if not df_filtered.empty:

    def detect(keys):
        for col in df_filtered.columns:
            for k in keys:
                if k.lower() in col.lower():
                    return col
        return None

    hours = detect(["hours"])
    incidents = detect(["incident"])
    lti = detect(["lost time"])
    lost_days = detect(["lost days"])
    date_col = detect(["date"])

    def safe(col):
        return pd.to_numeric(df_filtered[col], errors="coerce").sum() if col else 0

    H = safe(hours)
    R = safe(incidents)
    LTI = safe(lti)
    LD = safe(lost_days)

    TRIR = (R*200000)/H if H else 0
    LTIFR = (LTI*1000000)/H if H else 0
    SR = (LD*200000)/H if H else 0

    st.title("🛡️ OSHE Master Dashboard")

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

    # Charts
    if "Hazard Type" in df_filtered.columns:
        st.plotly_chart(px.pie(df_filtered,names="Hazard Type"),use_container_width=True)

    if "Risk" in df_filtered.columns:
        st.plotly_chart(px.histogram(df_filtered,x="Risk"),use_container_width=True)

    if "Location" in df_filtered.columns and "Hazard Type" in df_filtered.columns:
        heat = pd.crosstab(df_filtered["Location"], df_filtered["Hazard Type"])
        st.plotly_chart(px.imshow(heat, text_auto=True),use_container_width=True)

    # Prediction
    if date_col and incidents:
        try:
            temp=df_filtered.copy()
            temp[date_col]=pd.to_datetime(temp[date_col],errors="coerce")
            temp=temp.dropna()
            if len(temp)>2:
                temp["t"]=range(len(temp))
                model=LinearRegression().fit(temp[["t"]],temp[incidents])
                pred=model.predict([[len(temp)+1]])[0]
                st.write("📉 Next incidents:",round(pred,2))
        except:
            pass

# ---------------- AI ----------------
st.subheader("🤖 AI Assistant")

q = st.text_input("Ask")

if q and not df_filtered.empty:
    sample=df_filtered.head(50).to_csv(index=False)
    ans,ok=ask_ai("Analyze:\n"+sample+"\nQ:"+q)
    st.success(ans) if ok else st.warning(ans)

# ---------------- ROOT CAUSE ----------------
if not df_filtered.empty and "Risk" in df_filtered.columns:
    hr=df_filtered[df_filtered["Risk"].astype(str).str.contains("high",case=False)]
    if len(hr)>0:
        if st.button("Analyze Root Cause"):
            sample=hr.head(30).to_csv(index=False)
            ans,ok=ask_ai("Root cause:\n"+sample)
            st.write(ans if ok else "Improve controls")

# ---------------- CHECKLIST ----------------
if not df_filtered.empty and "Hazard Type" in df_filtered.columns:
    hazards=df_filtered["Hazard Type"].dropna().unique()
    st.dataframe(pd.DataFrame([{"Hazard":h,"Check":f"Control for {h}"} for h in hazards]))

# ---------------- PDF ----------------
if not df_filtered.empty and st.button("📄 Generate Report"):
    sample=df_filtered.head(50).to_csv(index=False)
    report,ok=ask_ai("Report:\n"+sample)
    if not ok: report="Basic report"
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial",size=10)
    for l in report.split("\n"): pdf.multi_cell(0,6,l)
    path=tempfile.NamedTemporaryFile(delete=False).name
    pdf.output(path)
    with open(path,"rb") as f:
        st.download_button("Download Report",f,"report.pdf")
