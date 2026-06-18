from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import List, Optional
from app.models.all_models import Event, Activity, Participant, Registration

class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_event(self, event: Event) -> Event:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_event_by_id(self, event_id: uuid.UUID) -> Optional[Event]:
        return self.db.scalars(select(Event).where(Event.id == event_id)).first()

    def delete_event(self, event: Event) -> None:
        self.db.delete(event)
        self.db.commit()

    def create_activity(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_activity_with_lock(self, activity_id: uuid.UUID) -> Optional[Activity]:
        return self.db.scalars(
            select(Activity).where(Activity.id == activity_id).with_for_update()
        ).first()

    def get_activities_paginated(self, theme: Optional[str], available: bool, limit: int, offset: int) -> List[Activity]:
        stmt = select(Activity)
        if theme:
            stmt = stmt.where(Activity.title.ilike(f"%{theme}%"))
        if available:
            stmt = stmt.where(Activity.current_registrations < Activity.max_capacity)
        return list(self.db.scalars(stmt.limit(limit).offset(offset)).all())

    def create_participant(self, participant: Participant) -> Participant:
        self.db.add(participant)
        self.db.commit()
        self.db.refresh(participant)
        return participant

    def get_participants_paginated(self, limit: int, offset: int) -> List[Participant]:
        return list(self.db.scalars(select(Participant).limit(limit).offset(offset)).all())

    def check_schedule_conflict(self, participant_id: uuid.UUID, start: datetime, end: datetime) -> bool:
        stmt = (
            select(Registration)
            .join(Activity)
            .where(
                Registration.participant_id == participant_id,
                Registration.status == "CONFIRMED",
                Activity.start_time < end,
                Activity.end_time > start
            )
        )
        return self.db.scalars(stmt).first() is not None

    def get_registration_by_id(self, reg_id: uuid.UUID) -> Optional[Registration]:
        return self.db.scalars(select(Registration).where(Registration.id == reg_id)).first()

    def create_registration(self, registration: Registration) -> Registration:
        self.db.add(registration)
        return registration