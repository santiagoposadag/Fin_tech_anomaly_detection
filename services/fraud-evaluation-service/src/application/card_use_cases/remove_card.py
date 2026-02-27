"""
RemoveCardUseCase - Soft-delete card from user account
Implements: HU-015 acceptance criteria (soft delete preserves audit trail)
"""
from datetime import datetime
from src.application.ports.card_repository import CardRepository
from src.application.ports.audit_publisher import AuditEventPublisher
from src.domain.validation.card_validators import get_last_four_digits


class RemoveCardUseCase:
    """
    Remove card use case (soft delete)
    
    Responsible for:
    1. Verify card exists
    2. Verify user owns card (authorization)
    3. Soft-delete card (status = INACTIVE)
    4. Publish audit event
    
    Note: Soft delete preserves card in database for audit trail
    """

    def __init__(
        self,
        card_repository: CardRepository,
        audit_publisher: AuditEventPublisher,
    ):
        self.repository = card_repository
        self.audit_publisher = audit_publisher

    async def execute(self, user_id: str, card_id: str) -> None:
        """
        Execute remove card use case
        
        Args:
            user_id: ID of user removing the card
            card_id: ID of card to remove
            
        Raises:
            ValueError: If card not found, unauthorized, or delete fails
        """
        # 1. Fetch card
        card = await self.repository.find_by_id(card_id)
        if not card:
            raise ValueError("Card not found")

        # 2. Verify authorization (user must own card)
        if card.user_id != user_id:
            raise ValueError("Unauthorized: Cannot remove another user's card")

        # 3. Soft-delete card
        await self.repository.soft_delete(card_id)

        # 4. Publish audit event
        audit_event = {
            'action': 'CARD_REMOVED',
            'card_id': card_id,
            'user_id': user_id,
            'card_type': card.card_type,
            'last_four_digits': get_last_four_digits(card.card_number),
            'timestamp': datetime.utcnow().isoformat(),
        }
        await self.audit_publisher.publish_event(audit_event)
