"""
Application Layer - Casos de Uso
Orquesta la lógica de negocio coordinando Domain y Infrastructure

Cumplimiento SOLID:
- Single Responsibility: Cada caso de uso tiene una responsabilidad única
- Open/Closed: Extensible mediante nuevas estrategias sin modificar código
- Dependency Inversion: Depende de interfaces (puertos), no de implementaciones

Nota del desarrollador (María Gutiérrez):
La IA sugirió un método genérico "process_transaction" que hacía todo.
Lo refactoricé en dos casos de uso separados (EvaluateTransaction y ReviewTransaction)
para cumplir con Single Responsibility y Command Query Separation (CQS).
"""
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional
from src.domain.models import Transaction, FraudEvaluation, Location, RiskLevel
from src.domain.strategies.base import FraudStrategy
from src.application.interfaces import (
    TransactionRepository,
    MessagePublisher,
    CacheService,
)

logger = logging.getLogger(__name__)


class EvaluateTransactionUseCase:
    """
    Caso de uso: Evaluar una transacción usando estrategias de fraude
    
    HU-001: Recibe transacción y ejecuta evaluación asíncrona
    HU-003 y HU-005: Aplica reglas de negocio (monto y ubicación)
    
    Cumple Dependency Inversion: Recibe interfaces (puertos) mediante inyección
    
    Nota del desarrollador:
    La IA propuso recibir las estrategias hardcodeadas. Las recibo como parámetro
    en el constructor para cumplir con Dependency Injection y facilitar testing.
    Esto también cumple con Open/Closed: puedo agregar estrategias sin modificar la clase.
    """

    def __init__(
        self,
        repository: TransactionRepository,
        publisher: MessagePublisher,
        cache: CacheService,
        strategies: List[FraudStrategy],
    ) -> None:
        """
        Inicializa el caso de uso con sus dependencias
        
        Args:
            repository: Puerto para persistencia
            publisher: Puerto para mensajería
            cache: Puerto para caché
            strategies: Lista de estrategias de detección
        """
        self.repository = repository
        self.publisher = publisher
        self.cache = cache
        self.strategies = strategies

    async def execute(self, transaction_data: dict) -> Dict[str, Any]:
        """
        Ejecuta la evaluación de una transacción
        
        Args:
            transaction_data: Dict con datos de la transacción
        
        Returns:
            Dict con resultado de la evaluación
        
        Raises:
            ValueError: Si los datos son inválidos
            KeyError: Si faltan campos requeridos
        
        Nota del desarrollador:
        La IA sugirió retornar la entidad FraudEvaluation directamente.
        Lo cambié a dict para evitar que Infrastructure dependa de Domain
        (cumple Dependency Inversion en sentido opuesto).
        """
        # 1. Convertir datos a entidad Transaction
        transaction = self._build_transaction_from_data(transaction_data)
        logger.debug("[USE_CASE] Transaction created - device_id: %s", transaction.device_id)

        # 2. Obtener ubicación histórica del usuario (si existe)
        historical_location = await self._get_historical_location(transaction.user_id)

        # 3. Ejecutar todas las estrategias y combinar resultados
        all_reasons = []
        max_risk_level = RiskLevel.LOW_RISK

        for strategy in self.strategies:
            result = strategy.evaluate(transaction, historical_location)
            
            # Acumular razones
            all_reasons.extend(result["reasons"])
            
            # Nota del desarrollador:
            # La IA sugirió usar un if/elif largo. Lo refactoricé usando
            # la comparación de enums para determinar el máximo nivel de riesgo,
            # cumpliendo con "Don't Repeat Yourself" (DRY).
            if result["risk_level"].value > max_risk_level.value:
                max_risk_level = result["risk_level"]

        # 4. Crear evaluación con el resultado final
        evaluation = FraudEvaluation(
            transaction_id=transaction.id,
            risk_level=max_risk_level,
            reasons=all_reasons,
            timestamp=datetime.now(),
        )

        # 5. Persistir evaluación
        await self.repository.save_evaluation(evaluation)

        # 6. Actualizar ubicación en caché
        await self.cache.set_user_location(
            user_id=transaction.user_id,
            latitude=transaction.location.latitude,
            longitude=transaction.location.longitude,
        )

        # 7. Si es HIGH_RISK o MEDIUM_RISK, enviar a revisión manual (HU-010)
        if max_risk_level in (RiskLevel.HIGH_RISK, RiskLevel.MEDIUM_RISK):
            await self.publisher.publish_for_manual_review(
                {
                    "transaction_id": transaction.id,
                    "risk_level": max_risk_level.name,
                    "reasons": all_reasons,
                    "amount": float(transaction.amount),
                    "user_id": transaction.user_id,
                }
            )

        # 8. Retornar resultado
        return {
            "transaction_id": transaction.id,
            "risk_level": max_risk_level.name,
            "reasons": all_reasons,
            "status": evaluation.status,
        }

    def _build_transaction_from_data(self, data: dict) -> Transaction:
        """
        Construye una entidad Transaction desde datos dict
        
        Nota del desarrollador:
        La IA sugirió acceso directo con data["key"]. Agregué validaciones
        y conversiones explícitas para "hacer los estados inválidos irrepresentables"
        y cumplir con "Parse, don't validate".
        """
        try:
            location_data = data["location"]
            location = Location(
                latitude=float(location_data["latitude"]),
                longitude=float(location_data["longitude"]),
            )

            timestamp_str = data.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.now()

            logger.debug("[USE_CASE] Building Transaction - device_id from data: %s", data.get('device_id'))

            return Transaction(
                id=data["id"],
                amount=Decimal(str(data["amount"])),
                user_id=data["user_id"],
                location=location,
                timestamp=timestamp,
                device_id=data.get("device_id"),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid data format: {e}")

    async def _get_historical_location(self, user_id: str) -> Optional[Location]:
        """
        Obtiene la ubicación histórica del usuario desde caché
        
        Returns:
            Location si existe, None si es usuario nuevo
        """
        location_data = await self.cache.get_user_location(user_id)
        if location_data is None:
            return None

        try:
            return Location(
                latitude=location_data["latitude"],
                longitude=location_data["longitude"],
            )
        except (KeyError, ValueError):
            # Datos corruptos en caché, tratarlo como usuario sin historial
            return None


class ReviewTransactionUseCase:
    """
    Caso de uso: Revisar transacción manualmente (Human in the Loop)
    
    HU-010: Permite al analista aprobar o rechazar una transacción
    
    Cumple Single Responsibility: Solo maneja revisión manual
    """

    def __init__(self, repository: TransactionRepository) -> None:
        """
        Inicializa el caso de uso con su dependencia
        
        Args:
            repository: Puerto para persistencia
        
        Nota del desarrollador:
        La IA sugirió también inyectar MessagePublisher para notificaciones.
        Lo eliminé para cumplir con YAGNI (You Aren't Gonna Need It) -
        las notificaciones se pueden agregar después si es necesario.
        """
        self.repository = repository

    async def execute(
        self, transaction_id: str, decision: str, analyst_id: str
    ) -> None:
        """
        Aplica una decisión manual a una transacción
        
        Args:
            transaction_id: ID de la transacción
            decision: 'APPROVED' o 'REJECTED'
            analyst_id: ID del analista
        
        Raises:
            ValueError: Si la transacción no existe o la decisión es inválida
        
        Nota del desarrollador:
        La IA sugirió retornar la evaluación actualizada. Lo cambié a void (None)
        para cumplir con Command Query Separation: este es un comando, no una query.
        """
        # 1. Obtener evaluación existente
        evaluation = await self.repository.get_evaluation_by_id(transaction_id)

        if evaluation is None:
            raise ValueError(f"Transaction {transaction_id} not found")

        # 2. Aplicar decisión manual (la validación está en la entidad)
        evaluation.apply_manual_decision(decision, analyst_id)

        # 3. Persistir actualización
        await self.repository.update_evaluation(evaluation)
