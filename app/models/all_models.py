import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")  # DRAFT, PUBLISHED, CONCLUDED, CANCELED

    activities: Mapped[list["Activity"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    max_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_registrations: Mapped[int] = mapped_column(Integer, default=0)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Para fins de Auditoria/Locking

    event: Mapped[Event] = relationship(back_populates="activities")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="activity")

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    registrations: Mapped[list["Registration"]] = relationship(back_populates="participant")

class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    activity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("activities.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="CONFIRMED")  # CONFIRMED, CANCELED

    participant: Mapped[Participant] = relationship(back_populates="registrations")
    activity: Mapped[Activity] = relationship(back_populates="registrations")

    __table_args__ = (
        UniqueConstraint("participant_id", "activity_id", name="uq_participant_activity"),
    )