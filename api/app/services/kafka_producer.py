from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TireData
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class TireDataCreate(BaseModel):
    tire_id: str
    pressure: float
    temperature: float
    timestamp: datetime = datetime.utcnow()

@router.post("/")
def create_tire_data(data: TireDataCreate, db: Session = Depends(get_db)):
    tire = TireData(**data.dict())
    db.add(tire)
    db.commit()
    db.refresh(tire)
    return tire

@router.get("/")
def list_tire_data(db: Session = Depends(get_db)):
    return db.query(TireData).all()
