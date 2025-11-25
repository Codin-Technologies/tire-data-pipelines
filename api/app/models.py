from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from .database import Base

class TireAlert(Base):
    __tablename__ = "tire_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(255), unique=True, nullable=False)
    sensor_id = Column(String(100), nullable=False, index=True)
    vehicle_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    description = Column(Text)
    triggering_value = Column(Float)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TireAggregation(Base):
    __tablename__ = "tire_aggregations"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String(100), nullable=False, index=True)
    vehicle_id = Column(String(100), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False, index=True)
    window_size = Column(String(10), nullable=False)
    avg_pressure = Column(Float, nullable=False)
    avg_temperature = Column(Float, nullable=False)
    min_pressure = Column(Float, nullable=False)
    max_pressure = Column(Float, nullable=False)
    min_temperature = Column(Float, nullable=False)
    max_temperature = Column(Float, nullable=False)
    record_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
