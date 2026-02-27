"""
FastAPI - Aplicación principal
Configuración de la API y dependency injection

HUMAN REVIEW (María Gutiérrez):
La IA quería poner todas las conexiones (MongoDB, Redis, etc.) como variables globales.
Eso funciona, pero hace imposible probar el código y cambiar configuraciones en runtime.
Por eso las puse en funciones separadas que se pueden inyectar - así los tests usan mocks
y el código real usa las conexiones reales. Es más trabajo inicial pero vale la pena.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from decimal import Decimal
from api_gateway.main_routes import router
from src.adapters import (
    MongoDBAdapter,
    RedisAdapter,
    RabbitMQAdapter,
)
from src.config import settings
from src.domain.strategies.amount_threshold import AmountThresholdStrategy
from src.domain.strategies.location_check import LocationStrategy
from src.application.use_cases import (
    EvaluateTransactionUseCase,
    ReviewTransactionUseCase,
)
from src.infrastructure.user_repository import UserRepository
from src.infrastructure.admin_repository import AdminRepository
from src.infrastructure.auth_service import (
    PasswordService,
    JWTService,
    EmailService
)
from src.application.auth_use_cases import (
    RegisterUserUseCase,
    LoginUserUseCase,
    VerifyEmailUseCase,
    GetCurrentUserUseCase
)
from src.application.admin_auth_use_cases import (
    RegisterAdminUseCase,
    LoginAdminUseCase,
    VerifyAdminEmailUseCase,
    GetCurrentAdminUseCase
)

# Crear aplicación FastAPI
app = FastAPI(
    title="Fraud Detection Engine",
    description="Motor de detección de fraude con Clean Architecture",
    version="0.1.0",
)

# CORS middleware
_allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency Injection
def get_repository():
    """Factory para TransactionRepository"""
    return MongoDBAdapter(settings.mongodb_url, settings.mongodb_database)


def get_cache():
    """Factory para CacheService"""
    return RedisAdapter(settings.redis_url, settings.redis_ttl)


def get_publisher():
    """Factory para MessagePublisher"""
    return RabbitMQAdapter(settings.rabbitmq_url)


def get_strategies():
    """
    Factory para estrategias de fraude
    
    Nota:
    La IA sugirió hardcodear las estrategias. Las cargo dinámicamente
    desde configuración para permitir modificación sin redespliegue (HU-008).
    """
    # Usar configuración por defecto de settings
    # NOTA: En producción se puede cargar desde Redis de forma asíncrona
    amount_threshold = Decimal(str(settings.amount_threshold))
    location_radius = settings.location_radius_km

    return [
        AmountThresholdStrategy(threshold=amount_threshold),
        LocationStrategy(radius_km=location_radius),
    ]


def get_evaluate_use_case(
    repository=Depends(get_repository),
    publisher=Depends(get_publisher),
    cache=Depends(get_cache),
):
    """Factory para EvaluateTransactionUseCase"""
    strategies = get_strategies()
    return EvaluateTransactionUseCase(repository, publisher, cache, strategies)


def get_review_use_case(repository=Depends(get_repository)):
    """Factory para ReviewTransactionUseCase"""
    return ReviewTransactionUseCase(repository)


# Authentication Factories
def get_user_repository():
    """Factory para UserRepository"""
    return UserRepository(settings.mongodb_url, settings.mongodb_database)


def get_password_service():
    """Factory para PasswordService"""
    return PasswordService()


def get_jwt_service():
    """Factory para JWTService"""
    return JWTService(
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        access_token_expire_minutes=settings.jwt_access_token_expire_minutes
    )


def get_email_service():
    """Factory para EmailService"""
    return EmailService(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_username=settings.smtp_username,
        smtp_password=settings.smtp_password,
        from_email=settings.from_email
    )


def get_register_use_case():
    """Factory para RegisterUserUseCase"""
    return RegisterUserUseCase(
        user_repository=get_user_repository(),
        password_service=get_password_service(),
        email_service=get_email_service(),
        base_url=settings.base_url
    )


def get_login_use_case():
    """Factory para LoginUserUseCase"""
    return LoginUserUseCase(
        user_repository=get_user_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service()
    )


def get_verify_email_use_case():
    """Factory para VerifyEmailUseCase"""
    return VerifyEmailUseCase(
        user_repository=get_user_repository(),
        email_service=get_email_service()
    )


def get_current_user_use_case():
    """Factory para GetCurrentUserUseCase"""
    return GetCurrentUserUseCase(
        user_repository=get_user_repository()
    )


# ========== FACTORIES PARA ADMIN AUTH ==========

def get_admin_repository():
    """Factory para AdminRepository"""
    return AdminRepository(settings.mongodb_url, settings.mongodb_database)


def get_register_admin_use_case():
    """Factory para RegisterAdminUseCase"""
    return RegisterAdminUseCase(
        admin_repository=get_admin_repository(),
        password_service=get_password_service(),
        email_service=get_email_service(),
        base_url=settings.admin_dashboard_url
    )


def get_login_admin_use_case():
    """Factory para LoginAdminUseCase"""
    return LoginAdminUseCase(
        admin_repository=get_admin_repository(),
        password_service=get_password_service(),
        jwt_service=get_jwt_service()
    )


def get_verify_admin_email_use_case():
    """Factory para VerifyAdminEmailUseCase"""
    return VerifyAdminEmailUseCase(
        admin_repository=get_admin_repository(),
        email_service=get_email_service()
    )


def get_current_admin_use_case():
    """Factory para GetCurrentAdminUseCase"""
    return GetCurrentAdminUseCase(
        admin_repository=get_admin_repository()
    )


# Registrar rutas con dependency injection
from api_gateway.main_routes import router, api_v1_router, configure_dependencies
from api_gateway.auth_routes import auth_router, configure_auth_dependencies
from api_gateway.admin_auth_routes import admin_auth_router, configure_admin_auth_dependencies

configure_dependencies(
    repository_factory=get_repository,
    cache_factory=get_cache,
    evaluate_use_case_factory=get_evaluate_use_case,
    review_use_case_factory=get_review_use_case,
    publisher_factory=get_publisher
)

configure_auth_dependencies(
    user_repository_factory=get_user_repository,
    password_service_factory=get_password_service,
    jwt_service_factory=get_jwt_service,
    email_service_factory=get_email_service,
    register_use_case_factory=get_register_use_case,
    login_use_case_factory=get_login_use_case,
    verify_email_use_case_factory=get_verify_email_use_case,
    get_current_user_use_case_factory=get_current_user_use_case
)

configure_admin_auth_dependencies(
    admin_repository_factory=get_admin_repository,
    password_service_factory=get_password_service,
    jwt_service_factory=get_jwt_service,
    email_service_factory=get_email_service,
    register_admin_use_case_factory=get_register_admin_use_case,
    login_admin_use_case_factory=get_login_admin_use_case,
    verify_admin_email_use_case_factory=get_verify_admin_email_use_case,
    get_current_admin_use_case_factory=get_current_admin_use_case
)

app.include_router(router)
app.include_router(api_v1_router)  # Añadir router v1
app.include_router(auth_router)  # Añadir router de autenticación
app.include_router(admin_auth_router)  # Añadir router de autenticación de admins


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
