"""
ListUserCardsUseCase - Retrieve all cards for user
"""
from typing import List
from src.domain.models import Card
from src.application.ports.card_repository import CardRepository


class ListUserCardsUseCase:
    """
    List user cards use case
    
    Responsible for:
    1. Fetch all cards for user (active and inactive)
    2. Return card list with masked card numbers for security
    
    Note: Card masking happens in the response serialization
    (domain method Card.mask_card_number() is used by API layer)
    """

    def __init__(self, card_repository: CardRepository):
        self.repository = card_repository

    async def execute(self, user_id: str) -> List[Card]:
        """
        Execute list user cards use case
        
        Args:
            user_id: User to fetch cards for
            
        Returns:
            List of Card entities (may be empty)
        """
        cards = await self.repository.find_by_user_id(user_id)
        return cards
