import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

# ---------------- LOGIN ----------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 HSE Dashboard Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if user == "admin" and pwd == "1234":  # Replace with secure auth
            st.session_state.authenticated = True
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")
    st.stop()

# ---------------- LANDING PAGE ----------------
st.markdown("""
# 🌟 Created by Amir Salem  
### Under supervision of Prof. Dr. [Name]  
**OSHE Master & HSE Dashboard**
""")

# ---------------- FILE UPLOAD ----------------
file = st.file_uploader("Upload Safety Data (CSV/Excel)", type=["csv","xlsx"])
if file:
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    st.success("✅ Data uploaded successfully!")
    st.write("Preview:", df.head())

    # ---------------- DATE FILTER ----------------
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        min_date, max_date = df["Date"].min(), df["Date"].max()
        start, end = st.date_input("Filter by Date Range", [min_date, max_date])
        df = df[(df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))]

    # ---------------- KPIs ----------------
    st.subheader("📊 KPIs")
    st.metric("Total Hazards", len(df))
    if "Severity" in df.columns:
        st.write("Counts by Severity:", df["Severity"].value_counts())
    if "Risk" in df.columns:
        st.write("Counts by Risk:", df["Risk"].value_counts())

    # OSHA TRIR Example (dummy Hours Worked)
    hours_worked = 200000
    recordable_cases = len(df[df["Severity"].str.contains("Recordable", case=False)]) if "Severity" in df.columns else 0
    trir = (recordable_cases * 200000) / hours_worked
    st.metric("OSHA TRIR", f"{trir:.2f}")

    # ---------------- CHARTS ----------------
    st.subheader("📈 Charts")
    for col in df.select_dtypes(include="object").columns:
        fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        st.plotly_chart(fig)

    if "Date" in df.columns:
        fig2 = px.line(df, x="Date", y=df.columns[1], title="Trend Over Time")
        st.plotly_chart(fig2)

    # Heatmap for location hazards
    if "Location" in df.columns and "Severity" in df.columns:
        pivot = pd.crosstab(df["Location"], df["Severity"])
        fig, ax = plt.subplots()
        sns.heatmap(pivot, annot=True, cmap="Reds", ax=ax)
        st.pyplot(fig)

    # Risk Matrix
    if "Likelihood" in df.columns and "Severity" in df.columns:
        fig3 = px.scatter(df, x="Likelihood", y="Severity", color="Risk", title="Risk Matrix")
        st.plotly_chart(fig3)

    # ---------------- AI INSIGHTS ----------------
    st.subheader("🤖 AI Insights")
    if "Hazard Type" in df.columns:
        common_hazard = df["Hazard Type"].mode()[0]
        st.write(f"Most common hazard: {common_hazard}")

    # Predictive modeling (simple demo)
    if "Severity" in df.columns:
        le = LabelEncoder()
        df["Severity_enc"] = le.fit_transform(df["Severity"].astype(str))
        X = df[["Severity_enc"]]
        y = (df["Severity_enc"] > 1).astype(int)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        model = LogisticRegression().fit(X_train, y_train)
        st.write("Prediction sample:", model.predict(X_test[:5]))

from transformers import pipeline
import re

# ---------------- NATURAL LANGUAGE Q&A ----------------
st.subheader("💬 Natural Language Q&A")

qa_input = st.text_input("Ask a question about incidents (e.g., 'Show me incidents in Port Said last year')")

if qa_input and not df.empty:
    # Simple keyword extraction
    location_match = None
    date_match = None

    # Extract location if present
    if "Location" in df.columns:
        for loc in df["Location"].unique():
            if str(loc).lower() in qa_input.lower():
                location_match = loc

    # Extract year if mentioned
    year_match = re.findall(r"\b(20\d{2})\b", qa_input)
    if year_match:
        date_match = int(year_match[0])

    # Apply filters
    filtered_df = df.copy()
    if location_match:
        filtered_df = filtered_df[filtered_df["Location"].str.contains(location_match, case=False)]
    if date_match and "Date" in df.columns:
        filtered_df = filtered_df[filtered_df["Date"].dt.year == date_match]

    # Display results
    if not filtered_df.empty:
        st.write(f"Results for query: {qa_input}")
        st.dataframe(filtered_df)
        # Optional chart
        if "Hazard Type" in filtered_df.columns:
            fig = px.bar(filtered_df, x="Hazard Type", title="Hazards by Type")
            st.plotly_chart(fig)
    else:
        st.warning("No matching records found.")


    # ---------------- PDF EXPORT ----------------
    if st.button("📄 Generate PDF Report"):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, 800, "Company HSE Report / تقرير السلامة")
        c.setFont("Helvetica", 10)
        c.drawString(50, 780, f"Prepared by Amir Salem - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(50, 760, f"Total Hazards: {len(df)}")
        c.drawString(50, 740, f"OSHA TRIR: {trir:.2f}")
        c.showPage()
        c.save()
        st.download_button("Download PDF", buffer.getvalue(), "HSE_Report.pdf")
