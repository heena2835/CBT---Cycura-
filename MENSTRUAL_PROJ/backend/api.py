from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import shutil
import os
import sys
import pandas as pd
import numpy as np
import json

# Add parent directory to path to import menstrual_backend
# Add parent directory to path to import modules if needed (legacy)
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
# Add feature directories
sys.path.append(os.path.join(root_dir, 'menstrual'))


# Add current directory (backend) to path to allow sibling imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from menstrual_backend import load_and_resample, detect_sleep_windows, fallback_night_windows, extract_daily_min, analyze_cycle, get_todays_insight, check_alerts


from datetime import datetime

# Inline simple state manager for period date
_manual_period_date = None

def get_manual_period_date():
    global _manual_period_date
    return _manual_period_date

def set_manual_period_date(date_obj):
    global _manual_period_date
    _manual_period_date = date_obj

app = FastAPI(title="CYCURA API", description="Backend for Cycura Menstrual Analysis")
print("--- LOADING API ---")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze_data(
    file: UploadFile = File(...), 
    age: int = Form(30),
    name: str = Form(None),
    gender: str = Form(None)
):
    temp_filename = f"temp_{file.filename}"
    try:
        # Save uploaded file
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run analysis logic
        df = load_and_resample(temp_filename)
        
        sleep_df = detect_sleep_windows(df)
        if sleep_df.empty:
            sleep_df = fallback_night_windows(df)
            
        daily_df = extract_daily_min(df, sleep_df)
        
        if daily_df.empty:
            return {
                "status": "success",
                "outputs": {
                    "Person_Type": "Insufficient Data",
                    "Ovulation_Day": None,
                    "Ovulation_Window": None,
                    "Ovulation_Confidence_pct": 0,
                    "Anovulation_Confidence_pct": 0,
                    "Next_Period_Window": "Not clear",
                    "Explanation": "No sufficient temperature measurements were recorded. Please ensure your device is tracking your body temperature correctly throughout the night.",
                    "Suggestion": "Try gathering at least 5-6 nights of consistent data.",
                    "Plateau_Len": 0,
                    "Todays_Insight": "Insight missing due to lack of historical data.",
                    "Alerts": {"alert_type": None, "message": "No data", "severity": "info", "show_alert": False}
                },
                "daily_data": []
            }
            
        outputs, analyzed_df = analyze_cycle(daily_df, age)
        
        # Calculate Insight
        ov_day = outputs.get("Ovulation_Day")
        p_type = outputs.get("Person_Type", "Unclassified")
        insight = get_todays_insight(daily_df, ov_day, person_type=p_type)
        outputs["Todays_Insight"] = insight
        
        # Check Alerts
        manual_date = get_manual_period_date()
        plateau_len = outputs.get("Plateau_Len", 0)
        alert_data = check_alerts(daily_df, ov_day, p_type, manual_period_date=manual_date, plateau_len=plateau_len)
        outputs["Alerts"] = alert_data

        # Convert df to records for JSON
        if not analyzed_df.empty:
            # handle date serialization
            analyzed_df["date"] = analyzed_df["date"].astype(str)
            analyzed_df["sleep_start"] = analyzed_df["sleep_start"].astype(str)
            analyzed_df["sleep_end"] = analyzed_df["sleep_end"].astype(str)
            
            # Replace NaNs with None for JSON compatibility
            analyzed_df = analyzed_df.replace({np.nan: None})
            
            daily_data = analyzed_df.to_dict(orient="records")
        else:
            daily_data = []

        # Handle NaNs in outputs dict too
        for k, v in outputs.items():
            if isinstance(v, float) and np.isnan(v):
                outputs[k] = None

        return {
            "status": "success",
            "outputs": outputs,
            "daily_data": daily_data
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


@app.post("/confirm-period")
async def confirm_period(date: str = Form(...)):
    """
    Manually confirms the start of a period.
    Format: YYYY-MM-DD
    """
    print(f"[/confirm-period] Received request with date: '{date}'")
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        set_manual_period_date(date_obj)
        print(f"[/confirm-period] Successfully set manual date to {date_obj}")
        return {"status": "success", "message": f"Period confirmed for {date}", "date": date}
    except ValueError as ve:
        print(f"[/confirm-period] ValueError: {ve}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {ve}. Use YYYY-MM-DD")
    except Exception as e:
        print(f"[/confirm-period] Critical Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")







# Mount Frontend Static Files at the END to ensure API routes take precedence
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")


