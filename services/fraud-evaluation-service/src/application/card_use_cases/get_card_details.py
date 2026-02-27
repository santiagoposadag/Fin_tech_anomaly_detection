"""
GetCardDetailsUseCase - Retrieve single card details
"""
from src.domain.models import Card
from src.application.ports.card_repository import CardRepository


class GetCardDetailsUseCase:
    """
    Get card details use case
    
    Responsible for:
    1. Fetch card by ID
    2. Verify user owns card (authorization)
    3. Return card entity
    """

    def __init__(self, card_repository: CardRepository):
        self.repository = card_repository

    async def execute(self, user_id: str, card_id: str) -> Card:
        """
        Execute get card details use case
        
        Args:
            user_id: ID of user requesting card details
            card_id: ID of card to fetch
            
        Returns:
            Card entity
            
        Raises:
            ValueError: If card not found or unauthorized
        """
        # 1. Fetch card
        card = await self.repository.find_by_id(card_id)
        if not card:
            raise ValueError("Card not found")

        # 2. Verify authorization
        if card.user_id != user_id:
            raise ValueError("Unauthorized: Cannot access another user's card")

        return card
