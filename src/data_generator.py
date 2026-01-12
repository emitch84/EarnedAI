import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_multi_project_data(output_dir="data"):
    """
    Generates data for 3 distinct projects with full history for S-Curves.
    Saves to: projects.csv, tasks.csv, logs.csv
    """
    np.random.seed(42)
    
    projects = [
        {"id": "P001", "name": "Project Alpha - Data Center Migration", "type": "IT Infra", "budget": 1200000},
        {"id": "P002", "name": "Project Beta - HQ Construction", "type": "Construction", "budget": 5500000},
        {"id": "P003", "name": "Project Gamma - AI Platform Launch", "type": "Software", "budget": 850000}
    ]
    
    tasks_list = []
    logs_list = []
    
    report_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for proj in projects:
        # Determine project timeline
        if proj["id"] == "P001":
            # 50% through
            duration = 180 
            start_date = report_date - timedelta(days=90) 
        elif proj["id"] == "P002":
            # 30% through
            duration = 365 
            start_date = report_date - timedelta(days=100)
        else:
            # 80% through (Almost done)
            duration = 100
            start_date = report_date - timedelta(days=80)
            
        proj_end_date = start_date + timedelta(days=duration)
        proj["start_date"] = start_date
        proj["end_date"] = proj_end_date
        
        # Generate Tasks
        num_tasks = np.random.randint(15, 30)
        remaining_budget = proj["budget"]
        
        for i in range(num_tasks):
            task_id = f"{proj['id']}-T{i+1:03d}"
            
            # Distribute budget (last task takes remainder)
            if i == num_tasks - 1:
                bac = remaining_budget
            else:
                bac = np.round(np.random.uniform(remaining_budget * 0.01, remaining_budget * 0.15), 2)
                remaining_budget -= bac
                if remaining_budget < 0: remaining_budget = 0
            
            # WBS simulation
            task_names = [
                "Requirements Gathering", "Design Phase", "Procurement", "Foundation/Core", 
                "Development Sprint 1", "Development Sprint 2", "Testing/QA", 
                "UAT", "Deployment", "Training", "Handover"
            ]
            task_name = f"{np.random.choice(task_names)} - {i+1}"
            
            # Schedule
            # Random start within the first 70% of project
            offset = np.random.randint(0, int(duration * 0.7))
            task_start = start_date + timedelta(days=offset)
            # Duration 5% to 20% of project
            task_dur = np.random.randint(int(duration * 0.05), int(duration * 0.2))
            task_end = task_start + timedelta(days=task_dur)
            
            tasks_list.append({
                "ProjectID": proj["id"],
                "TaskID": task_id,
                "TaskName": task_name,
                "BAC": bac,
                "PlannedStart": task_start,
                "PlannedEnd": task_end
            })
            
            # Generate History Logs (Weekly)
            # We iterate from Project Start to Report Date
            curr_log_date = start_date
            
            # Simulation factors for this specific task
            # Some are efficient (CPI > 1), some are not
            task_cpi_factor = np.random.normal(1.0, 0.15) 
            # Some are fast (SPI > 1), some slow
            task_spi_factor = np.random.normal(1.0, 0.15)
            
            completed = False
            
            while curr_log_date <= report_date:
                # Calculate what % SHOULD be done (Planned)
                total_days = (task_end - task_start).days
                if total_days == 0: total_days = 1
                days_since_start = (curr_log_date - task_start).days
                
                if days_since_start < 0:
                    pct_planned = 0.0
                elif days_since_start >= total_days:
                    pct_planned = 1.0
                else:
                    pct_planned = days_since_start / total_days
                
                # Apply SPI factor to get Actual % Complete
                # If SPI < 1, we are slower than planned
                if days_since_start < 0:
                    pct_complete = 0.0
                else:
                    # Random noise
                    noise = np.random.uniform(-0.05, 0.05)
                    pct_complete = min(max(pct_planned * task_spi_factor + noise, 0.0), 1.0)
                    
                # If task is logically done (time passed significantly), force completion logic or cap it
                if pct_complete >= 0.99:
                    pct_complete = 1.0
                    completed = True
                
                # Calculate EV
                ev = bac * pct_complete
                
                # Calculate AC
                # AC = EV / CPI
                if pct_complete == 0:
                    ac = 0.0
                else:
                    ac = ev / task_cpi_factor
                    # Add some randomness to cost
                    ac = ac * np.random.uniform(0.95, 1.05)
                
                logs_list.append({
                    "ProjectID": proj["id"],
                    "TaskID": task_id,
                    "Date": curr_log_date,
                    "PctPlanned": round(pct_planned, 4),
                    "PctComplete": round(pct_complete, 4),
                    "AC": round(ac, 2),
                    "EV": round(ev, 2),
                    "PV": round(bac * pct_planned, 2)
                })
                
                curr_log_date += timedelta(weeks=1)

    # Convert to DataFrames
    df_projects = pd.DataFrame(projects)
    df_tasks = pd.DataFrame(tasks_list)
    df_logs = pd.DataFrame(logs_list)
    
    # Save
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df_projects.to_csv(f"{output_dir}/projects.csv", index=False)
    df_tasks.to_csv(f"{output_dir}/tasks.csv", index=False)
    df_logs.to_csv(f"{output_dir}/logs.csv", index=False)
    
    print(f"Data generated in {output_dir}/")
    return df_projects, df_tasks, df_logs

if __name__ == "__main__":
    generate_multi_project_data()
