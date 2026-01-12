import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline
from datetime import timedelta, datetime

def forecast_project_performance(logs_df: pd.DataFrame, project_id: str, total_bac: float):
    """
    Uses Machine Learning (Ridge Regression) to forecast the final completion date and cost
    based on the historical performance velocity of the project.
    
    Returns:
    - ai_eac: Predicted total cost
    - ai_end_date: Predicted completion date
    - forecast_df: DataFrame containing the 'Future' projection points for plotting
    - r2_score: Confidence score (R-squared) of the fit
    """
    
    # 1. Prepare Data
    proj_data = logs_df[logs_df["ProjectID"] == project_id].copy()
    
    # Aggregate to Project Level Cumulative Daily Series
    # unique dates
    daily_data = proj_data.groupby("Date")[["EV", "AC"]].sum().reset_index()
    daily_data = daily_data.sort_values("Date")
    
    # We need numeric dates for regression
    daily_data["DayOrdinal"] = daily_data["Date"].map(pd.Timestamp.toordinal)
    start_date_ordinal = daily_data["DayOrdinal"].min()
    daily_data["DaysSinceStart"] = daily_data["DayOrdinal"] - start_date_ordinal
    
    X = daily_data[["DaysSinceStart"]]
    y_ev = daily_data["EV"]
    y_ac = daily_data["AC"]
    
    # Filter for active period only (ignore zero starts if any to avoid skewing)
    mask = daily_data["EV"] > 0
    if mask.sum() < 3: # Not enough data
        return None, None, None, 0.0

    X_train = daily_data.loc[mask, ["DaysSinceStart"]]
    y_ev_train = daily_data.loc[mask, "EV"]
    y_ac_train = daily_data.loc[mask, "AC"]

    # 2. Train Models
    # We use Ridge Regression to be robust
    model_ev = Ridge(alpha=1.0)
    model_ev.fit(X_train, y_ev_train)
    
    model_ac = Ridge(alpha=1.0)
    model_ac.fit(X_train, y_ac_train)
    
    # Get Velocity (Slope)
    ev_velocity = model_ev.coef_[0] # Dollars Earned per Day
    ac_burn_rate = model_ac.coef_[0] # Dollars Spent per Day
    
    # 3. Predict Completion
    if ev_velocity <= 0:
        return total_bac, None, None, 0.0 # Stalled
        
    current_ev = y_ev_train.iloc[-1]
    remaining_ev = total_bac - current_ev
    
    if remaining_ev <= 0:
        # Already done
        return y_ac_train.iloc[-1], daily_data["Date"].max(), None, 1.0
        
    days_to_complete = remaining_ev / ev_velocity
    total_days_proj = X_train["DaysSinceStart"].iloc[-1] + days_to_complete
    
    # final_ordinal = start_date_ordinal + total_days_proj
    # ai_end_date = datetime.fromordinal(int(final_ordinal))
    
    # 4. Predict Cost at that date
    # AC_final = Intercept + Slope * TotalDays
    ai_eac = model_ac.intercept_ + model_ac.coef_[0] * total_days_proj
    
    # 5. Generate Forecast Curve (for charting)
    # 5. Generate Forecast Curve (for charting)
    last_day = int(X_train["DaysSinceStart"].iloc[-1])
    # Use full float precision for end date
    future_days = np.linspace(last_day, total_days_proj, num=20).reshape(-1, 1)
    
    future_ev = model_ev.predict(future_days)
    future_ac = model_ac.predict(future_days)
    
    # Force alignment of final points
    future_ev[-1] = total_bac
    future_ac[-1] = ai_eac
    
    # Cap EV at total_bac to prevent overshoot artifacts
    future_ev = np.minimum(future_ev, total_bac)
    
    future_dates = [datetime.fromordinal(int(start_date_ordinal + d[0])) for d in future_days]
    
    forecast_df = pd.DataFrame({
        "Date": future_dates,
        "Forecast_EV": future_ev,
        "Forecast_AC": future_ac
    })
    
    score = model_ev.score(X_train, y_ev_train)
    
    return ai_eac, future_dates[-1], forecast_df, score
