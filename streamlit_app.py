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



# Previous Period (Day -60 to -30) for Trend Analysis
prev_month_start = month_start_date - pd.Timedelta(days=30)
prev_agg = logs_df[(logs_df["ProjectID"] == selected_proj_id) & (logs_df["Date"] <= prev_month_start)]
prev_ev_cum = prev_agg.groupby("TaskID")["EV"].max().sum() if not prev_agg.empty else 0
prev_ac_cum = prev_agg.groupby("TaskID")["AC"].max().sum() if not prev_agg.empty else 0
prev_pv_cum = prev_agg.groupby("TaskID")["PV"].max().sum() if not prev_agg.empty else 0

# --- Custom CSS for condensed "HUD" and styled Tabs ---
st.markdown("""
<style>
    /* Metric HUD Container - Dark/Light Mode Compatible */
    .hud-container {
        background-color: var(--secondary-background-color);
        padding: 15px 20px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        margin-bottom: 25px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .hud-row {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
        gap: 15px;
    }
    .hud-row:last-child { margin-bottom: 0; }
    
    .hud-metric {
        flex: 1;
        background: var(--background-color);
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid rgba(128, 128, 128, 0.2);
        text-align: center;
        min-width: 100px;
    }
    .hud-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .hud-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-color);
    }
    .hud-delta {
        font-size: 0.7rem;
        margin-top: 2px;
        font-weight: 500;
    }
    /* Adjusted colors for better visibility on both backgrounds */
    .delta-pos { color: #28a745; } /* Green */
    .delta-neg { color: #dc3545; } /* Red */
    .delta-neu { color: #6c757d; } /* Grey */
    
    .hud-divider {
        border-top: 1px dashed rgba(128, 128, 128, 0.3);
        margin: 10px 0;
    }
    .hud-section-header {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--text-color);
        opacity: 0.9;
        margin-bottom: 8px;
        text-align: left;
    }

    /* Enhanced Tab Styling - Dark Mode Ready */
    div[data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    button[data-baseweb="tab"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        color: var(--text-color);
        border-radius: 6px;
        padding: 8px 16px;
        font-size: 0.9rem;
        font-weight: 600;
        height: auto;
    }
    button[data-baseweb="tab"]:hover {
        border-color: rgba(128, 128, 128, 0.5);
        background-color: var(--background-color);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: rgba(128, 128, 128, 0.1);
        border-color: var(--primary-color);
        color: var(--primary-color);
        font-weight: 700;
    }
    /* Mobile Responsive Adjustments */
    @media (max-width: 768px) {
        .hud-row {
            flex-wrap: wrap;
        }
        .hud-metric {
            min-width: 45%; /* 2 per row on mobile */
            margin-bottom: 8px;
        }
        .hud-col {
            min-width: 100% !important;
            margin: 0 !important;
            margin-bottom: 20px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Helper to format delta HTML
def fmt_delta(val, suffix="", inverse=False):
    if val is None: return ""
    color = "delta-neu"
    if val > 0: color = "delta-neg" if inverse else "delta-pos"
    elif val < 0: color = "delta-pos" if inverse else "delta-neg"
    
    sign = "+" if val > 0 else ""
    return f'<div class="hud-delta {color}">{sign}{val:,.0f}{suffix}</div>' if isinstance(val, (int, float)) and abs(val) > 0.001 else ""

def fmt_idx_delta(val): # For CPI/SPI
    color = "delta-pos" if val >= 0 else "delta-neg"
    sign = "+" if val > 0 else ""
    return f'<div class="hud-delta {color}">{sign}{val:.2f}</div>'

# --- HTML HUD Construction ---

# Re-calculate Previous Period Metrics (Restored)
prev_month_start = month_start_date - pd.Timedelta(days=30)
prev_agg = logs_df[(logs_df["ProjectID"] == selected_proj_id) & (logs_df["Date"] <= prev_month_start)]
prev_ev_cum = prev_agg.groupby("TaskID")["EV"].max().sum() if not prev_agg.empty else 0
prev_ac_cum = prev_agg.groupby("TaskID")["AC"].max().sum() if not prev_agg.empty else 0
prev_pv_cum = prev_agg.groupby("TaskID")["PV"].max().sum() if not prev_agg.empty else 0

prev_period_ev = past_ev - prev_ev_cum
prev_period_ac = past_ac - prev_ac_cum
prev_period_pv = past_pv - prev_pv_cum

prev_period_cv = prev_period_ev - prev_period_ac
prev_period_sv = prev_period_ev - prev_period_pv

# Cumulative Variances
total_cv = total_ev - total_ac
total_sv = total_ev - total_pv

# Section 1: Top Level Project Stats
top_level_html = f"""<div class="hud-container">
    <div class="hud-row">
        <div class="hud-metric">
            <div class="hud-label">Budget (BAC)</div>
            <div class="hud-value">${total_bac:,.0f}</div>
        </div>
        <div class="hud-metric">
            <div class="hud-label">Forecast (EAC)</div>
            <div class="hud-value">${eac:,.0f}</div>
            {fmt_delta(vac, inverse=False)}
        </div>
        <div class="hud-metric">
            <div class="hud-label">Baseline Finish</div>
            <div class="hud-value">{baseline_finish.strftime('%Y-%m-%d')}</div>
        </div>
        <div class="hud-metric">
            <div class="hud-label">TCPI (To Go)</div>
            <div class="hud-value">{tcpi:.2f}</div>
        </div>
    </div>
    <div class="hud-divider"></div>
    <div class="hud-row">
        <div class="hud-col" style="flex:1; margin-right: 10px;">
            <div class="hud-section-header">Last 30 Days (Trend)</div>
            <div class="hud-row">
                <div class="hud-metric">
                    <div class="hud-label">Period CPI</div>
                    <div class="hud-value">{period_cpi:.2f}</div>
                    {fmt_idx_delta(period_cpi - 1.0)}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Period CV</div>
                    <div class="hud-value">${period_cv:,.0f}</div>
                    {fmt_delta(period_cv - prev_period_cv, " vs prev")}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Period SPI</div>
                    <div class="hud-value">{period_spi:.2f}</div>
                    {fmt_idx_delta(period_spi - 1.0)}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Period SV</div>
                    <div class="hud-value">${period_sv:,.0f}</div>
                    {fmt_delta(period_sv - prev_period_sv, " vs prev")}
                </div>
            </div>
        </div>
        <div class="hud-col" style="flex:1; margin-left: 10px;">
            <div class="hud-section-header">Project To Date</div>
            <div class="hud-row">
                <div class="hud-metric">
                    <div class="hud-label">Cum. CPI</div>
                    <div class="hud-value">{cpi:.2f}</div>
                    {fmt_idx_delta(cpi - 1.0)}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Cum. CV</div>
                    <div class="hud-value">${total_cv:,.0f}</div>
                    {fmt_delta(period_cv)}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Cum. SPI</div>
                    <div class="hud-value">{spi:.2f}</div>
                    {fmt_idx_delta(spi - 1.0)}
                </div>
                <div class="hud-metric">
                    <div class="hud-label">Cum. SV</div>
                    <div class="hud-value">${total_sv:,.0f}</div>
                    {fmt_delta(period_sv)}
                </div>
            </div>
        </div>
    </div>
</div>"""

st.markdown(top_level_html, unsafe_allow_html=True)

# --- Tabs ---
t_perf, t_risk, t_details, t_about, t_raw = st.tabs(["📈 Performance & Trends", "🚨 Risk & Anomalies", "📋 WBS Detail", "ℹ️ About & Features", "💾 Raw Data"])

with t_raw:
    st.subheader("Source Data Inspection")
    st.caption("Review the raw datasets driving this dashboard.")
    
    with st.expander("📂 Task Definitions (Baseline Data)", expanded=True):
        st.dataframe(tasks_df[tasks_df["ProjectID"] == selected_proj_id], use_container_width=True)
        
    with st.expander("📝 Daily Performance Logs (EV/AC/PV)", expanded=False):
        st.dataframe(current_logs.sort_values(by="Date", ascending=False), use_container_width=True)

with t_about:
    st.header("Welcome to EarnedAI")
    st.markdown("""
    **EarnedAI** is a next-generation Project Controls MVP designed to demonstrate how **Artificial Intelligence** and **Advanced Analytics** can transform standard Earned Value Management (EVM).
    
    This portfolio demonstrates a fully local, secure, and clear approach to managing complex project data without relying on external cloud APIs.
    """)
    
    st.divider()
    
    col_feat1, col_feat2 = st.columns(2)
    with col_feat1:
        st.subheader("AI Forecasting Engine")
        st.markdown("""
        The AI Forecaster in **EarnedAI** uses **Machine Learning (Ridge Regression)** to predict the future trajectory of your project. Unlike standard formulas (like `BAC / CPI`) which assume linear performance based on a simple average, this model looks at the **velocity and trend** of your work over time.

        *   **Learning Velocity**: The model looks at every single data point in your project's history (daily EV and AC). It fits a regression line to understand your true "speed" (Earn Rate) and "burn" (Spend Rate).
        *   **Predicting Finish**: It calculates exactly how many days it will take to finish the remaining work (`BAC - Current EV`) if you continue at your current machine-learned velocity.
        *   **Predicting Cost (EAC)**: It then projects your spending forward to that specific finish date to give you a highly accurate **EAC (Estimate at Completion)**.
        *   **Why Ridge?** We use Ridge Regression because it is robust against noise. If you had one bad week, the model won't panic; it smoothes out the trend to find the underlying signal.
        """)
    
    with col_feat2:
        st.subheader("Intelligent Anomaly Detection")
        st.markdown("""
        Don't just look at red/green cells. EarnedAI scans your WBS for specific risk patterns:
        
        *   **Budget Broken:** Detects when a task has physically exceeded its budget.
        *   **Unrealistic Recovery:** Flags tasks where the efficiency needed to finish on time is mathematically improbable (`TCPI > 1.2`), identifying "Death March" tasks early.
        *   **Efficiency Drag:** Clusters tasks that are dragging down the portfolio CPI/SPI.
        """)
        
    st.divider()
    st.subheader("📊 Key Metrics Glossary")
    g_col1, g_col2, g_col3 = st.columns(3)
    with g_col1:
        st.info("**CPI (Cost Performance)**\n\nEfficiency of spend. `1.0` is perfect. `< 1.0` means over budget.")
        st.info("**CV (Cost Variance)**\n\nAbsolute dollar amount over/under budget. Negative is bad.")
    with g_col2:
        st.info("**SPI (Schedule Performance)**\n\nSpeed of execution. `1.0` is on time. `< 1.0` is behind schedule.")
        st.info("**SV (Schedule Variance)**\n\nValue of work ahead/behind schedule in dollars.")
    with g_col3:
        st.info("**TCPI (To Complete)**\n\nThe efficiency required *from now on* to hit the original budget. `> 1.0` means you must work harder.")
        st.info("**EAC (Estimate at Completion)**\n\nThe projected final cost of the project based on current trends.")

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
        st.markdown("#### AI Predictive Insights")
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
