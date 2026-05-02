import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------- LOAD DATA ----------------
df = pd.read_csv("your_file.csv")  # replace with your dataset

# ---------------- HELPER ----------------
def detect(keys):
    for col in df.columns:
        for k in keys:
            if k.lower() in col.lower():
                return col
    return None

def safe(df, col):
    return pd.to_numeric(df[col], errors="coerce").sum() if col else 0

# ---------------- KPI CALC ----------------
hours = detect(["hours"])
incidents = detect(["incident"])
lti = detect(["lost time"])
lost_days = detect(["lost days"])

def calculate_kpis(data):
    H = safe(data, hours)
    R = safe(data, incidents)
    LTI = safe(data, lti)
    LD = safe(data, lost_days)

    TRIR = (R*200000)/H if H else 0
    LTIFR = (LTI*1000000)/H if H else 0
    SR = (LD*200000)/H if H else 0

    return TRIR, LTIFR, SR

# ---------------- APP ----------------
app = dash.Dash(__name__)

# ---------------- LAYOUT ----------------
app.layout = html.Div([

    # Sidebar
    html.Div([
        html.H3("📂 Filters"),
        dcc.Dropdown(
            id="risk_filter",
            options=[{"label": i, "value": i} for i in df["Risk"].dropna().unique()],
            multi=True,
            placeholder="Select Risk"
        ),
        dcc.Dropdown(
            id="hazard_filter",
            options=[{"label": i, "value": i} for i in df["Hazard Type"].dropna().unique()],
            multi=True,
            placeholder="Select Hazard"
        ),
    ], style={
        "width": "20%",
        "display": "inline-block",
        "verticalAlign": "top",
        "padding": "20px",
        "background": "#f4f6f9"
    }),

    # Main
    html.Div([

        html.H1("🛡️ OSHE Master Dashboard"),

        # KPI Cards
        html.Div(id="kpi_cards", style={"display": "flex", "gap": "20px"}),

        # Gauges
        html.Div(id="gauges", style={"display": "flex"}),

        # Charts
        html.Div([
            dcc.Graph(id="risk_chart"),
            dcc.Graph(id="hazard_chart")
        ]),

    ], style={"width": "78%", "display": "inline-block", "padding": "20px"})

])

# ---------------- CALLBACK ----------------
@app.callback(
    Output("kpi_cards", "children"),
    Output("gauges", "children"),
    Output("risk_chart", "figure"),
    Output("hazard_chart", "figure"),
    Input("risk_filter", "value"),
    Input("hazard_filter", "value"),
)
def update_dashboard(risk, hazard):

    dff = df.copy()

    if risk:
        dff = dff[dff["Risk"].isin(risk)]

    if hazard:
        dff = dff[dff["Hazard Type"].isin(hazard)]

    TRIR, LTIFR, SR = calculate_kpis(dff)

    # KPI Cards
    cards = [
        html.Div([html.H4("TRIR"), html.H2(round(TRIR,2))], style=card_style),
        html.Div([html.H4("LTIFR"), html.H2(round(LTIFR,2))], style=card_style),
        html.Div([html.H4("Severity"), html.H2(round(SR,2))], style=card_style),
    ]

    # Gauges
    gauges = [
        dcc.Graph(figure=gauge(TRIR, "TRIR", 5)),
        dcc.Graph(figure=gauge(LTIFR, "LTIFR", 3)),
        dcc.Graph(figure=gauge(SR, "Severity", 300)),
    ]

    # Charts
    risk_fig = px.bar(dff["Risk"].value_counts().reset_index(),
                      x="index", y="Risk", title="Risk Distribution")

    hazard_fig = px.pie(dff, names="Hazard Type", title="Hazard Distribution")

    return cards, gauges, risk_fig, hazard_fig

# ---------------- STYLE ----------------
card_style = {
    "background": "white",
    "padding": "20px",
    "borderRadius": "10px",
    "boxShadow": "0px 2px 6px rgba(0,0,0,0.1)",
    "flex": "1",
    "textAlign": "center"
}

def gauge(v,t,m):
    return go.Figure(go.Indicator(
        mode="gauge+number",
        value=v,
        title={'text':t},
        gauge={'axis':{'range':[0,m]}}
    ))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
