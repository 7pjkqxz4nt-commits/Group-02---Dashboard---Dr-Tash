import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="OSHE Master", layout="wide")

# ---------------- GLOBAL STYLE ----------------
st.markdown("""
<style>

/* Background */
.stApp {
    background: linear-gradient(to right, #203a43, #2c5364);
    color: white;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #1c2b36;
}

/* Cards */
.card {
    background: white;
    color: black;
    padding: 20px;
    border-radius: 15px;
    box-shadow: 0px 5px 15px rgba(0,0,0,0.2);
    margin-bottom: 20px;
}

/* Buttons */
.stButton>button {
    background-color: #f1c40f;
    color: black;
    font-weight: bold;
    border-radius: 8px;
}

/* Header */
.header {
    text-align: center;
    margin-bottom: 20px;
}

/* Footer */
.footer {
    text-align: center;
    margin-top: 40px;
    font-size: 12px;
    color: #ccc;
}

</style>
""", unsafe_allow_html=True)

# ---------------- SESSION ----------------
if "auth" not in st.session_state:
    st.session_state.auth = False

# ---------------- LOGIN ----------------
if not st.session_state.auth:

    st.markdown("""
    <div style="width:400px;margin:auto;margin-top:100px;
    background:white;color:black;padding:30px;border-radius:15px;text-align:center;">
    
    <img src="https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png" width="80">
    <h2>OSHE Master</h2>
    <p>HSE Dashboard</p>
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

st.sidebar.markdown("---")
file = st.sidebar.file_uploader("📂 Upload Data", type=["csv", "xlsx"])

# ---------------- HEADER ----------------
st.markdown("""
<div class="header">
<h1>🛡️ OSHE Master Dashboard</h1>
<p>University of Alexandria - Egypt</p>
</div>
""", unsafe_allow_html=True)

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

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 KPIs")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Records", len(df))

    if "Severity" in df.columns:
        col2.metric("Unique Severity", df["Severity"].nunique())

    if "Risk" in df.columns:
        col3.metric("Unique Risk Levels", df["Risk"].nunique())

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- CHARTS ----------------
if not df.empty:

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📈 Charts")

    for col in df.select_dtypes(include="object").columns[:3]:
        fig = px.histogram(df, x=col, title=f"{col} Distribution",
                           color_discrete_sequence=["#f1c40f"])
        st.plotly_chart(fig, use_container_width=True)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        num_cols = df.select_dtypes(include="number").columns

        if len(num_cols) > 0:
            fig2 = px.line(df, x="Date", y=num_cols[0],
                           title="Trend Over Time",
                           color_discrete_sequence=["#e67e22"])
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Q&A ----------------
query = st.text_input("💬 Ask a question about incidents")

if not df.empty and query:

    filtered_df = df.copy()

    if "Location" in df.columns:
        for loc in df["Location"].unique():
            if str(loc).lower() in query.lower():
                filtered_df = filtered_df[filtered_df["Location"] == loc]

    year_match = re.findall(r"\b(20\d{2})\b", query)
    if year_match and "Date" in df.columns:
        filtered_df = filtered_df[
            pd.to_datetime(filtered_df["Date"], errors="coerce").dt.year == int(year_match[0])
        ]

    if not filtered_df.empty:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔎 Results")
        st.dataframe(filtered_df)

        if "Hazard Type" in filtered_df.columns:
            fig = px.bar(filtered_df, x="Hazard Type",
                         color_discrete_sequence=["#f1c40f"])
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("No matching results")

# ---------------- FOOTER ----------------
st.markdown("""
<div class="footer">
© 2026 OSHE Master – HSE Dashboard | University of Alexandria
</div>
""", unsafe_allow_html=True)
