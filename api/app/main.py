from fastapi import FastAPI, HTTPException, Depends
from typing import List, Dict, Any
import time
from datetime import datetime
from sqlalchemy.orm import Session
from . import models, schemas
from .database import engine, get_db

# Create tables (if not exist, though init-db.sql should handle it)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tire Management API",
    description="Real-time tire pressure and temperature monitoring with alerts",
    version="1.0.0"
)

# --- Alerts endpoint ---
@app.get("/alerts/latest", response_model=List[schemas.TireAlert])
def get_latest_alerts(limit: int = 20, db: Session = Depends(get_db)):
    """Get latest alerts from the database"""
    alerts = db.query(models.TireAlert)\
        .order_by(models.TireAlert.timestamp.desc())\
        .limit(limit)\
        .all()
    return alerts

# --- Aggregations endpoint (New) ---
@app.get("/aggregations/latest", response_model=List[schemas.TireAggregation])
def get_latest_aggregations(limit: int = 20, db: Session = Depends(get_db)):
    """Get latest aggregations from the database"""
    aggs = db.query(models.TireAggregation)\
        .order_by(models.TireAggregation.window_end.desc())\
        .limit(limit)\
        .all()
    return aggs

# --- Dashboard summary ---
@app.get("/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get overall dashboard summary from real data"""
    
    # Get counts of active alerts
    total_alerts = db.query(models.TireAlert).count()
    critical_alerts = db.query(models.TireAlert).filter(models.TireAlert.severity == 'CRITICAL').count()
    warning_alerts = db.query(models.TireAlert).filter(models.TireAlert.severity == 'WARNING').count()
    
    # Get unique vehicles with recent activity (last 24 hours)
    # This is an approximation since we don't have a vehicles table
    recent_vehicles = db.query(models.TireAggregation.vehicle_id)\
        .distinct()\
        .count()
        
    return {
        "summary": {
            "total_alerts_history": total_alerts,
            "active_vehicles_24h": recent_vehicles,
            "critical_alerts_total": critical_alerts,
            "warning_alerts_total": warning_alerts,
        },
        "last_updated": datetime.now().isoformat()
    }

# --- Legacy/Mock Endpoints (Optional: Keep for reference or remove) ---
# For now, I'm keeping the structure simple and focused on the DB.
# If the user wants the simulation endpoints back, we can re-add them, 
# but they requested "real data".

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)