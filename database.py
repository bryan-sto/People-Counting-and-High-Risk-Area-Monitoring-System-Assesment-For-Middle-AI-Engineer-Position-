import datetime
from sqlalchemy.sql import func
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import config

# Engine setup using the configuration file
engine = create_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Area(Base):
    """
    Represents a monitored area (polygon) in the system.
    """
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    coordinates = Column(JSON, nullable=False)
    events = relationship("CountingEvent", back_populates="area", cascade="all, delete-orphan")

class CountingEvent(Base):
    """
    Represents a single entry or exit event for a tracked person.
    """
    __tablename__ = "counting_events"
    id = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, ForeignKey("areas.id", ondelete="CASCADE"), nullable=False)    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    event_type = Column(String, nullable=False) # 'entry' or 'exit'
    tracker_id = Column(Integer)
    area = relationship("Area", back_populates="events")

def create_db_and_tables():
    """
    Creates all database tables defined by the Base metadata.
    This is idempotent - it won't re-create existing tables.
    """
    Base.metadata.create_all(bind=engine)
    print("Database and tables checked/created successfully.")

if __name__ == "__main__":
    create_db_and_tables()