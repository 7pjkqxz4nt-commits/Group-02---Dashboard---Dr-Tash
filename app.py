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

client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

# ---------------- AI SAFE FUNCTION ----------------
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

/* Global */
.stApp {
    background-color: #f4f6f9;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #ddd;
}

/* KPI Cards */
.kpi-card {
    background: white;
    padding: 20px;
    border-radius: 12px;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.08);
    text-align: center;
}

/* Titles */
h1, h2, h3 {
    color: #1f4e79;
}

/* Buttons */
button {
    border-radius: 8px !important;
}

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

st.sidebar.markdown("## 🛡️ OSHE Master")
st.sidebar.markdown("HSE Intelligence Platform")

file = st.sidebar.file_uploader("📂 Upload Data", type=["csv","xlsx"])

st.sidebar.markdown("---")
st.sidebar.markdown("👤 User: Admin")
df = pd.DataFrame()

if file:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")
    # ---------------- LOAD DATA ----------------
if file:
    try:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file, engine="openpyxl")
        st.success("✅ Data uploaded")
        st.write(df.head())
    except Exception as e:
        st.error(e)
        st.stop()    

# ---------------- FILTERS (SAFE) ----------------

if 'df' not in locals() or df.empty:
    df_filtered = pd.DataFrame()
else:
    df_filtered = df.copy()

    st.sidebar.markdown("### 🎛 Filters")

    # -------- DATE --------
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

    # -------- LOCATION --------
    if "Location" in df.columns:
        loc = st.sidebar.multiselect("Location", df["Location"].unique())
        if loc:
            df_filtered = df_filtered[df_filtered["Location"].isin(loc)]

    # -------- RISK --------
    if "Risk" in df.columns:
        risk = st.sidebar.multiselect("Risk", df["Risk"].unique())
        if risk:
            df_filtered = df_filtered[df_filtered["Risk"].isin(risk)]

    # -------- HAZARD --------
    if "Hazard Type" in df.columns:
        haz = st.sidebar.multiselect("Hazard", df["Hazard Type"].unique())
        if haz:
            df_filtered = df_filtered[df_filtered["Hazard Type"].isin(haz)]

    st.sidebar.write(f"Filtered rows: {len(df_filtered)}")

    # -------- SHOW FILTERED DATA --------
    st.sidebar.markdown(f"📊 Records after filter: {len(df_filtered)}")

else:
   df_filtered = df.copy()


# ---------------- HELPERS ----------------
def detect_column(keys):
    for col in df.columns:
        for k in keys:
            if k.lower() in col.lower():
                return col
    return None

def safe_sum(col):
    return pd.to_numeric(df[col], errors="coerce").sum() if col else 0

# ---------------- ENTERPRISE DASHBOARD ----------------

if not df.empty:

    # -------- KPI CALCULATION --------
    hours = detect_column(["hours"])
    incidents = detect_column(["incident"])
    lti = detect_column(["lost time"])
    lost_days = detect_column(["lost days"])
    date_col = detect_column(["date"])

    H = safe_sum(hours)
    R = safe_sum(incidents)
    LTI = safe_sum(lti)
    LD = safe_sum(lost_days)

    TRIR = (R*200000)/H if H else 0
    LTIFR = (LTI*1000000)/H if H else 0
    SR = (LD*200000)/H if H else 0

    # -------- GAUGE FUNCTION --------
    import plotly.graph_objects as go
    def gauge(v,title,maxv):
        return go.Figure(go.Indicator(
            mode="gauge+number",
            value=v,
            title={'text':title},
            gauge={'axis':{'range':[0,maxv]},
                   'steps':[{'range':[0,maxv*0.3],'color':'green'},
                            {'range':[maxv*0.3,maxv*0.7],'color':'yellow'},
                            {'range':[maxv*0.7,maxv],'color':'red'}]}
        ))

    # -------- TABS --------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Executive Dashboard",
        "📈 Analysis",
        "🤖 AI Insights",
        "🧠 Audit & Investigation"
    ])

    # ================= TAB 1 =================
    with tab1:

        st.subheader("📊 KPI Overview")

        c1, c2, c3 = st.columns(3)
        c1.metric("TRIR", round(TRIR,2))
        c2.metric("LTIFR", round(LTIFR,2))
        c3.metric("Severity", round(SR,2))

        st.subheader("🎯 KPI Gauges")

        g1, g2, g3 = st.columns(3)
        g1.plotly_chart(gauge(TRIR,"TRIR",5), use_container_width=True)
        g2.plotly_chart(gauge(LTIFR,"LTIFR",3), use_container_width=True)
        g3.plotly_chart(gauge(SR,"Severity",300), use_container_width=True)

    # ================= TAB 2 =================
    with tab2:

        st.subheader("📈 Analysis")

        if "Hazard Type" in df.columns:
            st.plotly_chart(px.pie(df, names="Hazard Type"), use_container_width=True)

        if "Risk" in df.columns:
            st.plotly_chart(px.histogram(df, x="Risk"), use_container_width=True)

        if "Location" in df.columns and "Hazard Type" in df.columns:
            heat = pd.crosstab(df["Location"], df["Hazard Type"])
            st.plotly_chart(px.imshow(heat, text_auto=True), use_container_width=True)

        # Trend
        if date_col and incidents:
            temp = df.copy()
            temp[date_col] = pd.to_datetime(temp[date_col], errors="coerce")
            trend = temp.groupby(date_col)[incidents].sum().reset_index()
            st.plotly_chart(px.line(trend, x=date_col, y=incidents), use_container_width=True)

    # ================= TAB 3 =================
    with tab3:

        st.subheader("🤖 AI Insights")

        q = st.text_input("Ask about your data")

        if q:
            sample = df.head(50).to_csv(index=False)
            prompt = f"Analyze:\n{sample}\nQuestion:{q}"

            ans, ok = ask_ai(prompt)

            if ok:
                st.success(ans)
            else:
                st.warning(ans)

    # ================= TAB 4 =================
    with tab4:

        st.subheader("🧠 Root Cause")

        if "Risk" in df.columns:
            hr = df[df["Risk"].astype(str).str.contains("high", case=False)]

            if len(hr) > 0:
                if st.button("Analyze Root Cause"):
                    sample = hr.head(30).to_csv(index=False)
                    ans, ok = ask_ai("Root cause:\n" + sample)
                    st.write(ans if ok else "Basic: improve controls")

        st.subheader("📋 Checklist")

        if "Hazard Type" in df.columns:
            hazards = df["Hazard Type"].dropna().unique()
            checklist = [{"Hazard": h, "Check": f"Control for {h}"} for h in hazards]
            st.dataframe(pd.DataFrame(checklist))

        st.subheader("📄 Report")

        if st.button("Generate Report"):
            sample = df.head(50).to_csv(index=False)
            report, ok = ask_ai("Report:\n" + sample)

            if not ok:
                report = "Basic report"

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)

            for l in report.split("\n"):
                pdf.multi_cell(0,6,l)

            path = tempfile.NamedTemporaryFile(delete=False).name
            pdf.output(path)

            with open(path, "rb") as f:
                st.download_button("Download Report", f, "report.pdf")

