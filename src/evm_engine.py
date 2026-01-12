import pandas as pd
import numpy as np

def calculate_snapshot_metrics(tasks_df: pd.DataFrame, logs_df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes the most recent status (snapshot) for each task.
    """
    # Get the latest log entry for each task
    latest_logs = logs_df.sort_values("Date").groupby("TaskID").tail(1)
    
    # Merge with task details (BAC, Names)
    df = pd.merge(tasks_df, latest_logs, on="TaskID", how="left")
    
    # Fill NaNs for tasks that might not have logs (shouldn't happen in our generator but good practice)
    df.fillna(0, inplace=True)
    
    # Calculate Standard Metrics
    
    # CV = EV - AC
    df["CV"] = (df["EV"] - df["AC"]).round(2)
    
    # SV = EV - PV
    df["SV"] = (df["EV"] - df["PV"]).round(2)
    
    # CPI
    df["CPI"] = df.apply(lambda x: x["EV"] / x["AC"] if x["AC"] > 0 else (1.0 if x["EV"] == 0 else 0.0), axis=1).round(3)
    
    # SPI
    df["SPI"] = df.apply(lambda x: x["EV"] / x["PV"] if x["PV"] > 0 else 1.0, axis=1).round(3)
    
    # EAC = BAC / CPI
    df["EAC"] = df.apply(lambda x: x["BAC"] / x["CPI"] if x["CPI"] > 0.1 else x["BAC"], axis=1).round(2)
    
    # VAC
    df["VAC"] = (df["BAC"] - df["EAC"]).round(2)
    
    # TCPI (To Complete Performance Index)
    # (BAC - EV) / (BAC - AC)
    def calc_tcpi(row):
        work_remaining = row["BAC"] - row["EV"]
        budget_remaining = row["BAC"] - row["AC"]
        
        if budget_remaining <= 0:
            return 999.0 # Impossible or Infinite
        
        return work_remaining / budget_remaining
    
    df["TCPI"] = df.apply(calc_tcpi, axis=1).round(3)

    # Derive Status
    def get_status(pct):
        if pct >= 1.0: return "Completed"
        if pct <= 0.0: return "Not Started"
        return "In Progress"
        
    df["Status"] = df["PctComplete"].apply(get_status)

    return df

def get_project_s_curve(logs_df: pd.DataFrame, project_id: str) -> pd.DataFrame:
    """
    Aggregates metrics by Date for S-Curve plotting.
    Returns DataFrame with [Date, Cumulative_PV, Cumulative_EV, Cumulative_AC]
    """
    proj_logs = logs_df[logs_df["ProjectID"] == project_id].copy()
    
    # Group by Date and sum metrics
    daily_agg = proj_logs.groupby("Date")[["PV", "EV", "AC"]].sum().reset_index()
    
    # We want cumulative (the logs already contain cumulative data per task? 
    # Wait, our generator: "EV = bac * pct_complete". Yes, EV is cumulative absolute value at that time.)
    # So summing them up across all tasks at a specific date gives the project cumulative.
    
    return daily_agg.sort_values("Date")

def generate_baseline_curve(tasks_df: pd.DataFrame, project_id: str) -> pd.DataFrame:
    """
    Constructs the full Planned Value (PV) curve from Project Start to Project Finish.
    This ensures the 'Baseline' line extends into the future.
    """
    proj_tasks = tasks_df[tasks_df["ProjectID"] == project_id].copy()
    
    # Determine project range
    start_date = proj_tasks["PlannedStart"].min()
    end_date = proj_tasks["PlannedEnd"].max()
    
    # Create daily range
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    baseline_data = []
    
    # Pre-calculate daily PV for all tasks
    # Simplified: Linear distribution of PV for each task over its duration
    
    for _, task in proj_tasks.iterrows():
        t_start = task["PlannedStart"]
        t_end = task["PlannedEnd"]
        bac = task["BAC"]
        duration = (t_end - t_start).days
        if duration <= 0: duration = 1
        daily_rate = bac / duration
        
        baseline_data.append({
            "Start": t_start,
            "End": t_end,
            "Rate": daily_rate
        })
        
    # Aggregate daily
    pv_points = []
    cum_pv = 0.0
    
    # OPTIMIZATION: Instead of iterating days x tasks (slow), we use a timeline sweep
    # But for MVP with small N, iteration is fine.
    
    timeline_df = pd.DataFrame({"Date": date_range})
    timeline_df["Daily_PV"] = 0.0
    
    for item in baseline_data:
        # Vectorized update
        mask = (timeline_df["Date"] >= item["Start"]) & (timeline_df["Date"] < item["End"])
        timeline_df.loc[mask, "Daily_PV"] += item["Rate"]
        
    timeline_df["Cumulative_PV"] = timeline_df["Daily_PV"].cumsum()
    
    # Filter to reduce points for plotting (optional, but keep daily for now)
    return timeline_df[["Date", "Cumulative_PV"]]
