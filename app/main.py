from fastapi import FastAPI
from app.routers import event_router
from app.core.exceptions import BusinessException, business_exception_handler

app = FastAPI(
    title="Plataforma de Eventos Acadêmicos REST API",
    description="API robusta com travas complexas de concorrência e gerenciamento de estados."
)

app.add_exception_handler(BusinessException, business_exception_handler)

app.include_router(event_router.router)