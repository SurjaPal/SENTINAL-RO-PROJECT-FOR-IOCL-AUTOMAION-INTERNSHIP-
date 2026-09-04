"""
Sentinel-RO — Module 4 (Predictive Maintenance Engine)
Simulates a motor bearing vibration trend over the past 30 days and uses
Linear Regression to forecast the exact number of days until the vibration
crosses the critical failure threshold.
"""
from __future__ import annotations

import os
import argparse
from datetime import datetime, timezone

import numpy as np
import psycopg2
from sklearn.linear_model import LinearRegression

CRITICAL_VIBRATION_THRESHOLD = 6.0  # mm/s
INSERT_ANOMALY = (
    "INSERT INTO anomalies (time, ro_id, sensor_type, value, reason, severity) "
    "VALUES (%s, %s, %s, %s, %s, %s)"
)

def generate_and_forecast(ro_id: str, pump_id: str) -> dict:
    """
    Simulates past 30 days of daily vibration data.
    Fits a linear regression model and computes days to failure.
    """
    days_past = 30
    X_train = np.arange(-days_past, 0).reshape(-1, 1)
    
    # Synthetic vibration: base 2.0 mm/s + increasing trend of 0.12 mm/s per day + noise
    base_vibration = 2.0
    trend = 0.12 
    noise = np.random.normal(0, 0.2, size=days_past)
    y_train = base_vibration + (trend * (X_train.flatten() + days_past)) + noise
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # y = m*x + c
    # We want to find x where y = CRITICAL_VIBRATION_THRESHOLD
    # x = (y - c) / m
    m = model.coef_[0]
    c = model.intercept_
    
    if m <= 0:
        return {"will_fail": False}
        
    days_to_failure = (CRITICAL_VIBRATION_THRESHOLD - c) / m
    current_value = model.predict([[0]])[0]
    
    # If the failure is coming up in less than 14 days, generate a predictive alert!
    if 0 < days_to_failure < 14:
        return {
            "will_fail": True,
            "days_to_failure": float(days_to_failure),
            "current_vibration": float(current_value),
            "probability": round(min(0.99, max(0.70, 1.0 - (days_to_failure/30))), 2) * 100
        }
    return {"will_fail": False}

def run(dsn: str) -> None:
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Pick a random RO to apply the prediction to
    cursor.execute("SELECT ro_id FROM retail_outlets LIMIT 1")
    row = cursor.fetchone()
    if not row:
        print("[module4] No ROs found.")
        return
    ro_id = row[0]
    pump_id = "Pump 2"
    
    forecast = generate_and_forecast(ro_id, pump_id)
    if forecast.get("will_fail"):
        reason = (
            f"{pump_id} vibration trend indicates an {forecast['probability']}% probability "
            f"of motor bearing failure in {forecast['days_to_failure']:.1f} days."
        )
        print(f"[module4] Predictive Alert: {reason}")
        
        cursor.execute(INSERT_ANOMALY, (
            datetime.now(timezone.utc),
            ro_id,
            f"{pump_id} Motor Vibration",
            round(forecast["current_vibration"], 2),
            reason,
            "CRITICAL"
        ))
        print("[module4] Alert persisted to database.")
    else:
        print("[module4] No critical failure predicted in the near future.")
        
def main():
    parser = argparse.ArgumentParser(description="Sentinel-RO Module 4 Predictive Maintenance")
    parser.add_argument("--dsn", default=os.environ.get("SENTINEL_DB_DSN",
                         "dbname=sentinel user=sentinel password=sentinel host=localhost"))
    args = parser.parse_args()
    run(args.dsn)

if __name__ == "__main__":
    main()
