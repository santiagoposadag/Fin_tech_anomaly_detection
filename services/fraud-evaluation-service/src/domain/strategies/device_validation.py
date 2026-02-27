"""
DeviceValidationStrategy - Valida si el dispositivo ha sido usado previamente.
HU-004: Como sistema, quiero validar si el device_id del usuario ha sido usado
previamente para detectar actividad sospechosa.
"""
import logging
from typing import Dict, Any, Optional
from .base import FraudStrategy
from src.domain.models import Transaction, RiskLevel, Location

logger = logging.getLogger(__name__)


class DeviceValidationStrategy(FraudStrategy):
    """
    Estrategia que valida si el dispositivo ha sido registrado previamente.
    
    Utiliza Redis para cachear información de dispositivos y detecta el uso
    de dispositivos nuevos o no reconocidos que puedan indicar fraude.
    """
    
    def __init__(self, redis_client):
        """
        Inicializa la estrategia con el cliente Redis.
        
        Args:
            redis_client: Cliente Redis para almacenar y recuperar información de dispositivos
        """
        self.redis_client = redis_client
    
    def evaluate(
        self, transaction: Transaction, historical_location: Optional[Location] = None
    ) -> Dict[str, Any]:
        """
        Evalúa si el dispositivo usado en la transacción ha sido usado antes.
        
        Args:
            transaction: La transacción a evaluar
            historical_location: No usado en esta estrategia
            
        Returns:
            Dict con risk_level, reasons y details
        """
        try:
            user_id = transaction.user_id
            device_id = transaction.device_id
            
            if not device_id:
                return {
                    "risk_level": RiskLevel.MEDIUM_RISK,
                    "reasons": ["No se proporcionó device_id"],
                    "details": "Transacción sin identificador de dispositivo"
                }
            
            # Clave de Redis para dispositivos del usuario
            redis_key = f"user_devices:{user_id}"
            
            # Verificar si el dispositivo ya fue registrado
            is_known_device = self.redis_client.sismember(redis_key, device_id)
            
            if is_known_device:
                # Dispositivo conocido - no agregar a violaciones
                return {
                    "risk_level": RiskLevel.LOW_RISK,
                    "reasons": [],  # Sin violaciones
                    "details": f"Dispositivo {device_id} registrado previamente para usuario {user_id}"
                }
            else:
                # Registrar el nuevo dispositivo
                self.redis_client.sadd(redis_key, device_id)
                # Establecer expiración de 90 días
                self.redis_client.expire(redis_key, 90 * 24 * 60 * 60)
                
                return {
                    "risk_level": RiskLevel.HIGH_RISK,
                    "reasons": ["Dispositivo nuevo o no reconocido"],
                    "details": f"Primera transacción desde dispositivo {device_id} para usuario {user_id}"
                }
                
        except Exception as e:
            # En caso de error con Redis, retornar riesgo bajo para no bloquear
            logger.error(f"Error en DeviceValidationStrategy: {e}")
            return {
                "risk_level": RiskLevel.LOW_RISK,
                "reasons": ["Error en validación de dispositivo"],
                "details": "No se pudo validar el dispositivo"
            }

