from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import datetime

import database

# Initialize the database and tables on startup
database.create_db_and_tables()
app = FastAPI(
    title="People Counting API",
    description="API for managing areas and retrieving people counting statistics."
)

# --- Pydantic Models for Data Validation ---
class AreaBase(BaseModel):
    name: str
    coordinates: List[List[int]]

class AreaCreate(AreaBase):
    pass

class AreaResponse(AreaBase):
    id: int
    class Config:
        orm_mode = True

class LiveEventResponse(BaseModel):
    timestamp: datetime.datetime
    event_type: str

class StatsResponse(BaseModel):
    area_id: int
    entries: int
    exits: int
    query_filters: dict

# --- Database Dependency ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API Endpoints ---
@app.post("/api/areas/", response_model=AreaResponse, tags=["Areas"])
def create_area(area: AreaCreate, db: Session = Depends(get_db)):
    """Create a new monitored area with polygon coordinates."""
    db_area = db.query(database.Area).filter(database.Area.name == area.name).first()
    if db_area:
        raise HTTPException(status_code=400, detail="Area with this name already exists")
    if len(area.coordinates) < 3:
        raise HTTPException(status_code=400, detail="A polygon must have at least 3 points.")
    new_area = database.Area(name=area.name, coordinates=area.coordinates)
    db.add(new_area)
    db.commit()
    db.refresh(new_area)
    return new_area

@app.get("/api/areas/", response_model=List[AreaResponse], tags=["Areas"])
def get_areas(db: Session = Depends(get_db)):
    """Retrieve a list of all configured areas."""
    areas = db.query(database.Area).all()
    return areas

@app.delete("/api/areas/{area_id}", status_code=204, tags=["Areas"])
def delete_area(area_id: int, db: Session = Depends(get_db)):
    """Delete an area and all its associated event data."""
    db_area = db.query(database.Area).filter(database.Area.id == area_id).first()
    if not db_area:
        raise HTTPException(status_code=404, detail="Area not found")
    db.delete(db_area)
    db.commit()
    return

@app.get("/api/stats/{area_id}", response_model=StatsResponse, tags=["Statistics"])
def get_stats(
    area_id: int,
    start_date: Optional[datetime.datetime] = Query(None, description="ISO 8601 format: YYYY-MM-DDTHH:MM:SS"),
    end_date: Optional[datetime.datetime] = Query(None, description="ISO 8601 format: YYYY-MM-DDTHH:MM:SS"),
    db: Session = Depends(get_db)
):
    """Get total entry/exit counts for an area, with optional date filtering."""
    query = db.query(database.CountingEvent).filter(database.CountingEvent.area_id == area_id)
    
    if start_date:
        query = query.filter(database.CountingEvent.timestamp >= start_date)
    if end_date:
        query = query.filter(database.CountingEvent.timestamp <= end_date)

    entries = query.filter(database.CountingEvent.event_type == 'entry').count()
    exits = query.filter(database.CountingEvent.event_type == 'exit').count()
    
    return {
        "area_id": area_id,
        "entries": entries,
        "exits": exits,
        "query_filters": {"start_date": str(start_date) if start_date else None, "end_date": str(end_date) if end_date else None}
    }

@app.get("/api/stats/live/{area_id}", response_model=Optional[LiveEventResponse], tags=["Statistics"])
def get_live_stats(area_id: int, db: Session = Depends(get_db)):
    """Returns the most recent entry/exit event for a specific area."""
    latest_event = db.query(database.CountingEvent) \
        .filter(database.CountingEvent.area_id == area_id) \
        .order_by(database.CountingEvent.timestamp.desc()) \
        .first()
    if not latest_event:
        return None
    return latest_event