#!/usr/bin/env python3
"""
MENSTRUAL CYCLE BACKEND
Usage:
    python menstrual_backend.py --csv "/path/to/data.csv" --age 30
"""

import argparse
import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from datetime import datetime
from typing import Tuple, Optional
import os

# definition for explanation and suggestion
def generate_explanation_and_suggestion(person_type: str, details: dict) -> Tuple[str, str]:

    explanation = "Data analysis complete."
    suggestion = "Maintain a healthy lifestyle."
    
    plateau = details.get("plateau_len", 0)
    age = details.get("age", 30)
    
    if person_type == "Pregnancy Likely":
        explanation = f"We detected a high temperature plateau lasting {plateau} days (longer than the typical 14 days), which strongly indicates pregnancy."
        suggestion = "We recommend taking a home pregnancy test or consulting your doctor for confirmation."
        
    elif person_type == "Normal Ovulatory":
        explanation = "Your cycle shows a clear temperature rise and a stable luteal phase, indicating successful ovulation and hormonal balance."
        suggestion = "Your cycle looks healthy! Continue your current routine of sleep and tracking."
        
    elif person_type == "Possible Perimenopause":
        explanation = f"Given your age ({age}) and the irregular/anovulatory temperature patterns observed, this may indicate perimenopausal transitions."
        suggestion = "Consider tracking symptoms like hot flashes. Consulting a gynecologist about perimenopause management might be helpful."
        
    elif person_type == "Anovulatory / Possible PCOD":
        explanation = "We could not detect a sustained temperature rise characteristic of ovulation. This can happen occasionally, but frequent anovulation may suggest PCOD."
        suggestion = "If this pattern persists, consider a check-up for PCOD/PCOS. Focus on a balanced diet and regular sleep."
        
    elif person_type == "Ovulatory – Atypical":
        explanation = "Ovulation was detected, but the luteal phase (high temp period) is shorter than usual."
        suggestion = "This might indicate Luteal Phase Defect. Ensure you are getting enough progesterone-supporting nutrients (Vitamin B6, Zinc)."
        
    return explanation, suggestion

# definition for today's insight
def get_todays_insight(daily_df: pd.DataFrame, ovulation_day: Optional[int], person_type: str = "Unclassified") -> str:

    if daily_df.empty:
        return "Insight unavailable (No Data)."

    # Handle Special Person Types First
    if person_type == "Pregnancy Likely":
        return "High temperature plateau maintained. <b>Pregnancy likely</b>; period not expected."
    
    if person_type == "Anovulatory / Possible PCOD":
        return "No clear ovulation detected (Anovulatory). Cycle irregularity expected."

    if person_type == "Possible Perimenopause":
        return "Cycle patterns suggest perimenopause. Period timing may vary."

    if ovulation_day is None:
         return "Insight unavailable (Ovulation not detected)."
    #predicting phase according to today's date
    try:
        latest_data_date = daily_df["date"].max()
        today = datetime.now().date()
        
        days_gap = (today - latest_data_date).days
        
        if days_gap < 0:
            return "Data appears to be from the future? Check system time or file."
        elif days_gap > 15:
            return "It seems like there is no data for tracking."
            
        last_day_num = int(daily_df["day"].max())
        current_cycle_day = last_day_num + days_gap
        
        if current_cycle_day < ovulation_day - 1:
            phase = "Follicular"
            msg = "You look so energized! Support your overall wellness by exercising, taking good nutrition, and managing your stress."
        elif ovulation_day - 1 <= current_cycle_day <= ovulation_day + 1:
            phase = "Ovulatory"
            msg = "You look so cool today, keep going!"
        else:
            phase = "Luteal"
            msg = "Stay hydrated, relaxed, and calm."
            
        # Simplified Insight with Suggestion
        insight = f"Today you are in the <span class='insight-highlight'>{phase} Phase</span>.<br><br>{msg}"
            
        return insight

    except Exception as e:
        return f"Insight error: {str(e)}"


