import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import os

# ---------------- GLOBAL STYLING ----------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        color: white;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #2a5298, #1e3c72);
        color: white;
    }
    .stButton>button {
        background-color: #FFD700;
        color: black;
        font-weight: bold;
        border-radius: 8px;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #FFA500;
        color: white;
    }
    h1, h2, h3 {
        color: #FFD700;
    }
    .stDataFrame {
        background-color: white;
        color: black;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------- LOGIN PAGE ----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown('<h1 style="text-align:center;">🌟 OSHE Master – HSE Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align:center; font-size:16px; color:white;">
        Prepared by:<br>
        Dina Mohamed, Samar Zaiton, Mohamed Gamal, Ahmed Badawy,<br>
        Hazem Hasem, Ahmed Abd Elreheem, Mohamed Abd Elrazkik, Amir Salem
        </div>
    """, unsafe_allow_html=True)

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == "admin" and pwd == "1234":  # Replace with secure auth
            st.session_state.authenticated = True
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")
    st.stop()

# ---------------- SIDEBAR LOGOS ----------------
col1, col2 = st.sidebar.columns([1,1])
with col1:
    if os.path.exists("logo.png"):
        st.image("https://upload.wikimedia.org/wikipedia/en/0/0d/Alexandria_University_logo.png", width=120)
with col2:
    if os.path.exists("جامعة-الإسكندرية-مصر.png"):
        st.image("جامعة-الإسكندرية-مصر.png", use_column_width=True)

st.sidebar.markdown("""
    <div style="text-align:center; color:white; font-size:14px; font-weight:bold;">
    OSHE Master – HSE Dashboard<br>
    University of Alexandria – Egypt
    </div>
""", unsafe_allow_html=True)

# ---------------- FILE UPLOAD ----------------
st.sidebar.header("📂 Upload Data")
file = st.sidebar.file_uploader("Upload Safety Data (CSV/Excel)", type=["csv","xlsx"])
df = pd.DataFrame()
if file:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    st.success("✅ Data uploaded successfully!")
    st.write("Preview:", df.head())

# ---------------- KPIs ----------------
if not df.empty:
    st.header("📊 KPIs")
    st.metric("Total Hazards", len(df))
    if "Severity" in df.columns:
        st.write("Counts by Severity:", df["Severity"].value_counts())
    if "Risk" in df.columns:
        st.write("Counts by Risk:", df["Risk"].value_counts())

# ---------------- CHARTS ----------------
if not df.empty:
    st.header("📈 Charts")
    for col in df.select_dtypes(include="object").columns:
        fig = px.histogram(df, x=col, title=f"Distribution of {col}", color_discrete_sequence=["#FFD700"])
        st.plotly_chart(fig, use_container_width=True)

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        # Pick a numeric column for y-axis
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            fig2 = px.line(df, x="Date", y=numeric_cols[0], title="Trend Over Time", color_discrete_sequence=["#FFA500"])
            st.plotly_chart(fig2, use_container_width=True)

# ---------------- NATURAL LANGUAGE Q&A ----------------
qa_input = st.text_input("💬 Ask a question about incidents")

if file is not None and not df.empty and qa_input:
    location_match = None
    year_match = None

    if "Location" in df.columns:
        for loc in df["Location"].unique():
            if str(loc).lower() in qa_input.lower():
                location_match = loc

    year_match = re.findall(r"\b(20\d{2})\b", qa_input)
    if year_match:
        year_match = int(year_match[0])

    filtered_df = df.copy()
    if location_match:
        filtered_df = filtered_df[filtered_df["Location"].str.contains(location_match, case=False)]
    if year_match and "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        filtered_df = filtered_df[filtered_df["Date"].dt.year == year_match]

    if not filtered_df.empty:
        st.subheader(f"Results for query: {qa_input}")
        st.dataframe(filtered_df)
        if "Hazard Type" in filtered_df.columns:
            fig = px.bar(filtered_df, x="Hazard Type", title="Hazards by Type", color_discrete_sequence=["#FFD700"])
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No matching records found.")

# ---------------- FOOTER LOGOS ----------------
st.markdown("""
    <hr style="border:1px solid #FFD700;">
    <div style="text-align:center;">
        <img src="logo.png" width="100">
        <img src="جامعة-الإسكندرية-مصر.png" width="100" style="margin-left:20px;">
        <p style="color:white; font-size:12px;">
        © 2026 OSHE Master – HSE Dashboard | University of Alexandria
        </p>
    </div>
""", unsafe_allow_html=True)
