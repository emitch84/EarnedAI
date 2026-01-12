import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.evm_engine import calculate_snapshot_metrics, get_project_s_curve
from src.anomaly_detection import detect_anomalies, get_high_risk_tasks
import os

# --- Configuration ---
st.set_page_config(
    page_title="EarnedAI - Portfolio Controls",
    page_icon="📈",
    layout="wide",
)

# --- Styles ---
st.markdown("""
    <style>
    .metric-card {
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #e6e6e6;
        background: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- Data Loading ---
@st.cache_data
def load_db():
    if not os.path.exists("data/projects.csv"):
        st.error("Data not found. Please run data_generator.py first.")
        return None, None, None
        
    projects = pd.read_csv("data/projects.csv")
    tasks = pd.read_csv("data/tasks.csv")
    logs = pd.read_csv("data/logs.csv")
    
    # Parse dates
    logs["Date"] = pd.to_datetime(logs["Date"])
    tasks["PlannedStart"] = pd.to_datetime(tasks["PlannedStart"])
    tasks["PlannedEnd"] = pd.to_datetime(tasks["PlannedEnd"])
    
    return projects, tasks, logs

projects_df, tasks_df, logs_df = load_db()

# --- Sidebar ---
with st.sidebar:
    st.title("EarnedAI 📈")
    
    # Project Selector
    project_names = projects_df["name"].tolist()
    selected_proj_name = st.selectbox("Select Project", project_names)
    
    # Get ID
    selected_proj_id = projects_df[projects_df["name"] == selected_proj_name]["id"].values[0]
    
    st.markdown("---")
    st.info("Reviewing Portfolio Controls Data.")

# --- Main Logic ---

# 1. Filter Data for selected project
current_tasks = tasks_df[tasks_df["ProjectID"] == selected_proj_id]
current_logs = logs_df[logs_df["ProjectID"] == selected_proj_id]

# 2. Calculate Snapshots
snapshot_df = calculate_snapshot_metrics(current_tasks, current_logs)
snapshot_df = detect_anomalies(snapshot_df)

# 3. Calculate Project Aggregates
total_bac = snapshot_df["BAC"].sum()
total_ev = snapshot_df["EV"].sum()
total_pv = snapshot_df["PV"].sum()
total_ac = snapshot_df["AC"].sum()

cpi = total_ev / total_ac if total_ac > 0 else 1.0
spi = total_ev / total_pv if total_pv > 0 else 1.0
eac = total_bac / cpi if cpi > 0 else total_bac
vac = total_bac - eac

# TCPI for Project
work_remaining = total_bac - total_ev
funds_remaining = total_bac - total_ac
tcpi = work_remaining / funds_remaining if funds_remaining > 0 else 999.0

# Calculate Periodic (e.g., last 30 days) Variance
# We use the logs to find variance in the last reported month
last_log_date = logs_df["Date"].max()
month_start_date = last_log_date - pd.Timedelta(days=30)
recent_logs = logs_df[logs_df["Date"] > month_start_date]
# This simple subtraction of aggregates isn't quite right for "Monthly Delta"
# Better: Get Cumulative 30 days ago vs Cumulative Now.
past_agg = logs_df[(logs_df["ProjectID"] == selected_proj_id) & (logs_df["Date"] <= month_start_date)]
past_ev = past_agg.groupby("TaskID")["EV"].max().sum() if not past_agg.empty else 0
past_ac = past_agg.groupby("TaskID")["AC"].max().sum() if not past_agg.empty else 0
past_pv = past_agg.groupby("TaskID")["PV"].max().sum() if not past_agg.empty else 0

period_ev = total_ev - past_ev
period_ac = total_ac - past_ac
period_pv = total_pv - past_pv

period_cv = period_ev - period_ac
period_sv = period_ev - period_pv
baseline_finish = tasks_df[tasks_df["ProjectID"] == selected_proj_id]["PlannedEnd"].max()

# Period Indices
period_cpi = period_ev / period_ac if period_ac > 0 else 1.0
period_spi = period_ev / period_pv if period_pv > 0 else 1.0

# --- Dashboard Header ---
st.title(f"{selected_proj_name}")

# Row 1: High Level Totals & Forecasts
r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
with r1_c1:
    st.metric("Budget (BAC)", f"${total_bac:,.0f}")
with r1_c2:
    st.metric("Baseline Finish", baseline_finish.strftime("%Y-%m-%d"))
with r1_c3:
    st.metric("EAC (Forecast)", f"${eac:,.0f}", delta=f"${vac:,.0f}", delta_color="normal")
with r1_c4:
    st.metric("TCPI (To Finish)", f"{tcpi:.2f}")

st.markdown("---")

# Previous Period (Day -60 to -30) for Trend Analysis
prev_month_start = month_start_date - pd.Timedelta(days=30)
prev_agg = logs_df[(logs_df["ProjectID"] == selected_proj_id) & (logs_df["Date"] <= prev_month_start)]
prev_ev_cum = prev_agg.groupby("TaskID")["EV"].max().sum() if not prev_agg.empty else 0
prev_ac_cum = prev_agg.groupby("TaskID")["AC"].max().sum() if not prev_agg.empty else 0
prev_pv_cum = prev_agg.groupby("TaskID")["PV"].max().sum() if not prev_agg.empty else 0

# Previous Period Metrics
prev_period_ev = past_ev - prev_ev_cum
prev_period_ac = past_ac - prev_ac_cum
prev_period_pv = past_pv - prev_pv_cum

prev_period_cv = prev_period_ev - prev_period_ac
prev_period_sv = prev_period_ev - prev_period_pv

# Row 2: Current Period Performance (Last 30 Days)
st.subheader("Current Period Performance (Last 30 Days)")
r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
with r2_c1:
    st.metric("CPI (Current)", f"{period_cpi:.3f}", delta=f"{period_cpi - 1.0:.2f}", help="Efficiency in the last 30 days")
with r2_c2:
    st.metric("SPI (Current)", f"{period_spi:.3f}", delta=f"{period_spi - 1.0:.2f}", help="Schedule efficiency in the last 30 days")
with r2_c3:
    st.metric("CV (Current)", f"${period_cv:,.0f}", delta=f"{period_cv - prev_period_cv:,.0f} vs prev", delta_color="normal" if (period_cv - prev_period_cv) >= 0 else "inverse")
with r2_c4:
    st.metric("SV (Current)", f"${period_sv:,.0f}", delta=f"{period_sv - prev_period_sv:,.0f} vs prev", delta_color="normal" if (period_sv - prev_period_sv) >= 0 else "inverse")

# Row 3: Cumulative Performance (Project to Date)
st.subheader("Cumulative Performance (Project To Date)")
r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
with r3_c1:
    st.metric("CPI (Cumulative)", f"{cpi:.3f}", delta=f"{cpi-1.0:.2f}")
with r3_c2:
    st.metric("SPI (Cumulative)", f"{spi:.3f}", delta=f"{spi-1.0:.2f}")
with r3_c3:
    total_cv = total_ev - total_ac
    st.metric("CV (Cumulative)", f"${total_cv:,.0f}", delta=f"${period_cv:,.0f}", delta_color="normal" if period_cv >= 0 else "inverse")
with r3_c4:
    total_sv = total_ev - total_pv
    st.metric("SV (Cumulative)", f"${total_sv:,.0f}", delta=f"${period_sv:,.0f}", delta_color="normal" if period_sv >= 0 else "inverse")

# --- Tabs ---
t_perf, t_risk, t_details = st.tabs(["📈 Performance & Trends", "🚨 Risk & Anomalies", "📋 WBS Detail"])

with t_perf:
    st.subheader("Project S-Curves")
    
    # Generate S-Curve Data
    # 1. Historical Actuals (EV, AC)
    s_curve_df = get_project_s_curve(current_logs, selected_proj_id)
    
    # 2. Full Baseline (PV)
    from src.evm_engine import generate_baseline_curve
    baseline_df = generate_baseline_curve(tasks_df, selected_proj_id)
    
    fig_s = go.Figure()
    # Baseline covers entire project duration
    fig_s.add_trace(go.Scatter(x=baseline_df["Date"], y=baseline_df["Cumulative_PV"], mode='lines', name='Planned Value (PV)', line=dict(dash='dash', color='gray')))

    fig_s.add_trace(go.Scatter(x=s_curve_df["Date"], y=s_curve_df["EV"], mode='lines+markers', name='Earned Value (EV)', line=dict(color='green')))
    fig_s.add_trace(go.Scatter(x=s_curve_df["Date"], y=s_curve_df["AC"], mode='lines+markers', name='Actual Cost (AC)', line=dict(color='red')))
    
    fig_s.update_layout(title="Cumulative Cost/Value over Time", template="plotly_white", hovermode="x unified")
    
    # --- AI Integration Step ---
    from src.ai_forecaster import forecast_project_performance
    
    ai_eac, ai_end_date, ai_forecast_df, ai_conf = forecast_project_performance(logs_df, selected_proj_id, total_bac)
    
    if ai_forecast_df is not None and not ai_forecast_df.empty:
        # Plot AI Projections
        fig_s.add_trace(go.Scatter(
            x=ai_forecast_df["Date"], y=ai_forecast_df["Forecast_EV"], 
            mode='lines', name='AI Predicted EV', 
            line=dict(color='green', dash='dot', width=1)
        ))
        fig_s.add_trace(go.Scatter(
            x=ai_forecast_df["Date"], y=ai_forecast_df["Forecast_AC"], 
            mode='lines', name='AI Predicted AC', 
            line=dict(color='red', dash='dot', width=1)
        ))
        
        # Display AI Metrics Callout
        st.markdown("#### 🤖 AI Predictive Insights")
        ai_col1, ai_col2, ai_col3 = st.columns(3)
        with ai_col1:
            st.metric("AI Predicted EAC", f"${ai_eac:,.0f}", delta=f"${total_bac - ai_eac:,.0f}", help="Based on Ridge Regression of historical run rates.")
        with ai_col2:
            st.metric("Predicted Finish", ai_end_date.strftime("%Y-%m-%d"), help="Estimated date when EV will reach BAC.")
        with ai_col3:
            st.metric("Model Confidence", f"{ai_conf:.1%}", help="R2 Score of the regression fit.")

    st.plotly_chart(fig_s, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Efficiency Trend (CPI & SPI)")
        
        # Calculate weekly CPI/SPI from cumulative logs
        s_curve_df["Weekly_CPI"] = s_curve_df.apply(lambda x: x["EV"]/x["AC"] if x["AC"]>0 else 1, axis=1)
        s_curve_df["Weekly_SPI"] = s_curve_df.apply(lambda x: x["EV"]/x["PV"] if x["PV"]>0 else 1, axis=1)
        
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=s_curve_df["Date"], y=s_curve_df["Weekly_CPI"], name="CPI", line=dict(color='blue')))
        fig_trend.add_trace(go.Scatter(x=s_curve_df["Date"], y=s_curve_df["Weekly_SPI"], name="SPI", line=dict(color='orange')))
        fig_trend.add_hline(y=1.0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_b:
        st.subheader("Variance Analysis")
        # Plot Variance (CV and SV) over time
        s_curve_df["Cum_CV"] = s_curve_df["EV"] - s_curve_df["AC"]
        s_curve_df["Cum_SV"] = s_curve_df["EV"] - s_curve_df["PV"]
        
        fig_var = go.Figure()
        fig_var.add_trace(go.Bar(x=s_curve_df["Date"], y=s_curve_df["Cum_CV"], name="Cost Variance ($)", marker_color='blue'))
        fig_var.add_trace(go.Scatter(x=s_curve_df["Date"], y=s_curve_df["Cum_SV"], name="Schedule Variance ($)", line=dict(color='orange')))
        st.plotly_chart(fig_var, use_container_width=True)

with t_risk:
    risks = get_high_risk_tasks(snapshot_df[snapshot_df["Anomaly_Score"] > 0])
    
    st.write(f"Detected {len(risks)} tasks with attention flags.")
    
    for i, row in risks.iterrows():
        with st.container():
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.markdown(f"**{row['TaskName']}** (ID: {row['TaskID']})")
                st.warning(f"Reason: {row['Anomaly_Explanation']}")
            with c2:
                tcpi_val = row["TCPI"]
                if tcpi_val >= 999: # Sentinel for infinite/over budget
                    st.metric("TCPI (Recovery)", "N/A", delta="Budget Broken", delta_color="inverse")
                elif tcpi_val > 1.2:
                    st.metric("TCPI (Recovery)", f"{tcpi_val:.2f}", delta="Unrealistic", delta_color="inverse")
                else: 
                     st.metric("TCPI (Recovery)", f"{tcpi_val:.2f}")
            with c3:
                st.metric("CPI", f"{row['CPI']:.3f}")
            st.divider()

with t_details:
    # Prepare display dataframe to handle "Over Budget" strings
    display_df = snapshot_df.copy()
    display_df["TCPI"] = display_df["TCPI"].apply(lambda x: "Budget Exceeded" if x >= 100 else "{:.2f}".format(x))
    
    st.dataframe(
        display_df[["TaskID", "TaskName", "Status", "PV", "EV", "AC", "CPI", "SPI", "TCPI", "BAC", "EAC", "VAC"]].style.format({
            "CPI": "{:.2f}", "SPI": "{:.2f}", 
            "BAC": "${:,.0f}", "EAC": "${:,.0f}", "VAC": "${:,.0f}",
            "PV": "${:,.0f}", "EV": "${:,.0f}", "AC": "${:,.0f}"
        }),
        use_container_width=True
    )
