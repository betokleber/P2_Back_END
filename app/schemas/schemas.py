from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import datetime
import uuid
from typing import Optional, List

class EventCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)

class EventResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: str

    class Config:
        from_attributes = True

class EventStatusUpdate(BaseModel):
    status: str

class ActivityCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    max_capacity: int = Field(..., gt=0)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_dates(self) -> "ActivityCreate":
        if self.end_time <= self.start_time:
            raise ValueError("A data de término (end_time) deve ser maior que a data de início (start_time).")
        return self

class ActivityResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    title: str
    max_capacity: int
    current_registrations: int
    start_time: datetime
    end_time: datetime

    class Config:
        from_attributes = True

class ParticipantCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr

class ParticipantResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    class Config:
        from_attributes = True

class RegistrationCreate(BaseModel):
    participant_id: uuid.UUID
    activity_id: uuid.UUID

class RegistrationResponse(BaseModel):
    id: uuid.UUID
    participant_id: uuid.UUID
    activity_id: uuid.UUID
    status: str

    class Config:
        from_attributes = True