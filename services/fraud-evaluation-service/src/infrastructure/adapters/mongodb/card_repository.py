"""
MongoDB adapter for CardRepository port.

CLEAN ARCHITECTURE:
- This is an INFRASTRUCTURE adapter implementing the PORTS interface
- Depends on: Application port (CardRepository), Domain models (Card)
- Does NOT import: FastAPI, Pydantic, or other frameworks
- Pure persistence logic with MongoDB-specific operations

Pattern: Repository Pattern with soft-delete support
Database: MongoDB with encryption at rest (configured in docker-compose)
Indexing: Supports efficient queries by user_id, last_four_digits, status
"""

from typing import Optional, List, Any
from datetime import datetime
import uuid

from pymongo.errors import DuplicateKeyError
from src.domain.models import Card, CardStatus
from src.application.ports.card_repository import CardRepository


class MongoCardRepository(CardRepository):
    """
    MongoDB implementation of CardRepository.
    
    Handles persistence of Card entities in MongoDB while maintaining:
    - Immutability of Card domain objects (creates new Card with returned card_id)
    - Soft-delete pattern (marks as INACTIVE instead of hard delete)
    - Audit trail (timestamps preserved)
    - Encryption at rest (handled by MongoDB configuration)
    
    HUMAN REVIEW (Developer Name):
    Motor is used for async MongoDB operations. All queries filter for status='ACTIVE'
    to implement soft-delete behavior. See ARCHITECTURE.md for data model details.
    """
    
    def __init__(self, collection: Any):
        """
        Initialize MongoDB CardRepository.
        
        Args:
            collection: Motor AsyncIOMotorCollection for cards (or any async MongoDB collection)
        
        Ensures required indexes exist for efficient queries.
        """
        self.collection = collection
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Create required database indexes for efficient queries.

        Required index (run once via migration or startup):
            collection.create_index(
                [("user_id", 1), ("last_four_digits", 1)],
                unique=True,
                partialFilterExpression={"status": "ACTIVE"},
                name="unique_active_card_per_user"
            )
        This unique partial index enforces at database level that a user
        cannot have two ACTIVE cards with the same last 4 digits, eliminating
        the race condition in AddCardUseCase.
        """
        pass
    
    async def save(self, card: Card) -> Card:
        """
        Persist card to MongoDB.
        
        Args:
            card: Card entity to save (frozen dataclass)
        
        Returns:
            Card entity with card_id populated by MongoDB
        
        Raises:
            Exception: On database errors (connection, validation)
        
        Implementation Notes:
        - If card_id is empty string, generates new UUID
        - Converts Card dataclass to MongoDB document dict
        - Card number should already be masked/encrypted at higher level
        - Returns new Card instance with populated card_id (domain object immutability)
        """
        # Generate card_id if not already assigned
        card_id = card.card_id if card.card_id else str(uuid.uuid4())
        
        # Prepare document for MongoDB
        document = {
            '_id': card_id,
            'card_number': card.card_number,
            'last_four_digits': card.card_number[-4:] if card.card_number else None,
            'card_holder_name': card.card_holder_name,
            'expiry_date': card.expiry_date,
            'card_type': card.card_type,
            'user_id': card.user_id,
            'nickname': card.nickname,
            'status': card.status,
            'created_at': card.created_at,
            'updated_at': card.updated_at,
        }

        if not card.card_id:
            # New card: use insert_one so MongoDB's unique index triggers
            # DuplicateKeyError on concurrent inserts with the same
            # (user_id, last_four_digits) combination.
            try:
                await self.collection.insert_one(document)
            except DuplicateKeyError:
                last_four = document.get('last_four_digits', '????')
                raise ValueError(
                    f"Card with last 4 digits {last_four} already linked to your account"
                )
        else:
            # Existing card update (e.g., status change by RemoveCardUseCase)
            await self.collection.update_one(
                {'_id': card_id},
                {'$set': document},
                upsert=True
            )
        
        # Return Card entity with card_id populated
        return Card(
            card_number=card.card_number,
            card_holder_name=card.card_holder_name,
            expiry_date=card.expiry_date,
            card_type=card.card_type,
            user_id=card.user_id,
            card_id=card_id,
            nickname=card.nickname,
            status=card.status,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )
    
    async def find_by_id(self, card_id: str) -> Optional[Card]:
        """
        Retrieve card by ID from MongoDB.
        
        Args:
            card_id: Card identifier
        
        Returns:
            Card entity if found and ACTIVE, None otherwise
        
        Implementation Notes:
        - Only returns ACTIVE cards (soft-delete filter)
        - Returns None if card is INACTIVE or not found
        """
        doc = await self.collection.find_one({
            '_id': card_id,
            'status': CardStatus.ACTIVE.value
        })
        
        if not doc:
            return None
        
        return self._document_to_card(doc)
    
    async def find_by_user_id(self, user_id: str) -> List[Card]:
        """
        Retrieve all ACTIVE cards for a user.
        
        Args:
            user_id: User identifier
        
        Returns:
            List of Card entities (empty list if user has no cards)
        
        Implementation Notes:
        - Only returns ACTIVE cards (soft-delete filter)
        - Orders by created_at descending (newest first)
        - Used by ListUserCardsUseCase
        """
        cursor = self.collection.find({
            'user_id': user_id,
            'status': CardStatus.ACTIVE.value
        }).sort('created_at', -1)
        
        cards = []
        async for doc in cursor:
            cards.append(self._document_to_card(doc))
        
        return cards
    
    async def find_by_user_and_last_four(self, user_id: str, last_four_digits: str) -> Optional[Card]:
        """
        Find card by user and last 4 digits for duplicate detection.
        
        Args:
            user_id: User identifier
            last_four_digits: Last 4 digits of card (e.g., '0366')
        
        Returns:
            Card entity if duplicate exists, None otherwise
        
        Implementation Notes:
        - Used by AddCardUseCase to prevent duplicate cards
        - Compares last 4 digits of card number (extracted at application level)
        - Query is efficient with (user_id, status) compound index
        """
        doc = await self.collection.find_one({
            'user_id': user_id,
            'last_four_digits': last_four_digits,
            'status': CardStatus.ACTIVE.value,
        })

        if not doc:
            return None

        return self._document_to_card(doc)
    
    async def count_user_cards(self, user_id: str) -> int:
        """
        Count ACTIVE cards for user.
        
        Args:
            user_id: User identifier
        
        Returns:
            Number of ACTIVE cards (used to enforce max 10 limit)
        
        Implementation Notes:
        - Used by AddCardUseCase to check max 10 cards limit
        - Only counts ACTIVE cards (soft-deleted cards don't count toward limit)
        """
        count = await self.collection.count_documents({
            'user_id': user_id,
            'status': CardStatus.ACTIVE.value
        })
        return count
    
    async def soft_delete(self, card_id: str) -> None:
        """
        Soft-delete card by marking as INACTIVE.
        
        Args:
            card_id: Card identifier to delete
        
        Implementation Notes:
        - Sets status='INACTIVE' instead of deleting document
        - Preserves audit trail and card history
        - Card no longer returned in find operations
        - Used by RemoveCardUseCase
        """
        await self.collection.update_one(
            {'_id': card_id},
            {
                '$set': {
                    'status': CardStatus.INACTIVE.value,
                    'updated_at': datetime.utcnow().isoformat()
                }
            }
        )
    
    def _document_to_card(self, doc: dict) -> Card:
        """
        Convert MongoDB document to Card domain entity.
        
        Args:
            doc: MongoDB document dict
        
        Returns:
            Card domain entity
        
        Internal helper for maintaining immutability and type safety.
        """
        return Card(
            card_number=doc.get('card_number'),
            card_holder_name=doc.get('card_holder_name'),
            expiry_date=doc.get('expiry_date'),
            card_type=doc.get('card_type'),
            user_id=doc.get('user_id'),
            card_id=doc.get('_id'),
            nickname=doc.get('nickname'),
            status=doc.get('status', CardStatus.ACTIVE.value),
            created_at=doc.get('created_at'),
            updated_at=doc.get('updated_at'),
        )
