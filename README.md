# P2_Back_END

##
Modelagem de Entidades

1. 
Evento (Event)
O evento principal que abriga as atividades.

Atributos:
id: UUID (Chave Primária, Obrigatório)
title: String (Obrigatório)
status: String (Obrigatório, Padrão: 'DRAFT') — Máquina de estados: DRAFT >>> PUBLISHED >>> CONCLUDED ou CANCELED.

Relacionamentos:
Possui muitas Atividades (Activity) (1-para-N)


2. 
Atividade (Activity)
Palestras ou workshops específicos do evento, com limite de participantes.

Atributos:
id: UUID (Chave Primária, Obrigatório)
event_id: UUID (Chave Estrangeira, Obrigatório)
title: String (Obrigatório)
max_capacity: Integer (Obrigatório, Constraint: $> 0$) — Limite de vagas.
current_registrations: Integer (Obrigatório, Padrão: 0) — Cálculo derivado (total de inscritos ativos).
start_time: DateTime (Obrigatório)
end_time: DateTime (Obrigatório, Constraint: end_time > start_time)


Relacionamentos:
Pertence a um Evento (Event) (N-para-1)Possui muitas Inscrições (Registration) (1-para-N)

3. 
Participante (Participant)O usuário que se inscreve nas atividades.


Atributos:
id: UUID (Chave Primária, Obrigatório)
name: String (Obrigatório)
email: String (Obrigatório, Unique)

Relacionamentos:
Possui muitas Inscrições (Registration) (1-para-N)

4. 
Inscrição (Registration)
A tabela que une o Participante à Atividade (N-para-N).
Atributos:id: UUID (Chave Primária, Obrigatório)
participant_id: UUID (Chave Estrangeira, Obrigatório)
activity_id: UUID (Chave Estrangeira, Obrigatório)
status: String (Obrigatório, Padrão: 'CONFIRMED') — Máquina de estados: CONFIRMED >>> CANCELED.

Relacionamentos:
Pertence a um Participante (Participant) (N-para-1)
Pertence a uma Atividade (Activity) (N-para-1)


Máquinas de Estado

Fase do Evento:    [ DRAFT ] ──> [ PUBLISHED ] ──> [ CONCLUDED ]
                                      │
                                      └──> [ CANCELED ]

Fase da Inscrição: [ CONFIRMED ] ──> [ CANCELED ]


Regras de Negócio (Formato Exigido)

RN-001 
Impedir Inscrição em Atividade sem Vagas
Gatilho Ao criar uma nova Registration.
Pré-condição A Activity alvo deve estar associada a um evento publicado.
Ação O sistema deve verificar se current_registrations é menor que max_capacity. Se igual ou maior, a inscrição é rejeitada.
Violação HTTP 422 Unprocessable Entity{ "error": "ACTIVITY_FULL", "message": "A atividade selecionada já atingiu a capacidade máxima de vagas.", "details": { "activity_id": "uuid", "max_capacity": 50 } } 

RN-002  
Bloqueio de Inscrição em Evento Rascunho
Gatilho Ao tentar criar uma Registration.
Pré-condição Nenhuma.
Ação O sistema busca o status do Event pai daquela atividade. Se for DRAFT, impede a inscrição.
ViolaçãoHTTP 400 Bad Request{ "error": "EVENT_NOT_PUBLISHED", "message": "Não é possível se inscrever em atividades de um evento que ainda não foi publicado.", "details": { "event_id": "uuid", "current_status": "DRAFT" } } 


RN-003
Impedir Conflito de Horário do Participante
Gatilho Ao criar uma Registration.
Pré-condição Nenhuma.
Ação O sistema deve verificar se o participante já possui outra inscrição CONFIRMED em uma atividade cujo intervalo entre start_time e end_time se sobreponha ao horário da nova atividade.
Violação HTTP 409 Conflict{ "error": "SCHEDULE_CONFLICT", "message": "O participante já está inscrito em outra atividade no mesmo horário.", "details": { "conflicting_activity_id": "uuid", "time_slot": { "start": "2026-10-15T14:00:00", "end": "2026-10-15T16:00:00" } } } 


RN-004
Cancelamento Automático de Inscrições em Evento Cancelado
Gatilho Ao transicionar o status de um Event para CANCELED.
Pré-condição O status atual do evento deve ser PUBLISHED.
Ação O sistema deve buscar todas as atividades do evento e alterar o status de todas as suas respectivas Registration para CANCELED.
Violação HTTP 400 Bad Request{ "error": "INVALID_EVENT_TRANSITION", "message": "Não é possível cancelar um evento que já está concluído ou em rascunho.", "details": { "event_id": "uuid", "current_status": "CONCLUDED" } } 

RN-005 Imutabilidade de Inscrições Pós-Evento
Gatilho Ao tentar atualizar ou cancelar uma Registration.
Pré-condição O Event pai está com status CONCLUDED.
Ação O sistema barra qualquer modificação na inscrição, pois o evento já encerrou (estado terminal).
Violação HTTP 400 Bad Request{ "error": "EVENT_ALREADY_CONCLUDED", "message": "Não é permitido alterar inscrições de um evento que já foi finalizado.", "details": { "event_id": "uuid" } } 

##