# ---------------- CHARTS ----------------
if not df.empty:

    if "Hazard Type" in df.columns:
        st.plotly_chart(px.pie(df,names="Hazard Type"),use_container_width=True)

    if "Risk" in df.columns:
        st.plotly_chart(px.histogram(df,x="Risk"),use_container_width=True)

    if "Location" in df.columns and "Hazard Type" in df.columns:
        heat = pd.crosstab(df["Location"], df["Hazard Type"])
        st.plotly_chart(px.imshow(heat, text_auto=True), use_container_width=True)

# ---------------- PREDICTION ----------------
if not df.empty and date_col and incidents:
    try:
        temp = df.copy()
        temp[date_col]=pd.to_datetime(temp[date_col],errors="coerce")
        temp=temp.dropna()
        if len(temp)>2:
            temp["t"]=range(len(temp))
            model=LinearRegression().fit(temp[["t"]],temp[incidents])
            pred=model.predict([[len(temp)+1]])[0]
            st.subheader("📉 Prediction")
            st.write("Next incidents:",round(pred,2))
    except:
        pass

# ---------------- AI ----------------
st.subheader("🤖 AI Assistant")
q = st.text_input("Ask")

if q and not df.empty:
    sample=df.head(50).to_csv(index=False)
    prompt=f"Analyze:\n{sample}\nQuestion:{q}"
    ans,ok=ask_ai(prompt)
    if ok:
        st.success(ans)
    else:
        st.warning(ans)

# ---------------- ROOT CAUSE ----------------
if not df.empty and "Risk" in df.columns:
    hr=df[df["Risk"].astype(str).str.contains("high",case=False)]
    if len(hr)>0:
        if st.button("Analyze Root Cause"):
            sample=hr.head(30).to_csv(index=False)
            ans,ok=ask_ai("Root cause:\n"+sample)
            st.write(ans if ok else "Basic: improve controls")

# ---------------- CHECKLIST ----------------
if not df.empty and "Hazard Type" in df.columns:
    hazards=df["Hazard Type"].dropna().unique()
    checklist=[{"Hazard":h,"Check":f"Control for {h}"} for h in hazards]
    st.dataframe(pd.DataFrame(checklist))

# ---------------- PDF ----------------
if not df.empty and st.button("📄 Generate Report"):
    sample=df.head(50).to_csv(index=False)
    report,ok=ask_ai("Report:\n"+sample)
    if not ok: report="Basic report"
    pdf=FPDF(); pdf.add_page(); pdf.set_font("Arial",size=10)
    for l in report.split("\n"): pdf.multi_cell(0,6,l)
    path=tempfile.NamedTemporaryFile(delete=False).name
    pdf.output(path)
    with open(path,"rb") as f:
        st.download_button("Download",f,"report.pdf")
