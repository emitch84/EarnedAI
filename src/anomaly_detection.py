import pandas as pd

def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Identifies tasks with significant variances or risks.
    """
    
    def explain_row(row):
        reasons = []
        score = 0
        
        # Cost Overrun
        if row["CPI"] < 0.85 and row["PctComplete"] > 0.1:
            reasons.append(f"Significantly over budget (CPI: {row['CPI']}).")
            score += 2
        elif row["CPI"] < 0.95 and row["PctComplete"] > 0.1:
            reasons.append(f"Slightly over budget (CPI: {row['CPI']}).")
            score += 1
            
        # Schedule Slippage
        if row["SPI"] < 0.85 and row["PV"] > 0:
            reasons.append(f"Significantly behind schedule (SPI: {row['SPI']}).")
            score += 2
        elif row["SPI"] < 0.95 and row["PV"] > 0:
            reasons.append(f"Slightly behind schedule (SPI: {row['SPI']}).")
            score += 1
            
        # TCPI Warning
        if row["TCPI"] > 1.2 and row["TCPI"] < 10:
             reasons.append(f"Hard to recover (TCPI: {row['TCPI']}).")
             score += 1
        elif row["TCPI"] >= 10:
             reasons.append(f"Budget depleted.")
             score += 3

        if not reasons:
            return "Normal", 0
        else:
            return " | ".join(reasons), score

    df[["Anomaly_Explanation", "Anomaly_Score"]] = df.apply(
        lambda x: pd.Series(explain_row(x)), axis=1
    )
    
    return df

def get_high_risk_tasks(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    return df.sort_values(by="Anomaly_Score", ascending=False).head(top_n)