# definition for loading and resampling(preprocessing for reducing noise)
def load_and_resample(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    
    # --- ROBUST COLUMN MAPPING ---
    df.columns = [c.lower().strip() for c in df.columns]
    
    ts_col = next((c for c in df.columns if c in ['timestamp', 'time', 'date', 'datetime']), None)
    if ts_col:
        df["timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
    else:
        raise ValueError("CSV must contain a timestamp/date column.")

    cbt_col = next((c for c in df.columns if c in ['cbt', 'temp', 'temperature', 'body_temp']), None)
    if cbt_col:
        df["cbt"] = df[cbt_col]
    else:
         raise ValueError("CSV must contain a cbt/temperature column.")

    # df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce") # Replaced by logic above
    df = df.dropna(subset=["timestamp", "cbt"]).reset_index(drop=True)
    df = df[df["cbt"] < 38.5].reset_index(drop=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # check sampling
    td = df["timestamp"].diff().dt.total_seconds()
    td_median = float(td.median()) if not td.isna().all() else None
    print(f"[INFO] sampling median seconds: {td_median}")

    if td_median is None:
        print("[WARN] insufficient timestamp diffs.")
    elif not (50 <= td_median <= 70):
        print("[INFO] Irregular sampling -> resampling to 1-minute and interpolating CBT.")
        df = df.set_index("timestamp").resample("1T").mean()
        df["cbt"] = df["cbt"].interpolate(method="time", limit=30)
        df = df.reset_index().dropna(subset=["cbt"]).reset_index(drop=True)
    else:
        print("[INFO] Sampling looks ~1-minute. No resampling performed.")

    return df

# definition for detecting sleep window (start and end of sleep)
def detect_sleep_windows(df: pd.DataFrame,
                         NEG_EPS: float = -1e-4,
                         POS_EPS: float = 1e-4,
                         SLEEP_START_MINUTES: int = 30,
                         SLEEP_END_MINUTES: int = 20) -> pd.DataFrame:
    df = df.copy()
    df["cbt_diff"] = df["cbt"].diff()
    df["cbt_diff_smooth"] = df["cbt_diff"].rolling(window=5, center=True, min_periods=1).mean()

    sleep_windows = []
    in_sleep = False
    neg_count = pos_count = 0
    sleep_start = None
    n = len(df)

    for i in range(n):
        slope = float(df.loc[i, "cbt_diff_smooth"])

        if slope < NEG_EPS:
            neg_count += 1
            pos_count = 0
        else:
            neg_count = 0

        if not in_sleep and neg_count >= SLEEP_START_MINUTES:
            in_sleep = True
            idx = max(0, i - SLEEP_START_MINUTES)
            sleep_start = df.loc[idx, "timestamp"]

        if in_sleep:
            if slope > POS_EPS:
                pos_count += 1
            else:
                pos_count = 0

            if pos_count >= SLEEP_END_MINUTES:
                idx_end = max(0, i - SLEEP_END_MINUTES)
                sleep_end = df.loc[idx_end, "timestamp"]
                sleep_windows.append((pd.to_datetime(sleep_start), pd.to_datetime(sleep_end)))
                in_sleep = False
                neg_count = pos_count = 0

    sleep_df = pd.DataFrame(sleep_windows, columns=["sleep_start", "sleep_end"])
    print(f"[INFO] Slope-detected sleep windows: {len(sleep_df)}")
    return sleep_df

# definition for backup sleep window (if slope detection fails) 
def fallback_night_windows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["hour"] = df["timestamp"].dt.hour
    night_mask = (df["hour"] >= 21) | (df["hour"] < 10)
    df["night_change"] = (night_mask != night_mask.shift(1)).cumsum()
    fallback_windows = []
    for gid, g in df.groupby("night_change"):
        if not g.empty and night_mask.loc[g.index[0]]:
            start = g["timestamp"].iloc[0]
            end = g["timestamp"].iloc[-1]
            dur = (end - start).total_seconds()
            if dur >= 1.5 * 3600:  # >= 1.5 hours
                fallback_windows.append((pd.to_datetime(start), pd.to_datetime(end)))
    sleep_df = pd.DataFrame(fallback_windows, columns=["sleep_start", "sleep_end"])
    print(f"[INFO] Fallback windows found: {len(sleep_df)}")
    return sleep_df

# definition for extracting the least CBT value from each sleep window and calculating difference between days 
def extract_daily_min(df: pd.DataFrame, sleep_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = df["timestamp"].dt.date
    daily_rows = []

    if sleep_df.empty:
        print("[INFO] No sleep windows provided; calculating daily minimums across all daytime tracking...")
        for date, group in df.groupby("date"):
            min_cbt = float(group["cbt"].min())
            min_row = group.loc[group["cbt"].idxmin()]
            daily_rows.append({
                "date": date,
                "sleep_start": min_row["timestamp"],
                "sleep_end": min_row["timestamp"],
                "sleep_min_cbt": min_cbt
            })
    else:
        sleep_df["sleep_start"] = pd.to_datetime(sleep_df["sleep_start"])
        sleep_df["sleep_end"] = pd.to_datetime(sleep_df["sleep_end"])
        sleep_df["duration_s"] = (sleep_df["sleep_end"] - sleep_df["sleep_start"]).dt.total_seconds()
        sleep_df["date"] = sleep_df["sleep_start"].dt.date

        main_sleep = sleep_df.loc[sleep_df.groupby("date")["duration_s"].idxmax()].reset_index(drop=True)

        for _, r in main_sleep.iterrows():
            s = df[(df["timestamp"] >= r["sleep_start"]) & (df["timestamp"] <= r["sleep_end"])]
            if s.empty:
                continue
            daily_rows.append({
                "date": r["date"],
                "sleep_start": r["sleep_start"],
                "sleep_end": r["sleep_end"],
                "sleep_min_cbt": float(s["cbt"].min())
            })

    daily_df = pd.DataFrame(daily_rows)
    if not daily_df.empty:
        daily_df = daily_df.sort_values("date").reset_index(drop=True)
        daily_df["day"] = np.arange(1, len(daily_df) + 1)
        daily_df["delta_cbt"] = daily_df["sleep_min_cbt"].diff()
    return daily_df

# definition for analyzing the cycle according to the calculated CBT temp difference 
def analyze_cycle(daily_df: pd.DataFrame, user_age: int) -> Tuple[dict, pd.DataFrame]:
    # defaults
    ovulation_day = None
    follicular_mean = None
    plateau_len = 0
    BASELINE_DAYS = 5

    pregnancy_flag = False
    normal_ovulatory = False
    ovulatory_atypical = False
    anovulatory = False
    perimenopause = False

    if daily_df.empty or len(daily_df) < 6:
        anovulatory = True
    else:
        L = len(daily_df)
        for i in range(3, max(3, L - 2)):
            if i - BASELINE_DAYS < 0 or i + 1 >= L:
                continue
            baseline_rows = daily_df.loc[i-BASELINE_DAYS:i-1, "sleep_min_cbt"]
            baseline = float(baseline_rows.mean())
            baseline_std = float(baseline_rows.std(ddof=0) if not baseline_rows.empty else np.nan)
            BASELINE_STD_LIMIT = 0.08  # °C

            if np.isfinite(baseline_std) and baseline_std > BASELINE_STD_LIMIT:
                continue  # it means the baseline is too noisy

            tomorrow = float(daily_df.loc[i+1, "sleep_min_cbt"])
            if 0.2 <= (tomorrow - baseline) <= 0.7:
                ovulation_day = int(daily_df.loc[i+1, "day"])
                follicular_mean = baseline
                break
        # for detecting plateau length
        if ovulation_day is not None:
            post_ov = daily_df[daily_df["day"] > ovulation_day].reset_index(drop=True)
            margin = 0.05
            plateau_len = 0
            for v in post_ov["sleep_min_cbt"]:
                if v >= follicular_mean + margin:
                    plateau_len += 1
                else:
                    break

            # drop back detection for period window, pregnancy and so on
            drop_back = False
            if plateau_len < len(post_ov):
                try:
                    if float(post_ov.iloc[plateau_len]["sleep_min_cbt"]) <= follicular_mean + margin:
                        drop_back = True
                except Exception:
                    drop_back = False

            if plateau_len > 14 and not drop_back:
                pregnancy_flag = True
            elif 11 <= plateau_len <= 14 and drop_back:
                normal_ovulatory = True
            elif plateau_len >= 8:
                ovulatory_atypical = True
            else:
                anovulatory = True
        else:
            anovulatory = True

    if anovulatory:
        if user_age >= 45:
             perimenopause = True
        # If < 45, remains just Anovulatory / PCOD
    
    # person_type
    if pregnancy_flag:
        person_type = "Pregnancy Likely"
    elif normal_ovulatory:
        person_type = "Normal Ovulatory"
    elif ovulatory_atypical:
        # If older, atypical can be sign of peri
        if user_age >= 45:
            person_type = "Possible Perimenopause"
        else:
            person_type = "Ovulatory – Atypical"
    elif anovulatory and not perimenopause:
        person_type = "Anovulatory / Possible PCOD"
    elif perimenopause:
        person_type = "Possible Perimenopause"
    else:
        person_type = "Unclassified"

    # clear ovulation outputs for PCOD/perimenopause by default
    ov_window = None
    ov_confidence = 0

    # period window
    period_start = period_end = None
    period_window = "Not clear"
    if normal_ovulatory and ovulation_day:
        period_start = ovulation_day + 12
        period_end = ovulation_day + 18
        period_window = f"Day {period_start} – Day {period_end}"
    elif pregnancy_flag:
        period_window = "Not expected"

    # ovulation window + confidence
    if ovulation_day:
        ov_start_day = ovulation_day - 0.5
        ov_end_day = ovulation_day + 1.0
        ov_window = (ov_start_day, ov_end_day)

        plateau_score = min(plateau_len / 14.0, 1.0)
        noise_score = 0.5
        rise_score = 0.0

        try:
            post_rows = daily_df[daily_df["day"] >= ovulation_day].head(2)
            if len(post_rows) >= 1 and follicular_mean is not None:
                post_mean = float(post_rows["sleep_min_cbt"].mean())
                rise = max(0.0, post_mean - follicular_mean)
                rise_score = min(rise / 0.7, 1.0)
        except Exception:
            rise_score = 0.0

        try:
            baseline_rows = daily_df[daily_df["day"] < ovulation_day].tail(5)
            baseline_std = float(baseline_rows["sleep_min_cbt"].std(ddof=0) if not baseline_rows.empty else np.nan)
            if np.isfinite(baseline_std):
                noise_score = 1.0 - min(baseline_std / 0.2, 1.0)
            else:
                noise_score = 0.5
        except Exception:
            noise_score = 0.5

        conf_val = 0.5 * rise_score + 0.4 * plateau_score + 0.1 * noise_score
        ov_confidence = int(round(conf_val * 100))
        CONF_MIN_OVULATION = 50

        if ov_confidence < CONF_MIN_OVULATION:
            ovulation_day = None
            ov_window = None

    # anovulation confidence (when no ovulation found)
    anov_confidence_percent = 0
    if ovulation_day is None:
        baseline_rows2 = daily_df["sleep_min_cbt"].tail(BASELINE_DAYS)
        baseline_std2 = float(baseline_rows2.std(ddof=0)) if not baseline_rows2.empty else np.nan
        BASELINE_STD_LIMIT = 0.08
        if np.isfinite(baseline_std2):
            variability_score = min(1.0, baseline_std2 / BASELINE_STD_LIMIT)
        else:
            variability_score = 0.5

        max_rise = 0.0
        if len(daily_df) >= 4:
            for j in range(3, len(daily_df) - 1):
                try:
                    b_rows = daily_df.loc[j-3:j-1, "sleep_min_cbt"]
                    b_mean = float(b_rows.mean())
                    possible_rise = float(daily_df.loc[j+1, "sleep_min_cbt"]) - b_mean
                    if possible_rise > max_rise:
                        max_rise = possible_rise
                except Exception:
                    continue
        rise_score_shallow = min(1.0, max_rise / 0.2)
        anov_conf_val = 0.75 * variability_score + 0.25 * (1.0 - rise_score_shallow)
        anov_confidence_percent = int(round(anov_conf_val * 100))
    else:
        anov_confidence_percent = 0

    # Generate Why & Suggestion
    expl_details = {"plateau_len": plateau_len, "age": user_age}
    explanation, suggestion = generate_explanation_and_suggestion(person_type, expl_details)

    # attach outputs and daily_df
    outputs = {
        "Person_Type": person_type,
        "Ovulation_Day": ovulation_day,
        "Ovulation_Window": ov_window,
        "Ovulation_Confidence_pct": ov_confidence,
        "Anovulation_Confidence_pct": anov_confidence_percent,
        "Next_Period_Window": period_window,
        "Explanation": explanation,
        "Suggestion": suggestion
    }

# gathering cycle phase for plotting
    daily_df["cycle_phase"] = "Unclassified"
    if ovulation_day is not None:
        
        mask_fol = daily_df["day"] < (ovulation_day - 1)
        mask_ov = (daily_df["day"] >= (ovulation_day - 1)) & (daily_df["day"] <= (ovulation_day + 1))
        mask_lut = daily_df["day"] > (ovulation_day + 1)
        
        daily_df.loc[mask_fol, "cycle_phase"] = "Follicular"
        daily_df.loc[mask_ov, "cycle_phase"] = "Ovulatory"
        daily_df.loc[mask_lut, "cycle_phase"] = "Luteal"

    # Add plateau_len to outputs for alert logic
    outputs["Plateau_Len"] = plateau_len

    return outputs, daily_df



def check_alerts(daily_df, ovulation_day, person_type, manual_period_date=None, plateau_len=0):
    # Alerts disabled for now
    return {
        "alert_type": None,
        "message": None,
        "severity": "info",
        "show_alert": False
    }

#-----------output-----------------------
def pretty_print_results(outputs: dict, daily_df: pd.DataFrame):
    print("\n=== ANALYSIS SUMMARY ===")
    for k, v in outputs.items():
        print(f"{k}: {v}")
    print()

    if daily_df.empty:
        print("[INFO] No daily sleep-min CBT rows to display.")
    else:
        cols = ["date", "sleep_start", "sleep_end", "sleep_min_cbt", "day", "delta_cbt"]
        avail = [c for c in cols if c in daily_df.columns]
        print("[INFO] Daily summary (first rows):")
        print(daily_df[avail].to_string(index=False))


def plot_results(daily_df: pd.DataFrame, outputs: dict, out_path: Optional[str] = None):
    if daily_df.empty:
        print("[INFO] No plot (no daily data).")
        return

    ov_window = outputs.get("Ovulation_Window", None)
    ov_conf = outputs.get("Ovulation_Confidence_pct", 0)
    person_type = outputs.get("Person_Type", "Unclassified")
    period_window = outputs.get("Next_Period_Window", "Not clear")
    ov_day = outputs.get("Ovulation_Day", None)

    plt.figure(figsize=(14, 4))
    plt.plot(daily_df["day"], daily_df["sleep_min_cbt"], marker="o", linewidth=2, color="black", label="Sleep-Min CBT")

    # If cycle_phase exists, shade
    if "cycle_phase" in daily_df.columns:
        for _, row in daily_df.iterrows():
            d = float(row["day"])
            phase = row.get("cycle_phase", "Unclassified")
            if phase == "Follicular":
                plt.axvspan(d - 0.5, d + 0.5, color="lightblue", alpha=0.25)
            elif phase == "Ovulatory":
                plt.axvspan(d - 0.5, d + 0.5, color="pink", alpha=0.35)
            elif phase == "Luteal":
                plt.axvspan(d - 0.5, d + 0.5, color="navajowhite", alpha=0.35)

    if ov_day:
        plt.axvline(x=ov_day, color="crimson", linestyle="--", linewidth=2, label="Ovulation Day (rise)")

    if ov_window:
        ov_s, ov_e = ov_window
        ov_col = "salmon" if person_type != "Pregnancy Likely" else "gold"
        plt.axvspan(ov_s, ov_e, color=ov_col, alpha=0.25, label=f"Ovulation window (~24–36h) — {ov_conf}%")

    # period window only for normal ovulatory — parse robustly
    plt.title(f"CBT-Based Menstrual Cycle Analysis — {person_type}")
    if person_type == "Normal Ovulatory" and period_window:
        # extract numeric day values (handles formats like 'Day 12 – Day 18', '12-18', etc.)
        nums = re.findall(r"[-+]?\d*\.?\d+", str(period_window))
        if len(nums) >= 2:
            try:
                start_day, end_day = float(nums[0]), float(nums[1])
                plt.axvspan(start_day - 0.5, end_day + 0.5, color="pink", alpha=0.3, label="Estimated Period Window")
            except Exception:
                # if parsing fails, skip shading but keep plot
                pass

    ax = plt.gca()
    ax.set_xlim(1, max(30, int(daily_df["day"].max())))
    plt.xticks(range(1, max(31, int(daily_df["day"].max()) + 1)))
    plt.xlabel("Day")
    plt.ylabel("Sleep-Min CBT (°C)")
    plt.legend(loc="upper left")
    plt.grid(which="major", linestyle=":", linewidth=0.6)
    if out_path:
        try:
            out_dir = os.path.dirname(out_path) or "."
            os.makedirs(out_dir, exist_ok=True)
            plt.savefig(out_path, bbox_inches="tight")
            print(f"[INFO] Saved plot to: {out_path}")
        except Exception as e: 
            print(f"[ERROR] Could not save plot: {e}")
    else: 
        plt.show()

#----------------main----------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to CSV (minute-level timestamps + cbt column)")
    parser.add_argument("--age", type=int, default=30, help="User age (for perimenopause logic)")
    parser.add_argument("--out", help="Path to save the generated plot (png). If omitted, plot is shown interactively.")
    args = parser.parse_args()

    # If an output path is requested, switch to a non-interactive backend to avoid GUI blocking
    try:
        if getattr(args, "out", None):
            plt.switch_backend("Agg")
    except Exception:
        pass

    df = load_and_resample(args.csv)
    sleep_df = detect_sleep_windows(df)
    if sleep_df.empty:
        # fallback
        sleep_df = fallback_night_windows(df)
    if sleep_df.empty:
        outputs = {
            "Person_Type": "Insufficient Data",
            "Ovulation_Window": None,
            "Ovulation_Confidence_pct": 0,
            "Next_Period_Window": "Not available",
        }
        print("OUTPUT:", outputs)
        print("[INFO] No sleep detected / couldn't calibrate data — ensure device worn during sleep and minute-level sampling.")
        return

    daily_df = extract_daily_min(df, sleep_df)
    outputs, daily_df = analyze_cycle(daily_df, args.age)
    pretty_print_results(outputs, daily_df)
    plot_results(daily_df, outputs, out_path=args.out)



def analyze_menstrual_file(file_path: str):
    """
    API entry point for menstrual cycle analysis.
    Returns a dictionary clean for JSON serialization.
    """
    try:
        df = load_and_resample(file_path)
        sleep_df = detect_sleep_windows(df)
        
        # Fallback if sleep detection (slope-based) fails
        if sleep_df.empty:
            sleep_df = fallback_night_windows(df)
            
        daily_df = extract_daily_min(df, sleep_df)
        outputs, daily_df_analyzed = analyze_cycle(daily_df, user_age=30) # Default age 30 if not passed
        
        # Format for Frontend (align with dashboard expectation)
        # Frontend expects: cycle_length, next_period, symptoms (or message)
        
        # Map specific outputs
        result = {
            "cycle_length": outputs.get("Cycle_Length", 28), # Note: Backend doesn't explicitly calc cycle length in days yet?
            "next_period": outputs.get("Next_Period_Window", "Not clear"),
            "symptoms": outputs.get("Suggestion", "No specific symptoms detected."),
            "phase_insight": get_todays_insight(daily_df_analyzed, outputs.get("Ovulation_Day"), outputs.get("Person_Type")),
            "person_type": outputs.get("Person_Type"),
            "ovulation_day": outputs.get("Ovulation_Day"),
            "message": "Analysis successful"
        }
        
        # Add detailed metrics if needed
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    main()

