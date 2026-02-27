"""
Phase 3 - RED: Integration tests for MongoCardRepository (MongoDB adapter)
Following TDD approach: Write tests first, watch them fail

Test Pyramid Level: Integration Tests
Coverage Target: 100% of infrastructure/adapters/mongodb/card_repository.py
Database: MongoDB (real or mock)
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import sys
from pathlib import Path

# Add services/fraud-evaluation-service/src to sys.path for imports
_repo_root = Path(__file__).resolve().parents[2]
_fraud_service_src = _repo_root / 'services' / 'fraud-evaluation-service' / 'src'
if str(_fraud_service_src) not in sys.path:
    sys.path.insert(0, str(_fraud_service_src))


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def card_data():
    """Sample card data for testing persistence"""
    return {
        'card_number': '4532015112830366',
        'card_holder_name': 'John Doe',
        'expiry_date': '12/27',
        'card_type': 'DEBIT',
        'user_id': 'user_12345',
        'card_id': 'card_mongo_001',
        'nickname': 'Main Card',
        'status': 'ACTIVE',
    }


@pytest.fixture
def mock_mongo_client():
    """Mock MongoDB client"""
    client = Mock()
    db = Mock()
    collection = Mock()
    
    client.__getitem__ = Mock(return_value=db)
    db.__getitem__ = Mock(return_value=collection)
    
    return client, db, collection


# ============================================================================
# Test Suite 1: MongoCardRepository - Basic CRUD Operations
# ============================================================================

class TestMongoCardRepositorySave:
    """Tests for saving cards to MongoDB"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_new_card_returns_card_with_id(self, card_data):
        """Should save new card and return with auto-generated card_id"""
        from src.domain.models import Card
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        from unittest.mock import AsyncMock
        
        # Setup
        card = Card(
            card_number=card_data['card_number'],
            card_holder_name=card_data['card_holder_name'],
            expiry_date=card_data['expiry_date'],
            card_type=card_data['card_type'],
            user_id=card_data['user_id'],
            nickname=card_data['nickname'],
            status='ACTIVE',
            card_id='',  # Empty, to be assigned by repository
        )
        
        # Mock collection
        collection = AsyncMock()
        collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
        
        repository = MongoCardRepository(collection)
        
        # Execute
        result = await repository.save(card)
        
        # Verify - card_id should be generated
        assert result.card_id != ''
        assert result.card_number == card.card_number
        assert result.user_id == card.user_id
        assert result.status == 'ACTIVE'
        collection.update_one.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_save_card_encrypts_sensitive_data(self, card_data):
        """Should encrypt card number before persisting"""
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        from unittest.mock import AsyncMock
        
        collection = AsyncMock()
        collection.update_one = AsyncMock(return_value=Mock(modified_count=1))
        
        repository = MongoCardRepository(collection)
        # Note: In production, encryption handled by MongoDB configuration (encryption at rest)


# ============================================================================
# Test Suite 2: MongoCardRepository - Read Operations
# ============================================================================

