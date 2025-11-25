from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TireAlertBase(BaseModel):
    alert_id: str
    sensor_id: str
    vehicle_id: str
    timestamp: datetime
    alert_type: str
    severity: str
    description: Optional[str] = None
    triggering_value: Optional[float] = None

class TireAlertCreate(TireAlertBase):
    pass

class TireAlert(TireAlertBase):
    id: int
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class TireAggregationBase(BaseModel):
    sensor_id: str
    vehicle_id: str
    window_start: datetime
    window_end: datetime
    window_size: str
    avg_pressure: float
    avg_temperature: float
    min_pressure: float
    max_pressure: float
    min_temperature: float
    max_temperature: float
    record_count: int

class TireAggregation(TireAggregationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
