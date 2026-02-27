"""
FastAPI - Rutas de la API REST
Endpoints para evaluación, auditoría, revisión y configuración

Cumple Single Responsibility: Cada endpoint tiene una responsabilidad única

Nota (María Gutiérrez):
La IA sugirió poner toda la lógica en las rutas. La moví a los casos de uso
para cumplir con Separation of Concerns - las rutas solo manejan HTTP.
"""
import logging
from fastapi import APIRouter, HTTPException, Header, Query, status
from typing import List, Optional, Callable, Any, Dict
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """
    Return an ISO 8601 string in UTC ('Z') for a datetime.
    If dt is None, return None.
    If dt is naive, assume it's in local time and convert to UTC.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # treat as local, convert to UTC
        return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

# Constantes
RULE_NOT_FOUND_MESSAGE = "Rule not found"

# DTOs para request/response
class TransactionRequest(BaseModel):
    """DTO para solicitud de evaluación de transacción"""

    id: str = Field(..., description="Transaction ID")
    amount: float = Field(..., gt=0, description="Transaction amount")
    user_id: str = Field(..., description="User ID")
    location: dict = Field(..., description="Transaction location")
    timestamp: Optional[str] = None
    transaction_type: Optional[str] = Field(None, description="Tipo de transacción: transfer, payment, recharge, deposit")
    description: Optional[str] = Field(None, description="Descripción o destinatario de la transacción")


class ReviewRequest(BaseModel):
    """DTO para decisión manual de revisión"""

    decision: str = Field(..., pattern="^(APPROVED|REJECTED)$")
    analyst_comment: Optional[str] = None


class ThresholdConfigRequest(BaseModel):
    """DTO para actualización de configuración"""

    amount_threshold: float = Field(..., gt=0)
    location_radius_km: float = Field(..., gt=0)


class TransactionValidateRequest(BaseModel):
    """DTO para validación sincrónica de transacción (Frontend Usuario)"""

    amount: float = Field(..., description="Transaction amount (can be positive or negative)")
    userId: str = Field(..., description="User ID")
    location: str = Field(..., description="Location string")
    deviceId: Optional[str] = Field(None, description="Device ID (optional)")
    transactionType: Optional[str] = Field(None, description="Transaction type")


class RuleParametersRequest(BaseModel):
    """DTO para actualización de parámetros de regla"""

    parameters: Dict[str, Any] = Field(..., description="Rule parameters")


class RuleReorderRequest(BaseModel):
    """DTO para reordenar reglas en Chain of Responsibility"""

    ruleIds: List[str] = Field(..., description="Ordered list of rule IDs")


class UserAuthenticateRequest(BaseModel):
    """DTO para autenticación de transacción por parte del usuario"""

    confirmed: bool = Field(..., description="True si 'Fui yo', False si 'No fui yo'")


# Router principal
router = APIRouter()

# Sub-routers para organización
api_v1_router = APIRouter(prefix="/api/v1")

# Variables globales para las factories de dependencias
_repository_factory = None
_cache_factory = None
_publisher_factory = None
_evaluate_use_case_factory = None
_review_use_case_factory = None

def configure_dependencies(
    repository_factory,
    cache_factory,
    evaluate_use_case_factory,
    review_use_case_factory,
    publisher_factory=None
):
    """Configura las factories de dependencias desde main.py"""
    global _repository_factory, _cache_factory, _evaluate_use_case_factory, _review_use_case_factory, _publisher_factory
    _repository_factory = repository_factory
    _cache_factory = cache_factory
    _evaluate_use_case_factory = evaluate_use_case_factory
    _review_use_case_factory = review_use_case_factory
    _publisher_factory = publisher_factory


# ============================================================================
# Helper Functions para reducir complejidad cognitiva
# ============================================================================

async def _get_disabled_rules(cache) -> set:
    """Obtiene el conjunto de reglas deshabilitadas desde cache"""
    try:
        disabled_set = await cache.redis.smembers("disabled_default_rules")
        return {r.decode('utf-8') if isinstance(r, bytes) else r for r in disabled_set}
    except Exception as e:
        print(f"Error loading disabled rules: {e}")
        return set()


async def _build_strategies(disabled_rules: set, cache, repository):
    """Construye las estrategias de fraude basadas en reglas habilitadas"""
    from src.config import settings
    from src.domain.strategies.amount_threshold import AmountThresholdStrategy
    from src.domain.strategies.location_check import LocationStrategy
    from src.domain.strategies.device_validation import DeviceValidationStrategy
    from src.domain.strategies.rapid_transaction import RapidTransactionStrategy
    from src.domain.strategies.unusual_time import UnusualTimeStrategy
    
    strategies = []
    config = await cache.get_threshold_config()
    
    # 1. AmountThresholdStrategy
    if "rule_amount_threshold" not in disabled_rules:
        threshold = config.get("amount_threshold", settings.amount_threshold) if config else settings.amount_threshold
        strategies.append(AmountThresholdStrategy(Decimal(str(threshold))))
    
    # 2. LocationStrategy
    if "rule_location_check" not in disabled_rules:
        radius_km = config.get("location_radius_km", settings.location_radius_km) if config else settings.location_radius_km
        strategies.append(LocationStrategy(radius_km))
    
    # 3. DeviceValidationStrategy
    if "rule_device_validation" not in disabled_rules:
        strategies.append(DeviceValidationStrategy(redis_client=cache.redis_sync))
    
    # 4. RapidTransactionStrategy
    if "rule_rapid_transaction" not in disabled_rules:
        max_transactions_str = await cache.redis.get("rule_config:rule_rapid_transaction:max_transactions")
        time_window_minutes_str = await cache.redis.get("rule_config:rule_rapid_transaction:time_window_minutes")
        max_transactions = int(max_transactions_str) if max_transactions_str else 3
        time_window_minutes = int(time_window_minutes_str) if time_window_minutes_str else 5
        strategies.append(RapidTransactionStrategy(redis_client=cache.redis_sync, max_transactions=max_transactions, window_minutes=time_window_minutes))
    
    # 5. UnusualTimeStrategy
    if "rule_unusual_time" not in disabled_rules:
        strategies.append(UnusualTimeStrategy(audit_repository=repository))
    
    return strategies


def _parse_location(location_str: str) -> dict:
    """Parsea la ubicación desde string a coordenadas lat/lon"""
    location_str = location_str.strip()
    
    # Verificar si ya son coordenadas (formato: "lat,lon")
    if ',' in location_str and len(location_str.split(',')) == 2:
        try:
            parts = location_str.split(',')
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            return {"latitude": lat, "longitude": lon}
        except ValueError:
            pass
    
    # Mapeo de ciudades a coordenadas (fallback)
    location_coords = {
        "New York": {"latitude": 40.7128, "longitude": -74.0060},
        "Los Angeles": {"latitude": 34.0522, "longitude": -118.2437},
        "Chicago": {"latitude": 41.8781, "longitude": -87.6298},
        "Miami": {"latitude": 25.7617, "longitude": -80.1918},
        "San Francisco": {"latitude": 37.7749, "longitude": -122.4194},
        "Bogota": {"latitude": 4.6097, "longitude": -74.0817},
        "Medellin": {"latitude": 6.2442, "longitude": -75.5812},
        "Cali": {"latitude": 3.4516, "longitude": -76.5320}
    }
    
    city = location_str.split(",")[0].strip()
    return location_coords.get(city, {"latitude": 40.7128, "longitude": -74.0060})


def _adjust_amount_by_type(amount: float, transaction_type: str) -> float:
    """Ajusta el signo del monto según el tipo de transacción"""
    if transaction_type in ['transfer', 'payment', 'recharge']:
        return -abs(amount)  # Salida de dinero
    return abs(amount)  # Entrada de dinero (deposit)


def _map_risk_to_response(risk_level: str) -> tuple:
    """Mapea el nivel de riesgo a status y score"""
    risk_mapping = {
        "LOW_RISK": ("APPROVED", 15),
        "MEDIUM_RISK": ("SUSPICIOUS", 62),
        "HIGH_RISK": ("REJECTED", 95)
    }
    return risk_mapping.get(risk_level, ("REJECTED", 95))


def _get_default_rule_ids() -> set:
    """Retorna el conjunto de IDs de reglas predeterminadas"""
    return {
        "rule_amount_threshold",
        "rule_location_check",
        "rule_device_validation",
        "rule_rapid_transaction",
        "rule_unusual_time"
    }


async def _delete_default_rule(rule_id: str, cache) -> None:
    """Marca una regla predeterminada como eliminada en Redis"""
    await cache.redis.sadd("deleted_default_rules", rule_id)
    await cache.redis.srem("disabled_default_rules", rule_id)


def _delete_custom_rule(rule_id: str, repository) -> None:
    """Elimina una regla personalizada de MongoDB"""
    if hasattr(repository, 'db'):
        result = repository.db.custom_rules.delete_one({"id": rule_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail=RULE_NOT_FOUND_MESSAGE)


async def _handle_rule_enabled_state(rule_id: str, enabled: bool, cache, analyst_id: str) -> dict:
    """Maneja el cambio de estado enabled/disabled de una regla"""
    if enabled == False:
        await cache.redis.sadd("disabled_default_rules", rule_id)
    else:
        await cache.redis.srem("disabled_default_rules", rule_id)
    
    return {
        "success": True,
        "rule": {"id": rule_id, "enabled": enabled, "updated_by": analyst_id}
    }


async def _update_amount_threshold(rule_params: RuleParametersRequest, cache) -> None:
    """Actualiza los parámetros de rule_amount_threshold"""
    threshold = rule_params.parameters.get("threshold")
    if threshold is None or threshold <= 0:
        raise ValueError("Threshold must be positive")
    
    config = await cache.get_threshold_config()
    if config is None:
        from src.config import settings
        config = {
            "amount_threshold": settings.amount_threshold,
            "location_radius_km": settings.location_radius_km
        }
    
    config["amount_threshold"] = threshold
    await cache.set_threshold_config(**config)


async def _update_location_check(rule_params: RuleParametersRequest, cache) -> None:
    """Actualiza los parámetros de rule_location_check"""
    radius_km = rule_params.parameters.get("radius_km")
    if radius_km is None or radius_km <= 0:
        raise ValueError("Radius must be positive")
    
    config = await cache.get_threshold_config()
    if config is None:
        from src.config import settings
        config = {
            "amount_threshold": settings.amount_threshold,
            "location_radius_km": settings.location_radius_km
        }
    
    config["location_radius_km"] = radius_km
    await cache.set_threshold_config(**config)


async def _update_device_validation(rule_id: str, rule_params: RuleParametersRequest, cache) -> dict:
    """Actualiza los parámetros de rule_device_validation"""
    device_memory_days = rule_params.parameters.get("device_memory_days")
    if device_memory_days is not None:
        if device_memory_days <= 0:
            raise ValueError("device_memory_days must be positive")
        await cache.redis.set(f"rule_config:{rule_id}:device_memory_days", str(device_memory_days))
    
    return {"id": rule_id, "parameters": rule_params.parameters}


async def _update_rapid_transaction(rule_id: str, rule_params: RuleParametersRequest, cache) -> dict:
    """Actualiza los parámetros de rule_rapid_transaction"""
    max_transactions = rule_params.parameters.get("max_transactions")
    time_window_minutes = rule_params.parameters.get("time_window_minutes")
    
    if max_transactions is not None:
        if max_transactions <= 0:
            raise ValueError("max_transactions must be positive")
        await cache.redis.set(f"rule_config:{rule_id}:max_transactions", str(max_transactions))
    
    if time_window_minutes is not None:
        if time_window_minutes <= 0:
            raise ValueError("time_window_minutes must be positive")
        await cache.redis.set(f"rule_config:{rule_id}:time_window_minutes", str(time_window_minutes))
    
    return {"id": rule_id, "parameters": rule_params.parameters}


async def _update_unusual_time(rule_id: str, rule_params: RuleParametersRequest, cache) -> dict:
    """Actualiza los parámetros de rule_unusual_time"""
    deviation_threshold = rule_params.parameters.get("deviation_threshold")
    if deviation_threshold is not None:
        if deviation_threshold <= 0 or deviation_threshold > 1:
            raise ValueError("deviation_threshold must be between 0 and 1")
        await cache.redis.set(f"rule_config:{rule_id}:deviation_threshold", str(deviation_threshold))
    
    return {"id": rule_id, "parameters": rule_params.parameters}


def _update_custom_rule(rule_id: str, rule_params: RuleParametersRequest, repository, analyst_id: str) -> None:
    """Actualiza una regla personalizada en MongoDB"""
    if not hasattr(repository, 'db'):
        raise HTTPException(status_code=404, detail=RULE_NOT_FOUND_MESSAGE)
    
    update_data = {
        "parameters": rule_params.parameters,
        "updated_at": datetime.now(),
        "updated_by": analyst_id
    }
    
    if "enabled" in rule_params.parameters:
        update_data["enabled"] = rule_params.parameters["enabled"]
    
    result = repository.db.custom_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=RULE_NOT_FOUND_MESSAGE)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/transaction", status_code=status.HTTP_202_ACCEPTED)
async def submit_transaction(transaction: TransactionRequest):
    """
    HU-001: Recibe transacción y responde 202 Accepted
    El procesamiento es asíncrono vía RabbitMQ
    
    Nota del desarrollador:
    La IA sugirió 200 OK. Lo cambié a 202 Accepted porque el procesamiento
    es asíncrono - esto comunica mejor la semántica al cliente.
    """
    try:
        # Instanciar directamente con las factories
        repository = _repository_factory()
        cache = _cache_factory()
        publisher = _publisher_factory()
        
        # Ajustar el monto según el tipo de transacción
        transaction_data = transaction.model_dump()
        transaction_type = transaction_data.get('transaction_type', 'transfer')
        
        # Transferencias, pagos y recargas son salidas de dinero (negativo)
        # Depósitos son entradas de dinero (positivo)
        if transaction_type in ['transfer', 'payment', 'recharge']:
            # Hacer el monto negativo si no lo es
            if transaction_data['amount'] > 0:
                transaction_data['amount'] = -transaction_data['amount']
        # Para 'deposit' el monto ya es positivo, no se modifica
        
        # Crear estrategias
        from decimal import Decimal
        from src.config import settings
        from src.domain.strategies.amount_threshold import AmountThresholdStrategy
        from src.domain.strategies.location_check import LocationStrategy
        from src.domain.strategies.device_validation import DeviceValidationStrategy
        from src.domain.strategies.rapid_transaction import RapidTransactionStrategy
        from src.domain.strategies.unusual_time import UnusualTimeStrategy
        
        strategies = [
            AmountThresholdStrategy(Decimal(str(settings.amount_threshold))),
            LocationStrategy(settings.location_radius_km),
            DeviceValidationStrategy(redis_client=cache.redis_sync),
            RapidTransactionStrategy(redis_client=cache.redis_sync),
            UnusualTimeStrategy(audit_repository=repository),
        ]
        
        # Crear e invocar use case
        from src.application.use_cases import EvaluateTransactionUseCase
        evaluate_use_case = EvaluateTransactionUseCase(repository, publisher, cache, strategies)
        
        result = await evaluate_use_case.execute(transaction_data)
        return {
            "status": "accepted",
            "transaction_id": transaction.id,
            "risk_level": result["risk_level"],
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/audit/all")
async def get_all_evaluations():
    """
    HU-002: Consulta todas las evaluaciones para auditoría
    """
    repository = _repository_factory()
    evaluations = await repository.get_all_evaluations()
    return [
        {
            "transaction_id": e.transaction_id,
            "risk_level": e.risk_level.name,
            "reasons": e.reasons,
            "timestamp": _iso_utc(e.timestamp),
            "status": e.status,
            "reviewed_by": e.reviewed_by,
            "reviewed_at": _iso_utc(e.reviewed_at) if e.reviewed_at else None,
        }
        for e in evaluations
    ]


@router.get("/audit/transaction/{transaction_id}")
async def get_evaluation_by_id(transaction_id: str):
    """
    Consulta una evaluación específica por ID
    """
    repository = _repository_factory()
    evaluation = await repository.get_evaluation_by_id(transaction_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": evaluation.transaction_id,
        "risk_level": evaluation.risk_level.name,
        "reasons": evaluation.reasons,
            "timestamp": _iso_utc(evaluation.timestamp),
        "status": evaluation.status,
        "reviewed_by": evaluation.reviewed_by,
        "reviewed_at": _iso_utc(evaluation.reviewed_at)
        if evaluation.reviewed_at
        else None,
    }


@router.get("/audit/user/{user_id}")
async def get_user_transactions(user_id: str):
    """
    Consulta todas las transacciones de un usuario específico
    
    Returns:
        Lista de evaluaciones de transacciones del usuario
    """
    repository = _repository_factory()
    evaluations = repository.get_evaluations_by_user(user_id)
    
    if not evaluations:
        return []
    
    return [
        {
            "transaction_id": e.transaction_id,
            "user_id": user_id,
            "risk_level": e.risk_level.name,
            "reasons": e.reasons,
            "status": e.status,
            "evaluated_at": _iso_utc(e.evaluated_at) if hasattr(e, 'evaluated_at') and e.evaluated_at else _iso_utc(e.timestamp),
            "reviewed_by": e.reviewed_by,
            "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
        }
        for e in evaluations
    ]


@api_v1_router.put("/transaction/review/{transaction_id}")
async def review_transaction(
    transaction_id: str,
    review: ReviewRequest,
    analyst_id: str = Header(..., alias="X-Analyst-ID"),
):
    """
    HU-010: Analista toma decisión final sobre transacción
    
    Nota del desarrollador:
    La IA sugirió recibir analyst_id en el body. Lo moví a un header
    para separar datos de autenticación de datos de negocio.
    """
    from starlette.concurrency import run_in_threadpool
    from src.application.use_cases import ReviewTransactionUseCase
    
    try:
        # Instanciar el use case correctamente
        repository = _repository_factory()
        review_use_case = ReviewTransactionUseCase(repository)
        
        # Ejecutar en thread pool para no bloquear el event loop
        await run_in_threadpool(
            review_use_case.execute, transaction_id, review.decision, analyst_id
        )
        return {"status": "reviewed", "decision": review.decision}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/config/thresholds")
async def get_thresholds():
    """
    HU-009: Consulta configuración actual de umbrales
    """
    cache = _cache_factory()
    config = await cache.get_threshold_config()
    if config is None:
        # Valores por defecto desde settings
        from src.infrastructure.config import settings

        return {
            "amount_threshold": settings.amount_threshold,
            "location_radius_km": settings.location_radius_km,
            "source": "default",
        }

    config["source"] = "cache"
    return config


@router.put("/config/thresholds")
async def update_thresholds(
    config: ThresholdConfigRequest,
    analyst_id: str = Header(..., alias="X-Analyst-ID"),
):
    """
    HU-008: Actualiza umbrales sin redespliegue
    
    Nota del desarrollador:
    La IA no contempló auditoría de cambios. Agregué analyst_id
    para saber quién modificó la configuración (compliance requirement).
    """
    cache = _cache_factory()
    await cache.set_threshold_config(
        amount_threshold=config.amount_threshold,
        location_radius_km=config.location_radius_km,
    )

    # FUTURE: Guardar en MongoDB para auditoría (tracked in backlog)
    return {
        "status": "updated",
        "updated_by": analyst_id,
        "config": config.model_dump(),
    }


# ============================================================================
# Endpoints API v1 para Frontends
# ============================================================================

@api_v1_router.post("/transaction/validate")
async def validate_transaction_sync(transaction: TransactionValidateRequest):
    """
    Validación sincrónica de transacción para Frontend Usuario
    
    Endpoint específico para el simulador de transacciones.
    Retorna resultado inmediato con status, riskScore y violations.
    """
    try:
        logger.debug("[ROUTE] Received - userId: %s, deviceId: %s", transaction.userId, transaction.deviceId)
        
        # Instanciar dependencias
        repository = _repository_factory()
        cache = _cache_factory()
        publisher = _publisher_factory()
        
        # Obtener reglas deshabilitadas y crear estrategias
        disabled_rules = await _get_disabled_rules(cache)
        strategies = await _build_strategies(disabled_rules, cache, repository)
        
        # Crear use case
        from src.application.use_cases import EvaluateTransactionUseCase
        import uuid
        evaluate_use_case = EvaluateTransactionUseCase(repository, publisher, cache, strategies)
        
        # Parsear ubicación y ajustar monto
        location_dict = _parse_location(transaction.location)
        transaction_type = getattr(transaction, 'transactionType', 'transfer')
        adjusted_amount = _adjust_amount_by_type(transaction.amount, transaction_type)
        
        # Preparar payload
        transaction_data = {
            "id": str(uuid.uuid4()),
            "amount": adjusted_amount,
            "user_id": transaction.userId,
            "location": location_dict,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": transaction.deviceId,
            "transaction_type": transaction_type,
            "description": getattr(transaction, 'description', None)
        }
        
        logger.debug("[ROUTE] transaction_data: device_id=%s", transaction_data.get('device_id'))
        
        # Evaluar transacción
        result = await evaluate_use_case.execute(transaction_data)
        
        # Mapear resultado
        risk_level = result["risk_level"]
        status_value, risk_score = _map_risk_to_response(risk_level)
        violations = result.get("reasons", [])
        
        return {
            "status": status_value,
            "transactionId": transaction_data["id"],
            "riskScore": risk_score,
            "riskLevel": risk_level,
            "violations": violations
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _get_threshold_config(config, settings):
    """Extrae los umbrales de configuración."""
    amount_threshold = config.get("amount_threshold", settings.amount_threshold) if config else settings.amount_threshold
    location_radius = config.get("location_radius_km", settings.location_radius_km) if config else settings.location_radius_km
    return amount_threshold, location_radius

def _build_default_rules(amount_threshold, location_radius):
    """Construye la lista de reglas predeterminadas."""
    return [
        {
            "id": "rule_amount_threshold",
            "name": "RuleMontoAlto",
            "type": "amount_threshold",
            "parameters": {
                "threshold": amount_threshold
            },
            "enabled": True,
            "order": 1
        },
        {
            "id": "rule_location_check",
            "name": "RuleUbicacionInusual",
            "type": "location_check",
            "parameters": {
                "radius_km": location_radius
            },
            "enabled": True,
            "order": 2
        },
        {
            "id": "rule_device_validation",
            "name": "RuleValidacionDispositivo",
            "type": "device_validation",
            "parameters": {
                "device_memory_days": 90
            },
            "enabled": True,
            "order": 3
        },
        {
            "id": "rule_rapid_transaction",
            "name": "RuleTransaccionesRapidas",
            "type": "rapid_transaction",
            "parameters": {
                "max_transactions": 3,
                "time_window_minutes": 5
            },
            "enabled": True,
            "order": 4
        },
        {
            "id": "rule_unusual_time",
            "name": "RuleHorarioInusual",
            "type": "unusual_time",
            "parameters": {
                "deviation_threshold": 0.3
            },
            "enabled": True,
            "order": 5
        }
    ]

async def _update_rule_parameter(cache, rule_id: str, param_key: str, default_rules, param_type=int):
    """Actualiza un parámetro específico de una regla desde Redis."""
    value = await cache.redis.get(f"rule_config:{rule_id}:{param_key}")
    if value:
        for rule in default_rules:
            if rule["id"] == rule_id:
                rule["parameters"][param_key] = param_type(value)

async def _load_device_validation_params(cache, default_rules):
    """Carga parámetros de device_validation."""
    await _update_rule_parameter(cache, "rule_device_validation", "device_memory_days", default_rules, int)

async def _load_rapid_transaction_params(cache, default_rules):
    """Carga parámetros de rapid_transaction."""
    await _update_rule_parameter(cache, "rule_rapid_transaction", "max_transactions", default_rules, int)
    await _update_rule_parameter(cache, "rule_rapid_transaction", "time_window_minutes", default_rules, int)

async def _load_unusual_time_params(cache, default_rules):
    """Carga parámetros de unusual_time."""
    await _update_rule_parameter(cache, "rule_unusual_time", "deviation_threshold", default_rules, float)

async def _load_custom_rule_parameters(cache, default_rules):
    """Carga parámetros personalizados de Redis para las reglas."""
    try:
        await _load_device_validation_params(cache, default_rules)
        await _load_rapid_transaction_params(cache, default_rules)
        await _load_unusual_time_params(cache, default_rules)
    except Exception as e:
        print(f"Error loading custom rule parameters from Redis: {e}")

async def _get_deleted_rules(cache):
    """Obtiene las reglas eliminadas de Redis."""
    deleted_rules = set()
    try:
        deleted_set = await cache.redis.smembers("deleted_default_rules")
        deleted_rules = {r.decode('utf-8') if isinstance(r, bytes) else r for r in deleted_set}
    except Exception as e:
        print(f"Error loading deleted rules: {e}")
    return deleted_rules

async def _get_disabled_rules(cache):
    """Obtiene las reglas deshabilitadas de Redis."""
    disabled_rules = set()
    try:
        disabled_set = await cache.redis.smembers("disabled_default_rules")
        disabled_rules = {r.decode('utf-8') if isinstance(r, bytes) else r for r in disabled_set}
    except Exception as e:
        print(f"Error loading disabled rules: {e}")
    return disabled_rules

def _get_custom_rules(repository):
    """Obtiene reglas personalizadas de MongoDB."""
    custom_rules = []
    try:
        if hasattr(repository, 'db'):
            cursor = repository.db.custom_rules.find({})
            for rule_doc in cursor:
                custom_rules.append({
                    "id": rule_doc["id"],
                    "name": rule_doc["name"],
                    "type": rule_doc["type"],
                    "parameters": rule_doc["parameters"],
                    "enabled": rule_doc["enabled"],
                    "order": rule_doc["order"]
                })
    except Exception as e:
        print(f"Error loading custom rules: {e}")
    return custom_rules

@api_v1_router.get("/admin/rules")
async def get_rules():
    """
    Lista todas las reglas activas
    
    Retorna información completa de cada regla incluyendo
    ID, nombre, tipo, parámetros, estado y orden de prioridad.
    """
    try:
        cache = _cache_factory()
        
        # Obtener configuración actual de umbrales
        config = await cache.get_threshold_config()
        
        from src.config import settings
        amount_threshold, location_radius = _get_threshold_config(config, settings)
        
        # Definir reglas predeterminadas
        default_rules = _build_default_rules(amount_threshold, location_radius)
        
        # Leer parámetros personalizados desde Redis si existen
        await _load_custom_rule_parameters(cache, default_rules)
        
        # Obtener reglas ELIMINADAS de Redis (estas NO deben aparecer)
        deleted_rules = await _get_deleted_rules(cache)
        
        # Filtrar reglas ELIMINADAS (no deben aparecer en la lista)
        default_rules = [r for r in default_rules if r["id"] not in deleted_rules]
        
        # Obtener reglas DESHABILITADAS de Redis (estas sí deben aparecer pero con enabled=false)
        disabled_rules = await _get_disabled_rules(cache)
        
        # Marcar reglas predeterminadas deshabilitadas (NO filtrarlas)
        for rule in default_rules:
            if rule["id"] in disabled_rules:
                rule["enabled"] = False
        
        # Obtener reglas personalizadas de MongoDB (TODAS, no solo enabled)
        repository = _repository_factory()
        custom_rules = _get_custom_rules(repository)
        
        # Combinar y ordenar por prioridad
        all_rules = default_rules + custom_rules
        all_rules.sort(key=lambda x: x["order"])
        
        return all_rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rules: {str(e)}")


@api_v1_router.put("/admin/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    rule_params: RuleParametersRequest,
    analyst_id: str = Header(..., alias="X-Analyst-ID")
):
    """
    Actualiza parámetros de una regla específica
    
    Permite modificar los parámetros de configuración de una regla
    sin necesidad de redesplegar el sistema.
    """
    try:
        cache = _cache_factory()
        repository = _repository_factory()
        default_rule_ids = _get_default_rule_ids()
        
        # Manejar cambio de estado enabled para reglas predeterminadas
        if "enabled" in rule_params.parameters and rule_id in default_rule_ids:
            enabled = rule_params.parameters.get("enabled")
            return await _handle_rule_enabled_state(rule_id, enabled, cache, analyst_id)
        
        # Actualizar según el tipo de regla
        rule_data = None
        if rule_id == "rule_amount_threshold":
            await _update_amount_threshold(rule_params, cache)
        elif rule_id == "rule_location_check":
            await _update_location_check(rule_params, cache)
        elif rule_id == "rule_device_validation":
            rule_data = await _update_device_validation(rule_id, rule_params, cache)
        elif rule_id == "rule_rapid_transaction":
            rule_data = await _update_rapid_transaction(rule_id, rule_params, cache)
        elif rule_id == "rule_unusual_time":
            rule_data = await _update_unusual_time(rule_id, rule_params, cache)
        else:
            # Intentar actualizar regla personalizada en MongoDB
            _update_custom_rule(rule_id, rule_params, repository, analyst_id)
        
        # Construir respuesta
        if rule_data is None:
            rule_data = {"id": rule_id, "parameters": rule_params.parameters}
        
        return {
            "success": True,
            "rule": {**rule_data, "updated_by": analyst_id}
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating rule: {str(e)}")


@api_v1_router.get("/admin/transactions/log")
async def get_transactions_log(
    status: Optional[str] = Query(None, description="Filter by status: APPROVED, SUSPICIOUS, REJECTED"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of transactions to return (omit for all)"),
    user_id: Optional[str] = Query(None, description="Filter by user ID")
):
    """
    Log completo de transacciones con filtros
    
    Permite filtrar por estado, usuario y limitar cantidad de resultados.
    Utilizado por el Dashboard Admin para monitoreo.
    """
    try:
        repository = _repository_factory()
        
        # Obtener todas las evaluaciones
        evaluations = await repository.get_all_evaluations()
        
        # Filtrar por user_id si se especifica
        if user_id:
            evaluations = [e for e in evaluations if e.user_id == user_id]
        
        # Filtrar por status si se especifica
        if status:
            # Mapear status del frontend a status del backend
            status_map = {
                "APPROVED": "APPROVED",
                "SUSPICIOUS": "PENDING_REVIEW",
                "REJECTED": "REJECTED"
            }
            backend_status = status_map.get(status.upper(), status.upper())
            evaluations = [e for e in evaluations if e.status == backend_status]
        
        # Limitar resultados si se especificó un límite
        if limit is not None:
            evaluations = evaluations[:limit]
        
        # Helper para mapear status
        def map_status_to_frontend(status: str) -> str:
            if status == "APPROVED":
                return "APPROVED"
            elif status == "PENDING_REVIEW":
                return "SUSPICIOUS"
            else:
                return "REJECTED"
        
        # Formatear respuesta con datos de la evaluación
        result = []
        for e in evaluations:
            frontend_status = map_status_to_frontend(e.status)
            
            result.append({
                "id": e.transaction_id,
                "amount": float(e.amount) if e.amount else 0.0,
                "userId": e.user_id,
                "date": _iso_utc(e.timestamp),
                "status": frontend_status,
                "violations": e.reasons,
                "riskLevel": e.risk_level.name,
                "location": f"{e.location.latitude}, {e.location.longitude}" if e.location else "N/A",
                "userAuthenticated": e.user_authenticated,
                "reviewedBy": e.reviewed_by,
                "reviewedAt": _iso_utc(e.reviewed_at) if e.reviewed_at else None
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transaction log: {str(e)}")


@api_v1_router.get("/admin/metrics")
async def get_metrics():
    """
    KPIs del sistema para Dashboard Admin
    
    Retorna métricas clave: total de transacciones, tasas de bloqueo,
    transacciones en revisión y risk score promedio.
    """
    try:
        repository = _repository_factory()
        
        # Obtener todas las evaluaciones
        evaluations = await repository.get_all_evaluations()
        
        if not evaluations:
            return {
                "totalTransactions": 0,
                "blockedRate": 0.0,
                "suspiciousRate": 0.0,
                "avgRiskScore": 0
            }
        
        total = len(evaluations)
        blocked = sum(1 for e in evaluations if e.status == "REJECTED")
        suspicious = sum(1 for e in evaluations if e.status in ["SUSPICIOUS", "PENDING_REVIEW"])
        
        # Calcular risk score promedio (simplificado)
        risk_scores = []
        for e in evaluations:
            if e.risk_level.name == "LOW_RISK":
                risk_scores.append(15)
            elif e.risk_level.name == "MEDIUM_RISK":
                risk_scores.append(62)
            else:  # HIGH_RISK
                risk_scores.append(95)
        
        avg_risk_score = sum(risk_scores) // len(risk_scores) if risk_scores else 0
        
        return {
            "totalTransactions": total,
            "blockedRate": round((blocked / total) * 100, 2) if total > 0 else 0.0,
            "suspiciousRate": round((suspicious / total) * 100, 2) if total > 0 else 0.0,
            "avgRiskScore": avg_risk_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@api_v1_router.get("/admin/trends")
async def get_trends():
    """
    Tendencias de transacciones de las últimas 24h agrupadas por hora
    
    Retorna conteos de transacciones aprobadas, sospechosas y rechazadas
    por cada hora, permitiendo visualizar patrones temporales.
    """
    from datetime import timedelta
    from collections import defaultdict
    
    try:
        repository = _repository_factory()
        
        # Obtener todas las evaluaciones
        evaluations = await repository.get_all_evaluations()
        
        if not evaluations:
            # Retornar 24 horas con valores en 0
            return [
                {"time": f"{h:02d}:00", "approved": 0, "suspicious": 0, "rejected": 0}
                for h in range(24)
            ]
        
        # Filtrar evaluaciones de las últimas 24h
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        recent_evaluations = [e for e in evaluations if e.timestamp >= last_24h]
        
        # Agrupar por hora
        hourly_data = defaultdict(lambda: {"approved": 0, "suspicious": 0, "rejected": 0})
        
        for e in recent_evaluations:
            hour = e.timestamp.strftime("%H:00")
            
            if e.status == "APPROVED":
                hourly_data[hour]["approved"] += 1
            elif e.status in ["PENDING_REVIEW", "SUSPICIOUS"]:
                hourly_data[hour]["suspicious"] += 1
            elif e.status == "REJECTED":
                hourly_data[hour]["rejected"] += 1
        
        # Generar resultado para todas las 24 horas
        result = []
        for h in range(24):
            time_key = f"{h:02d}:00"
            result.append({
                "time": time_key,
                "approved": hourly_data[time_key]["approved"],
                "suspicious": hourly_data[time_key]["suspicious"],
                "rejected": hourly_data[time_key]["rejected"]
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")


@api_v1_router.post("/admin/rules")
async def create_rule(
    rule: dict,
    analyst_id: str = Header(..., alias="X-Analyst-ID")
):
    """
    Crea una nueva regla personalizada
    
    Permite a los analistas crear reglas de fraude personalizadas
    sin necesidad de modificar el código.
    """
    try:
        # Validar datos requeridos
        if "name" not in rule or "type" not in rule or "parameters" not in rule:
            raise ValueError("Missing required fields: name, type, parameters")
        
        # Generar ID único para la regla
        import uuid
        from datetime import datetime
        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        
        # Preparar documento para MongoDB
        rule_doc = {
            "id": rule_id,
            "name": rule["name"],
            "type": rule["type"],
            "parameters": rule["parameters"],
            "enabled": rule.get("enabled", True),
            "order": rule.get("order", 999),
            "created_by": analyst_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Guardar en MongoDB
        repository = _repository_factory()
        if hasattr(repository, 'db'):
            repository.db.custom_rules.insert_one(rule_doc)
        
        return {
            "success": True,
            "message": "Rule created successfully",
            "rule": {
                "id": rule_id,
                "name": rule["name"],
                "type": rule["type"],
                "parameters": rule["parameters"],
                "enabled": rule.get("enabled", True),
                "order": rule.get("order", 999)
            },
            "created_by": analyst_id
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating rule: {str(e)}")


@api_v1_router.delete("/admin/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    analyst_id: str = Header(..., alias="X-Analyst-ID")
):
    """
    Elimina permanentemente una regla (predeterminada o personalizada)
    
    Las reglas predeterminadas se marcan como ELIMINADAS en Redis (deleted_default_rules).
    Las reglas personalizadas se eliminan de MongoDB.
    """
    try:
        default_rule_ids = _get_default_rule_ids()
        cache = _cache_factory()
        repository = _repository_factory()
        
        if rule_id in default_rule_ids:
            await _delete_default_rule(rule_id, cache)
            message = "Default rule deleted permanently"
        else:
            _delete_custom_rule(rule_id, repository)
            message = "Custom rule deleted successfully"
        
        return {
            "success": True,
            "message": message,
            "deleted_by": analyst_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting rule: {str(e)}")


@api_v1_router.post("/admin/rules/reorder")
async def reorder_rules(
    reorder: RuleReorderRequest,
    analyst_id: str = Header(..., alias="X-Analyst-ID")
):
    """
    Reordena el Chain of Responsibility
    
    Permite cambiar el orden de ejecución de las reglas de fraude.
    Implementación simplificada - en producción guardar en BD.
    """
    try:
        # Validar que los IDs sean válidos
        valid_rule_ids = {"rule_amount_threshold", "rule_location_check"}
        invalid_ids = [rid for rid in reorder.ruleIds if rid not in valid_rule_ids]
        
        if invalid_ids:
            raise ValueError(f"Invalid rule IDs: {invalid_ids}")
        
        # En producción, actualizar el orden en la base de datos
        # Por ahora, solo retornar éxito
        return {
            "success": True,
            "newOrder": [
                {"id": rid, "order": idx + 1}
                for idx, rid in enumerate(reorder.ruleIds)
            ],
            "updated_by": analyst_id
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reordering rules: {str(e)}")

# ============================================================================
# ENDPOINTS PARA USUARIO
# ============================================================================

@api_v1_router.get("/user/transactions/{user_id}")
async def get_user_transactions(
    user_id: str,
    limit: int = Query(50, gt=0, le=100, description="Máximo de transacciones a retornar")
):
    """
    Obtiene todas las transacciones de un usuario específico
    
    Permite al usuario ver:
    - Historial de sus transacciones
    - Estado actual (APPROVED, SUSPICIOUS, REJECTED)
    - Si necesita autenticar alguna transacción sospechosa
    """
    from starlette.concurrency import run_in_threadpool
    
    try:
        repository = _repository_factory()
        # Ejecutar en thread pool ya que es síncrono
        evaluations = await run_in_threadpool(
            repository.get_evaluations_by_user, user_id
        )
        
        # Limitar resultados
        evaluations = evaluations[:limit]
        
        return [
            {
                "id": e.transaction_id,
                "userId": e.user_id,
                "amount": float(e.amount) if e.amount else None,
                "location": f"{e.location.latitude}, {e.location.longitude}" if e.location else None,
                "timestamp": _iso_utc(e.timestamp),
                "status": e.status,
                "riskScore": e.risk_level.value,
                "violations": e.reasons,
                "needsAuthentication": e.status == "PENDING_REVIEW" and e.user_authenticated is None,
                "userAuthenticated": e.user_authenticated,
                "reviewedBy": e.reviewed_by,
                "reviewedAt": _iso_utc(e.reviewed_at) if e.reviewed_at else None,
                "transactionType": e.transaction_type,
                "description": e.description
            }
            for e in evaluations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving transactions: {str(e)}")


@api_v1_router.post("/user/transaction/{transaction_id}/authenticate")
async def authenticate_transaction(
    transaction_id: str,
    auth: UserAuthenticateRequest
):
    """
    Permite al usuario autenticar una transacción sospechosa
    
    El usuario confirma si la transacción fue realizada por él:
    - confirmed=True: "Fui yo" → Ayuda al analista a aprobarla
    - confirmed=False: "No fui yo" → Indica posible fraude
    """
    from starlette.concurrency import run_in_threadpool
    
    try:
        repository = _repository_factory()
        
        # Obtener la evaluación
        evaluation = await run_in_threadpool(
            repository.get_evaluation_by_id, transaction_id
        )
        
        if evaluation is None:
            raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")
        
        # Solo se puede autenticar transacciones en estado PENDING_REVIEW (SUSPICIOUS)
        if evaluation.status != "PENDING_REVIEW":
            raise HTTPException(
                status_code=400, 
                detail=f"Transaction is {evaluation.status}, cannot authenticate"
            )
        
        # Aplicar autenticación del usuario
        evaluation.authenticate_by_user(auth.confirmed)
        
        # Guardar en BD
        await run_in_threadpool(repository.update_evaluation, evaluation)
        
        return {
            "status": "authenticated",
            "transaction_id": transaction_id,
            "confirmed": auth.confirmed,
            "message": "Gracias por confirmar. Un analista revisará tu transacción pronto." if auth.confirmed 
                      else "Gracias por alertarnos. Bloquearemos esta transacción."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error authenticating transaction: {str(e)}")
