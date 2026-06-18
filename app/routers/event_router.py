from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional
from app.core.dependencies import get_db
from app.services.event_service import EventService
from app.repositories.event_repository import EventRepository
from app.schemas.schemas import (
    EventCreate, EventResponse, EventStatusUpdate,
    ActivityCreate, ActivityResponse,
    ParticipantCreate, ParticipantResponse,
    RegistrationCreate, RegistrationResponse
)

router = APIRouter(prefix="/api", tags=["Eventos Acadêmicos"])

@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventCreate, db: Session = Depends(get_db)):
    return EventService(db).create_event(payload)

@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    EventService(db).delete_event(event_id)

@router.patch("/events/{event_id}/status", response_model=EventResponse)
def update_event_status(event_id: uuid.UUID, payload: EventStatusUpdate, db: Session = Depends(get_db)):
    return EventService(db).update_event_status(event_id, payload)

@router.post("/events/{event_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(event_id: uuid.UUID, payload: ActivityCreate, db: Session = Depends(get_db)):
    return EventService(db).create_activity(event_id, payload)

@router.get("/activities", response_model=List[ActivityResponse])
def list_activities(
    theme: Optional[str] = Query(None),
    available: bool = Query(False),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return EventRepository(db).get_activities_paginated(theme, available, limit, offset)

@router.post("/participants", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
def create_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    return EventService(db).create_participant(payload)

@router.get("/participants", response_model=List[ParticipantResponse])
def list_participants(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return EventRepository(db).get_participants_paginated(limit, offset)

@router.post("/registrations", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_registration(payload: RegistrationCreate, db: Session = Depends(get_db)):
    return EventService(db).register_participant(payload)