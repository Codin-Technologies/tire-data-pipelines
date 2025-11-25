from ..models import TPMSMetrics
from sqlalchemy.orm import Session

def get_latest_metrics(db: Session, vehicle_id: int):
    return db.query(TPMSMetrics).filter(TPMSMetrics.vehicle_id == vehicle_id).order_by(TPMSMetrics.timestamp.desc()).limit(10).all()

def get_latest_alerts(db: Session, vehicle_id: int):
    from ..models import Alerts
    return db.query(Alerts).filter(Alerts.vehicle_id == vehicle_id).order_by(Alerts.timestamp.desc()).limit(10).all()