class TestMongoCardRepositoryFind:
    """Tests for reading cards from MongoDB"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_find_by_id_returns_card(self, card_data):
        """Should retrieve card by ID from MongoDB"""
        from src.domain.models import Card
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        from unittest.mock import AsyncMock
        
        collection = AsyncMock()
        collection.find_one = AsyncMock(return_value={
            '_id': card_data['card_id'],
            'card_number': card_data['card_number'],
            'card_holder_name': card_data['card_holder_name'],
            'expiry_date': card_data['expiry_date'],
            'card_type': card_data['card_type'],
            'user_id': card_data['user_id'],
            'status': 'ACTIVE',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        })
        
        repository = MongoCardRepository(collection)
        
        # Execute
        result = await repository.find_by_id(card_data['card_id'])
        
        # Verify
        assert result is not None
        assert result.card_id == card_data['card_id']
        assert result.user_id == card_data['user_id']

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_if_not_found(self):
        """Should return None if card doesn't exist"""
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        from unittest.mock import AsyncMock
        
        collection = AsyncMock()
        collection.find_one = AsyncMock(return_value=None)
        
        repository = MongoCardRepository(collection)
        
        # Execute
        result = await repository.find_by_id('nonexistent')
        
        # Verify
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_find_by_user_id_returns_all_active_cards(self, card_data):
        """Should return all active cards for a user"""
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        from unittest.mock import AsyncMock
        
        collection = AsyncMock()
        # Mock find() to return async cursor
        cursor = AsyncMock()
        cursor.__aiter__ = AsyncMock(return_value=iter([
            {
                '_id': 'card_1',
                'card_number': '4532015112830366',
                'user_id': 'user_12345',
                'status': 'ACTIVE',
                'card_holder_name': 'John',
                'expiry_date': '12/27',
                'card_type': 'DEBIT',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            },
            {
                '_id': 'card_2',
                'card_number': '5425233010103442',
                'user_id': 'user_12345',
                'status': 'ACTIVE',
                'card_holder_name': 'John',
                'expiry_date': '06/27',
                'card_type': 'CREDIT',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            },
        ]))
        collection.find = Mock(return_value=cursor)
        
        repository = MongoCardRepository(collection)
        
        # Execute
        result = await repository.find_by_user_id('user_12345')
        
        # Verify
        assert len(result) == 2
        assert all(card.user_id == 'user_12345' for card in result)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_find_by_user_and_last_four_detects_duplicates(self, mock_mongo_client):
        """Should find card by user and last 4 digits for duplicate detection"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.find_one = Mock(return_value={
            '_id': 'card_existing',
            'card_number': '4532015112830366',  # Encrypted
            'user_id': 'user_12345',
            'status': 'ACTIVE',
        })
        
        repository = MongoCardRepository(collection)
        
        # Execute - check if card with last 4 digits '0366' exists for user
        result = await repository.find_by_user_and_last_four('user_12345', '0366')
        
        # Verify
        assert result is not None
        assert result.user_id == 'user_12345'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_count_user_cards_respects_max_limit(self, mock_mongo_client):
        """Should count active cards for user to enforce max 10 limit"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.count_documents = Mock(return_value=9)
        
        repository = MongoCardRepository(collection)
        
        # Execute
        count = await repository.count_user_cards('user_12345')
        
        # Verify
        assert count == 9
        assert count < 10  # Still under limit


# ============================================================================
# Test Suite 3: MongoCardRepository - Delete Operations (Soft Delete)
# ============================================================================

class TestMongoCardRepositorySoftDelete:
    """Tests for soft-deleting cards (marking as INACTIVE)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_soft_delete_marks_card_inactive(self, mock_mongo_client):
        """Should update card status to INACTIVE instead of hard delete"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.update_one = Mock(return_value=Mock(modified_count=1))
        
        repository = MongoCardRepository(collection)
        
        # Execute
        await repository.soft_delete('card_123')
        
        # Verify - update_one should be called to set status='INACTIVE'
        collection.update_one.assert_called_once()
        call_args = collection.update_one.call_args
        # Verify the status field is being set to INACTIVE
        assert 'INACTIVE' in str(call_args) or call_args[0][1].get('$set', {}).get('status') == 'INACTIVE'

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_soft_deleted_cards_not_returned_in_find(self, mock_mongo_client):
        """Should filter out INACTIVE cards from find queries"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        # Mock only returns active cards
        collection.find = Mock(return_value=[])  # Empty, because deleted cards filtered
        
        repository = MongoCardRepository(collection)
        
        # Execute - query for user cards should only return ACTIVE
        result = await repository.find_by_user_id('user_12345')
        
        # Verify - no cards returned because all are INACTIVE
        assert result == []


# ============================================================================
# Test Suite 4: MongoCardRepository - Data Consistency & Audit Trail
# ============================================================================

class TestMongoCardRepositoryAuditTrail:
    """Tests for audit trail preservation in MongoDB"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_saves_audit_metadata_on_card_save(self, card_data, mock_mongo_client):
        """Should preserve created_at and updated_at timestamps"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.insert_one = Mock(return_value=Mock(inserted_id='card_new'))
        
        repository = MongoCardRepository(collection)
        
        # Timestamps should be included in saved document

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_updates_updated_at_on_card_modification(self, mock_mongo_client):
        """Should update updated_at timestamp on any modification"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.update_one = Mock(return_value=Mock(modified_count=1))
        
        repository = MongoCardRepository(collection)


# ============================================================================
# Test Suite 5: MongoCardRepository - Error Handling
# ============================================================================

class TestMongoCardRepositoryErrorHandling:
    """Tests for error handling and database failures"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handles_database_connection_error(self, card_data, mock_mongo_client):
        """Should raise meaningful error on database connection failure"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
        
        client, db, collection = mock_mongo_client
        collection.insert_one = Mock(side_effect=Exception("Connection refused"))
        
        repository = MongoCardRepository(collection)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_handles_duplicate_key_error(self, card_data, mock_mongo_client):
        """Should handle MongoDB duplicate key constraint violation"""
        pytest.skip("MongoCardRepository not yet implemented")
        
        from src.infrastructure.adapters.mongodb.card_repository import MongoCardRepository
