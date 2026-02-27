"""
AddCardUseCase - Add new card to user account
Implements: HU-015 acceptance criteria with validation and duplicate prevention
"""
from datetime import datetime
from typing import Dict, Any
from src.domain.models import Card, CardType, CardStatus
from src.domain.validation.card_validators import (
    validate_card_number,
    validate_expiry_date,
    validate_card_holder_name,
    validate_card_nickname,
    get_last_four_digits,
)
from src.application.ports.card_repository import CardRepository
from src.application.ports.audit_publisher import AuditEventPublisher


class AddCardUseCase:
    """
    Add new card use case
    
    Responsible for:
    1. Validate all card fields
    2. Check for duplicate cards (same last 4 digits)
    3. Enforce max cards limit (10 per user)
    4. Create Card entity
    5. Persist to repository
    6. Publish audit event
    """

    def __init__(
        self,
        card_repository: CardRepository,
        audit_publisher: AuditEventPublisher,
    ):
        self.repository = card_repository
        self.audit_publisher = audit_publisher
        self.MAX_CARDS_PER_USER = 10

    async def execute(self, card_data: Dict[str, Any]) -> Card:
        """
        Execute add card use case
        
        Args:
            card_data: Dictionary with card fields
                - card_number: str (16 digits)
                - card_holder_name: str (3-50 chars)
                - expiry_date: str (MM/YY format)
                - card_type: str ('DEBIT' or 'CREDIT')
                - user_id: str
                - nickname: str (optional, max 20 chars)
                
        Returns:
            Created Card entity
            
        Raises:
            ValueError: If validation fails or business rules violated
        """
        # Extract data
        card_number = card_data.get('card_number')
        card_holder_name = card_data.get('card_holder_name')
        expiry_date = card_data.get('expiry_date')
        card_type = card_data.get('card_type')
        user_id = card_data.get('user_id')
        nickname = card_data.get('nickname')

        # 1. Validate all fields (fail-fast)
        validate_card_number(card_number)
        validate_expiry_date(expiry_date)
        validate_card_holder_name(card_holder_name)
        validate_card_nickname(nickname)

        # 2. Check duplicate (same last 4 digits for this user)
        last_four = get_last_four_digits(card_number)
        existing_card = await self.repository.find_by_user_and_last_four(
            user_id, last_four
        )
        if existing_card:
            raise ValueError(
                f"Card with last 4 digits {last_four} already linked to your account"
            )

        # 3. Check max cards limit
        card_count = await self.repository.count_user_cards(user_id)
        if card_count >= self.MAX_CARDS_PER_USER:
            raise ValueError(
                f"Maximum of {self.MAX_CARDS_PER_USER} cards per account. "
                "Remove a card to add new one."
            )

        # 4. Create Card entity
        card = Card(
            card_number=card_number,
            card_holder_name=card_holder_name,
            expiry_date=expiry_date,
            card_type=card_type,
            user_id=user_id,
            nickname=nickname,
            status='ACTIVE',
            card_id='',  # Will be assigned by repository
        )

        # 5. Persist to repository
        # The repository raises ValueError on duplicate key (race condition safety):
        # two concurrent requests may both pass the duplicate check above, but the
        # repository catches MongoDB's DuplicateKeyError and re-raises as ValueError.
        saved_card = await self.repository.save(card)

        # 6. Publish audit event
        audit_event = {
            'action': 'CARD_ADDED',
            'card_id': saved_card.card_id,
            'user_id': user_id,
            'card_type': card_type,
            'last_four_digits': last_four,
            'timestamp': datetime.utcnow().isoformat(),
        }
        await self.audit_publisher.publish_event(audit_event)

        return saved_card
