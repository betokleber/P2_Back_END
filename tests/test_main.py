import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.core.dependencies import get_db
from app.models.all_models import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

# 1. Teste de Criação de Evento
def test_create_event(client):
    response = client.post("/api/events", json={"title": "Simpósio de IA"})
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"

# 2. Teste Pydantic Validator - Erro de Datas na Atividade
def test_activity_date_validation_error(client):
    response = client.post("/api/events", json={"title": "X"})
    ev_id = response.json()["id"]
    
    # end_time antes de start_time
    payload = {
        "title": "Workshop",
        "max_capacity": 30,
        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "end_time": datetime.now().isoformat()
    }
    res = client.post(f"/api/events/{ev_id}/activities", json=payload)
    assert res.status_code == 422

# 3. Teste de Fluxo de Transição Permitida de Estado
def test_event_status_transition_success(client):
    ev = client.post("/api/events", json={"title": "Congresso"}).json()
    res = client.patch(f"/api/events/{ev['id']}/status", json={"status": "PUBLISHED"})
    assert res.status_code == 200
    assert res.json()["status"] == "PUBLISHED"

# 4. Teste de Fluxo de Transição INVÁLIDA de Estado
def test_event_status_transition_invalid(client):
    ev = client.post("/api/events", json={"title": "Congresso"}).json()
    res = client.patch(f"/api/events/{ev['id']}/status", json={"status": "CONCLUDED"})
    assert res.status_code == 400
    assert res.json()["error"] == "INVALID_STATUS_TRANSITION"

# 5. RN-002: Impedir inscrição se o evento pai for rascunho
def test_registration_blocked_in_draft_event(client):
    ev = client.post("/api/events", json={"title": "Draft Event"}).json()
    part = client.post("/api/participants", json={"name": "Dev", "email": "dev@test.com"}).json()
    act = client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "Palestra", "max_capacity": 10,
        "start_time": datetime.now().isoformat(), "end_time": (datetime.now() + timedelta(hours=2)).isoformat()
    }).json()

    res = client.post("/api/registrations", json={"participant_id": part["id"], "activity_id": act["id"]})
    assert res.status_code == 400
    assert res.json()["error"] == "EVENT_NOT_PUBLISHED"

# 6. RN-001: Impedir Inscrição sem Vagas Livres
def test_registration_activity_full(client):
    ev = client.post("/api/events", json={"title": "Lotação"}).json()
    client.patch(f"/api/events/{ev['id']}/status", json={"status": "PUBLISHED"})
    
    act = client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "Sala VIP", "max_capacity": 1,
        "start_time": datetime.now().isoformat(), "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
    }).json()

    p1 = client.post("/api/participants", json={"name": "P1", "email": "p1@t.com"}).json()
    p2 = client.post("/api/participants", json={"name": "P2", "email": "p2@t.com"}).json()

    # Primeira inscrição ocupa a única vaga
    client.post("/api/registrations", json={"participant_id": p1["id"], "activity_id": act["id"]})
    # Segunda deve estourar a regra
    res = client.post("/api/registrations", json={"participant_id": p2["id"], "activity_id": act["id"]})
    
    assert res.status_code == 422
    assert res.json()["error"] == "ACTIVITY_FULL"

# 7. RN-003: Bloquear Inscrição se Horários se Sobrepuserem
def test_registration_schedule_conflict(client):
    ev = client.post("/api/events", json={"title": "Horários"}).json()
    client.patch(f"/api/events/{ev['id']}/status", json={"status": "PUBLISHED"})
    part = client.post("/api/participants", json={"name": "P", "email": "p@t.com"}).json()

    now = datetime.now()
    act1 = client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "Python Avançado", "max_capacity": 10,
        "start_time": now.isoformat(), "end_time": (now + timedelta(hours=2)).isoformat()
    }).json()

    act2 = client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "FastAPI Core", "max_capacity": 10,
        "start_time": (now + timedelta(hours=1)).isoformat(), "end_time": (now + timedelta(hours=3)).isoformat()
    }).json()

    client.post("/api/registrations", json={"participant_id": part["id"], "activity_id": act1["id"]})
    res = client.post("/api/registrations", json={"participant_id": part["id"], "activity_id": act2["id"]})
    
    assert res.status_code == 409
    assert res.json()["error"] == "SCHEDULE_CONFLICT"

# 8. RN-005: Imutabilidade Pós-Evento Concluído
def test_immutable_registration_after_concluded(client):
    ev = client.post("/api/events", json={"title": "Fim"}).json()
    client.patch(f"/api/events/{ev['id']}/status", json={"status": "PUBLISHED"})
    part = client.post("/api/participants", json={"name": "P", "email": "p@t.com"}).json()
    act = client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "A", "max_capacity": 5,
        "start_time": datetime.now().isoformat(), "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
    }).json()

    client.patch(f"/api/events/{ev['id']}/status", json={"status": "CONCLUDED"})
    res = client.post("/api/registrations", json={"participant_id": part["id"], "activity_id": act["id"]})
    assert response_status := res.status_code == 400
    assert res.json()["error"] == "EVENT_ALREADY_CONCLUDED"

# 9. Cenário de Borda: Proibir Deleção Física de Eventos Ativos
def test_cannot_delete_active_event(client):
    ev = client.post("/api/events", json={"title": "Imutável"}).json()
    client.patch(f"/api/events/{ev['id']}/status", json={"status": "PUBLISHED"})
    
    res = client.delete(f"/api/events/{ev['id']}")
    assert res.status_code == 400
    assert res.json()["error"] == "CANNOT_DELETE_PUBLISHED"

# 10. Paginação e Filtros
def test_list_activities_with_pagination_and_filter(client):
    ev = client.post("/api/events", json={"title": "Filtros"}).json()
    client.post(f"/api/events/{ev['id']}/activities", json={
        "title": "Workshop de Java", "max_capacity": 5,
        "start_time": datetime.now().isoformat(), "end_time": (datetime.now() + timedelta(hours=1)).isoformat()
    })
    
    res = client.get("/api/activities?theme=Java&limit=5&offset=0")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert "Java" in res.json()[0]["title"]