import uuid
from sqlalchemy.orm import Session
from app.repositories.event_repository import EventRepository
from app.models.all_models import Event, Activity, Participant, Registration
from app.schemas.schemas import EventCreate, ActivityCreate, ParticipantCreate, RegistrationCreate, EventStatusUpdate
from app.core.exceptions import BusinessException

class EventService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EventRepository(db)

    def create_event(self, data: EventCreate) -> Event:
        event = Event(title=data.title, status="DRAFT")
        return self.repo.create_event(event)

    def delete_event(self, event_id: uuid.UUID) -> None:
        event = self.repo.get_event_by_id(event_id)
        if not event:
            raise BusinessException("NOT_FOUND", "Evento não encontrado", 404)
        
        # Cenário de Borda: Restringir deleção se não for DRAFT
        if event.status != "DRAFT":
            raise BusinessException(
                "CANNOT_DELETE_PUBLISHED",
                "Não é permitido deletar fisicamente um evento publicado ou encerrado. Altere o status para CANCELED.",
                status_code=400
            )
        self.repo.delete_event(event)

    def create_activity(self, event_id: uuid.UUID, data: ActivityCreate) -> Activity:
        event = self.repo.get_event_by_id(event_id)
        if not event:
            raise BusinessException("NOT_FOUND", "Evento pai não encontrado", 404)
        
        activity = Activity(
            event_id=event_id,
            title=data.title,
            max_capacity=data.max_capacity,
            start_time=data.start_time,
            end_time=data.end_time
        )
        return self.repo.create_activity(activity)

    def register_participant(self, data: RegistrationCreate) -> Registration:
        # RN-001 via Lock Pessimista
        activity = self.repo.get_activity_with_lock(data.activity_id)
        if not activity:
            raise BusinessException("NOT_FOUND", "Atividade não encontrada", 404)

        event = self.repo.get_event_by_id(activity.event_id)

        # RN-002: Bloqueio de Inscrição em Rascunho
        if event.status == "DRAFT":
            raise BusinessException(
                "EVENT_NOT_PUBLISHED",
                "Não é possível se inscrever em atividades de um evento rascunho.",
                status_code=400,
                details={"event_id": str(event.id), "current_status": event.status}
            )

        # RN-005: Imutabilidade pós-evento concluído
        if event.status == "CONCLUDED":
            raise BusinessException(
                "EVENT_ALREADY_CONCLUDED",
                "Não é permitido criar inscrições para um evento finalizado.",
                status_code=400
            )

        # RN-001: Checagem de Capacidade
        if activity.current_registrations >= activity.max_capacity:
            raise BusinessException(
                "ACTIVITY_FULL",
                "A atividade selecionada já atingiu a capacidade máxima de vagas.",
                status_code=422,
                details={"activity_id": str(activity.id), "max_capacity": activity.max_capacity}
            )

        # RN-003: Bloqueio de choque de horário do Participante
        if self.repo.check_schedule_conflict(data.participant_id, activity.start_time, activity.end_time):
            raise BusinessException(
                "SCHEDULE_CONFLICT",
                "O participante já está alocado em outra atividade concorrente neste horário.",
                status_code=409
            )

        new_reg = Registration(participant_id=data.participant_id, activity_id=data.activity_id, status="CONFIRMED")
        activity.current_registrations += 1
        activity.version += 1  # Incremento estratégico para auditoria da migration 3
        
        self.repo.create_registration(new_reg)
        self.db.commit()
        return new_reg

    def update_event_status(self, event_id: uuid.UUID, data: EventStatusUpdate) -> Event:
        event = self.repo.get_event_by_id(event_id)
        if not event:
            raise BusinessException("NOT_FOUND", "Evento não encontrado", 404)

        valid_transitions = {
            "DRAFT": ["PUBLISHED"],
            "PUBLISHED": ["CONCLUDED", "CANCELED"],
            "CONCLUDED": [],
            "CANCELED": []
        }

        if data.status not in valid_transitions.get(event.status, []):
            raise BusinessException(
                "INVALID_STATUS_TRANSITION",
                f"Transição inválida de {event.status} para {data.status}.",
                status_code=400
            )

        event.status = data.status

        # RN-004 adaptado: Cancelamento automático em cascata
        if data.status == "CANCELED":
            for activity in event.activities:
                act_locked = self.repo.get_activity_with_lock(activity.id)
                for reg in act_locked.registrations:
                    reg.status = "CANCELED"
                act_locked.current_registrations = 0

        self.db.commit()
        return event

    def create_participant(self, data: ParticipantCreate) -> Participant:
        participant = Participant(name=data.name, email=data.email)
        return self.repo.create_participant(participant)