import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.observabilidade import init_sentry

# Logo após o sys.path.append e antes de qualquer outro import de core/infra:
# RuntimeError de configuração ausente (SECRET_KEY em core/auth_utils.py,
# SCPI_EXPORT_HMAC_KEY, DB_* em infra/database.py:_build_database_url)
# acontece na hora do import — antes de existir qualquer FastAPI(...) ou
# startup event. Sem o Sentry já inicializado aqui, exatamente os erros de
# deploy mal configurado que esta telemetria deveria capturar morrem
# silenciosos no journal do systemd.
init_sentry("api")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from core.csrf import CSRFMiddleware
from core.docs_protegidos import registrar_rotas_docs
from core.errors import rate_limit_handler
from core.limiter import limiter
from core.security_headers import SecurityHeadersMiddleware
from infra import migrations as _migrations
from infra.aws_clientes import rekognition_client, s3_client
from infra.database import close_pool
from services.agendador import iniciar_agendador
from routers import (
    admin,
    alunos,
    auth,
    chamadas,
    notificacoes,
    professores,
    public,
    relatorios,
    turmas,
)

_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(_LOG_DIR, exist_ok=True)


def _make_rotating_handler(filename: str) -> TimedRotatingFileHandler:
    h = TimedRotatingFileHandler(
        os.path.join(_LOG_DIR, filename),
        when="midnight",
        backupCount=90,
        encoding="utf-8",
    )
    h.setFormatter(logging.Formatter(_LOG_FORMAT))
    return h


# Console handler para desenvolvimento
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))

# Configurar root logger (console) + loggers específicos (arquivo)
logging.basicConfig(level=logging.INFO, handlers=[_console_handler])

logging.getLogger("scpi").addHandler(_make_rotating_handler("scpi.log"))
_audit_logger = logging.getLogger("scpi.audit")
_audit_logger.addHandler(_make_rotating_handler("scpi_audit.log"))
_audit_logger.propagate = False  # audit events must not duplicate into scpi.log

logger = logging.getLogger("scpi.api")


def _check_aws_connectivity():
    try:
        if rekognition_client:
            rekognition_client.list_collections(MaxResults=1)
            logger.info("AWS Rekognition: conectado.")
        else:
            logger.warning("AWS Rekognition: cliente não inicializado.")
    except Exception as e:
        logger.warning("AWS Rekognition: falha na verificação de conectividade: %s", e)
    try:
        if s3_client:
            s3_client.list_buckets()
            logger.info("AWS S3: conectado.")
        else:
            logger.warning("AWS S3: cliente não inicializado.")
    except Exception as e:
        logger.warning("AWS S3: falha na verificação de conectividade: %s", e)


_agendador_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Substitui os antigos @app.on_event("startup"/"shutdown"), deprecados.

    O `try/finally` cerca só o `yield`: se `run_all()` levantar, o teardown
    NÃO roda — mesmo comportamento de antes, quando um startup que falhava
    impedia o evento de shutdown de ser disparado. Cercar o startup também
    faria `close_pool()` rodar sobre um pool que talvez nem tenha sido criado.

    Migrations concorrentes dos 4 workers do gunicorn já são cobertas por
    advisory lock dentro de `run_all` (infra/migrations.py).
    """
    global _agendador_task
    _migrations.run_all()
    _agendador_task = asyncio.create_task(iniciar_agendador())
    _check_aws_connectivity()
    try:
        yield
    finally:
        if _agendador_task:
            _agendador_task.cancel()
        close_pool()


# Em produção, /docs, /redoc e /openapi.json exigem sessão de Admin e respondem
# 404 para o resto — evita expor toda a superfície da API (endpoints + schemas)
# a anônimos. Em dev/homolog seguem abertos. Ver core/docs_protegidos.py.
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "").strip().lower() == "production"
_DESCRICAO_API = """
API do SCPI — controle de presença acadêmica por reconhecimento facial.

**Autenticação.** O login devolve cookies `HttpOnly` (`scpi_access` e
`scpi_refresh`); não existe header `Authorization`. Toda requisição que altera
estado precisa do header `X-Requested-With: XMLHttpRequest` (CSRF
double-submit). `/auth/login` e `/auth/refresh` são isentos de CSRF por
design — o cookie jar do React Native motivou a isenção.

**Papéis.** `Admin`, `Professor` e `Aluno`. A tag `admin` inteira exige papel
Admin. Rotas marcadas como *serviço* são chamadas pelo script da câmera, com
token emitido por sala.

**Erros.** Respostas de erro trazem `error_code` além de `detail` — são 27
códigos padronizados, consumidos pelo toast do portal e pelo `useErrorToast`
do app. Violação de unicidade vira 409, chave estrangeira vira 400, banco
indisponível vira 503.

**Limites.** Rotas sensíveis têm rate limit por IP (SlowAPI, storage
compartilhado em PostgreSQL) e o login tem lockout progressivo.

Este `/docs` fica **desligado em produção** (`ENVIRONMENT=production`).
"""

_TAGS_OPENAPI = [
    {"name": "público", "description": "Sem autenticação: saúde da API e política de privacidade."},
    {"name": "auth", "description": "Login, refresh, logout, primeiro acesso e recuperação de senha."},
    {"name": "admin", "description": "Gestão de usuários, turmas, horários, biometria e relatórios. Exige papel Admin em todas as rotas."},
    {"name": "alunos", "description": "Dashboard, frequência, biometria, consentimento LGPD e export de dados do próprio aluno."},
    {"name": "professores", "description": "Dashboard do professor."},
    {"name": "turmas", "description": "Turmas do usuário e alunos matriculados."},
    {"name": "chamadas", "description": "Abertura, acompanhamento, ajuste e fechamento de chamada. Inclui as rotas de serviço usadas pela câmera."},
    {"name": "relatorios", "description": "Relatórios de frequência em JSON e PDF, para professor e admin."},
    {"name": "notificacoes", "description": "Registro do push token do dispositivo."},
]

app = FastAPI(
    title="SCPI API",  # gitleaks:allow — falso positivo (generic-api-key), sem segredo
    # Subir na mudança que quebra contrato com portal ou app.
    version="1.0.0",
    description=_DESCRICAO_API,
    openapi_tags=_TAGS_OPENAPI,
    # As tres rotas nativas ficam desligadas: quem as serve e
    # registrar_rotas_docs, que exige Admin quando em producao.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if _raw_origins:
    _allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
else:
    _allowed_origins = [
        "http://localhost:8081",
        "http://localhost:19006",
        "http://localhost:3000",
    ]

# Ordem importa: middleware adicionado por último é o mais externo (executa antes
# no request). Queremos CORS por fora do CSRF para que o preflight OPTIONS seja
# respondido pelo CORS sem passar pelo CSRF. Já o CSRF fica antes da aplicação
# para bloquear mutações sem X-Requested-With quando auth vier por cookie.
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    # O portal roda em outra origem que a API; sem expor o header, o JS não
    # consegue ler o nome do arquivo dos downloads de PDF.
    expose_headers=["Content-Disposition"],
)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["127.0.0.1"])
app.add_middleware(SecurityHeadersMiddleware)


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(notificacoes.router)
app.include_router(alunos.router)
app.include_router(professores.router)
app.include_router(turmas.router)
app.include_router(chamadas.router)
app.include_router(relatorios.router)

# Depois dos routers: o /openapi.json servido aqui monta o schema do app ja completo.
registrar_rotas_docs(app, producao=_IS_PRODUCTION)
