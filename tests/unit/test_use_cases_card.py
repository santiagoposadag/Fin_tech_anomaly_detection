"""
Phase 2 - RED: Failing tests for Card use cases (application layer)
Following TDD approach: Write tests first, watch them fail

Test Pyramid Level: Unit Tests + Mocked Repositories
Coverage Target: 100% of application/use_cases/card_*.py
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock
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
def valid_card_data():
    """Standard valid card data for creating cards"""
    return {
        'card_number': '4532015112830366',
        'card_holder_name': 'John Doe',
        'expiry_date': '12/27',
        'card_type': 'DEBIT',
        'user_id': 'user_12345',
        'nickname': 'Main Card',
    }


@pytest.fixture
def mock_card_repository():
    """Mock CardRepository for testing use cases"""
    from src.domain.models import Card
    
    repo = Mock()
    
    # For save: accept a Card input and return it with a card_id assigned
    async def mock_save(card):
        # Return the card with a card_id assigned
        return Card(
            card_number=card.card_number,
            card_holder_name=card.card_holder_name,
            expiry_date=card.expiry_date,
            card_type=card.card_type,
            user_id=card.user_id,
            nickname=card.nickname,
            status=card.status,
            card_id='card_' + datetime.now().strftime('%f'),  # Unique ID
            created_at=card.created_at,
            updated_at=card.updated_at,
        )
    
    repo.save = AsyncMock(side_effect=mock_save)
    repo.find_by_id = AsyncMock(return_value=None)
    repo.find_by_user_id = AsyncMock(return_value=[])
    repo.find_by_user_and_last_four = AsyncMock(return_value=None)
    repo.count_user_cards = AsyncMock(return_value=0)
    repo.soft_delete = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def mock_audit_publisher():
    """Mock AuditEventPublisher for testing use cases"""
    publisher = Mock()
    publisher.publish_event = AsyncMock(return_value=None)
    return publisher


# ============================================================================
# Test Suite 1: AddCardUseCase (Create new card)
# ============================================================================

class TestAddCardUseCase:
    """Tests for AddCardUseCase - Adding new card to user account"""

    @pytest.mark.asyncio
    async def test_add_card_happy_path(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should successfully add a new card when all validation passes"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        from src.domain.models import Card
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute
        # This will fail until AddCardUseCase is implemented
        result = await use_case.execute(valid_card_data)
        
        # Verify
        assert isinstance(result, Card)
        assert result.card_number == valid_card_data['card_number']
        assert result.user_id == valid_card_data['user_id']
        assert result.status == 'ACTIVE'
        
        # Verify repository was called to save
        mock_card_repository.save.assert_called_once()
        
        # Verify audit event was published
        mock_audit_publisher.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_card_duplicate_prevention(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should reject card if same last 4 digits already exist for user"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        # Mock that card with same last 4 digits exists
        mock_card_repository.find_by_user_and_last_four.return_value = Mock()  # Card exists
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Card with last 4 digits .* already linked"):
            await use_case.execute(valid_card_data)
        
        # Card should not be saved
        mock_card_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_card_max_cards_limit_exceeded(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should reject if user already has 10 cards (max limit)"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        # Mock that user has 10 cards
        mock_card_repository.count_user_cards.return_value = 10
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Maximum of 10 cards"):
            await use_case.execute(valid_card_data)
        
        # Card should not be saved
        mock_card_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_card_validates_card_number(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should reject invalid card number format"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Invalid card number (too short)
        invalid_data = {**valid_card_data, 'card_number': '1234'}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Card number must be exactly 16 digits"):
            await use_case.execute(invalid_data)

    @pytest.mark.asyncio
    async def test_add_card_validates_expiry_date(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should reject invalid expiry date format"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Invalid expiry format
        invalid_data = {**valid_card_data, 'expiry_date': '12-25'}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Expiry date must be in MM/YY format"):
            await use_case.execute(invalid_data)

    @pytest.mark.asyncio
    async def test_add_card_validates_cardholder_name(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should reject invalid card holder name"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Too short name
        invalid_data = {**valid_card_data, 'card_holder_name': 'Jo'}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Card holder name must be 3-50 characters"):
            await use_case.execute(invalid_data)

    @pytest.mark.asyncio
    async def test_add_card_publishes_audit_event(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should publish audit event when card is added"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        
        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute
        result = await use_case.execute(valid_card_data)
        
        # Verify audit event was published with correct info
        call_args = mock_audit_publisher.publish_event.call_args
        assert call_args is not None
        # Event should contain card_id, user_id, action='CARD_ADDED'
        event = call_args[0][0]  # First positional argument
        assert 'card_id' in event
        assert event.get('user_id') == valid_card_data['user_id']
        assert event.get('action') == 'CARD_ADDED'

    @pytest.mark.asyncio
    async def test_add_card_handles_duplicate_key_error_from_repository(
        self, valid_card_data, mock_card_repository, mock_audit_publisher
    ):
        """Should propagate ValueError when the repository detects a concurrent duplicate insert"""
        from src.application.card_use_cases.add_card import AddCardUseCase

        # Simulate: duplicate pre-check passes (race condition), but the repository
        # re-raises MongoDB's DuplicateKeyError as ValueError (infrastructure-level handling).
        mock_card_repository.find_by_user_and_last_four = AsyncMock(return_value=None)
        mock_card_repository.count_user_cards = AsyncMock(return_value=0)
        mock_card_repository.save = AsyncMock(
            side_effect=ValueError(
                "Card with last 4 digits 0366 already linked to your account"
            )
        )

        use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)

        with pytest.raises(ValueError, match="already linked to your account"):
            await use_case.execute(valid_card_data)


# ============================================================================
# Test Suite 2: RemoveCardUseCase (Soft delete card)
# ============================================================================

class TestRemoveCardUseCase:
    """Tests for RemoveCardUseCase - Remove/soft-delete card"""

    @pytest.mark.asyncio
    async def test_remove_card_happy_path(self, mock_card_repository, mock_audit_publisher):
        """Should successfully soft-delete a card"""
        from src.application.card_use_cases.remove_card import RemoveCardUseCase
        from src.domain.models import Card
        
        # Mock existing card
        existing_card = Card(
            card_number='4532015112830366',
            card_holder_name='John Doe',
            expiry_date='12/27',
            card_type='DEBIT',
            user_id='user_12345',
            card_id='card_123',
            status='ACTIVE'
        )
        mock_card_repository.find_by_id.return_value = existing_card
        
        use_case = RemoveCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute
        await use_case.execute(user_id='user_12345', card_id='card_123')
        
        # Verify
        mock_card_repository.soft_delete.assert_called_once_with('card_123')
        mock_audit_publisher.publish_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_card_not_found(self, mock_card_repository, mock_audit_publisher):
        """Should raise error if card doesn't exist"""
        from src.application.card_use_cases.remove_card import RemoveCardUseCase
        
        # Mock card not found
        mock_card_repository.find_by_id.return_value = None
        
        use_case = RemoveCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Card not found"):
            await use_case.execute(user_id='user_12345', card_id='nonexistent')

    @pytest.mark.asyncio
    async def test_remove_card_unauthorized_access(self, mock_card_repository, mock_audit_publisher):
        """Should reject if user_id doesn't match card owner"""
        from src.application.card_use_cases.remove_card import RemoveCardUseCase
        from src.domain.models import Card
        
        # Mock card owned by different user
        existing_card = Card(
            card_number='4532015112830366',
            card_holder_name='John Doe',
            expiry_date='12/27',
            card_type='DEBIT',
            user_id='other_user',  # Different owner
            card_id='card_123',
        )
        mock_card_repository.find_by_id.return_value = existing_card
        
        use_case = RemoveCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Unauthorized"):
            await use_case.execute(user_id='user_12345', card_id='card_123')
        
        # Should not delete
        mock_card_repository.soft_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_card_publishes_audit_event(self, mock_card_repository, mock_audit_publisher):
        """Should publish audit event when card is removed"""
        from src.application.card_use_cases.remove_card import RemoveCardUseCase
        from src.domain.models import Card
        
        existing_card = Card(
            card_number='4532015112830366',
            card_holder_name='John Doe',
            expiry_date='12/27',
            card_type='DEBIT',
            user_id='user_12345',
            card_id='card_123',
        )
        mock_card_repository.find_by_id.return_value = existing_card
        
        use_case = RemoveCardUseCase(mock_card_repository, mock_audit_publisher)
        
        # Execute
        await use_case.execute(user_id='user_12345', card_id='card_123')
        
        # Verify audit event includes card info
        call_args = mock_audit_publisher.publish_event.call_args
        event = call_args[0][0]
        assert event.get('action') == 'CARD_REMOVED'
        assert event.get('card_id') == 'card_123'


# ============================================================================
# Test Suite 3: ListUserCardsUseCase
# ============================================================================

class TestListUserCardsUseCase:
    """Tests for ListUserCardsUseCase - Get all cards for user"""

    @pytest.mark.asyncio
    async def test_list_user_cards_happy_path(self, mock_card_repository):
        """Should return all active cards for user"""
        from src.application.card_use_cases.list_user_cards import ListUserCardsUseCase
        from src.domain.models import Card
        
        # Mock cards
        cards = [
            Card(
                card_number='4532015112830366',
                card_holder_name='John Doe',
                expiry_date='12/27',
                card_type='DEBIT',
                user_id='user_12345',
                card_id='card_1',
                status='ACTIVE'
            ),
            Card(
                card_number='5425233010103442',
                card_holder_name='John Doe',
                expiry_date='06/27',
                card_type='CREDIT',
                user_id='user_12345',
                card_id='card_2',
                status='ACTIVE'
            ),
        ]
        mock_card_repository.find_by_user_id.return_value = cards
        
        use_case = ListUserCardsUseCase(mock_card_repository)
        
        # Execute
        result = await use_case.execute(user_id='user_12345')
        
        # Verify
        assert len(result) == 2
        assert result[0].card_id == 'card_1'
        assert result[1].card_id == 'card_2'

    @pytest.mark.asyncio
    async def test_list_user_cards_empty_list(self, mock_card_repository):
        """Should return empty list if user has no cards"""
        from src.application.card_use_cases.list_user_cards import ListUserCardsUseCase
        
        mock_card_repository.find_by_user_id.return_value = []
        
        use_case = ListUserCardsUseCase(mock_card_repository)
        
        # Execute
        result = await use_case.execute(user_id='user_no_cards')
        
        # Verify
        assert result == []

    @pytest.mark.asyncio
    async def test_list_user_cards_masks_card_numbers(self, mock_card_repository):
        """Should mask card numbers in response for security"""
        from src.application.card_use_cases.list_user_cards import ListUserCardsUseCase
        from src.domain.models import Card
        
        cards = [
            Card(
                card_number='4532015112830366',
                card_holder_name='John Doe',
                expiry_date='12/27',
                card_type='DEBIT',
                user_id='user_12345',
                card_id='card_1',
            ),
        ]
        mock_card_repository.find_by_user_id.return_value = cards
        
        use_case = ListUserCardsUseCase(mock_card_repository)
        
        # Execute
        result = await use_case.execute(user_id='user_12345')
        
        # Verify card number is masked in response
        # The use case should return masked card numbers
        assert result[0].mask_card_number() == '****0366'


# ============================================================================
# Test Suite 4: GetCardDetailsUseCase
# ============================================================================

class TestGetCardDetailsUseCase:
    """Tests for GetCardDetailsUseCase - Get single card details"""

    @pytest.mark.asyncio
    async def test_get_card_details_happy_path(self, mock_card_repository):
        """Should return card details for authorized user"""
        from src.application.card_use_cases.get_card_details import GetCardDetailsUseCase
        from src.domain.models import Card
        
        card = Card(
            card_number='4532015112830366',
            card_holder_name='John Doe',
            expiry_date='12/27',
            card_type='DEBIT',
            user_id='user_12345',
            card_id='card_123',
        )
        mock_card_repository.find_by_id.return_value = card
        
        use_case = GetCardDetailsUseCase(mock_card_repository)
        
        # Execute
        result = await use_case.execute(user_id='user_12345', card_id='card_123')
        
        # Verify
        assert result.card_id == 'card_123'
        assert result.user_id == 'user_12345'

    @pytest.mark.asyncio
    async def test_get_card_details_card_not_found(self, mock_card_repository):
        """Should raise error if card doesn't exist"""
        from src.application.card_use_cases.get_card_details import GetCardDetailsUseCase
        
        mock_card_repository.find_by_id.return_value = None
        
        use_case = GetCardDetailsUseCase(mock_card_repository)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Card not found"):
            await use_case.execute(user_id='user_12345', card_id='nonexistent')

    @pytest.mark.asyncio
    async def test_get_card_details_unauthorized_access(self, mock_card_repository):
        """Should reject if user_id doesn't match card owner"""
        from src.application.card_use_cases.get_card_details import GetCardDetailsUseCase
        from src.domain.models import Card
        
        card = Card(
            card_number='4532015112830366',
            card_holder_name='John Doe',
            expiry_date='12/27',
            card_type='DEBIT',
            user_id='other_user',  # Different owner
            card_id='card_123',
        )
        mock_card_repository.find_by_id.return_value = card
        
        use_case = GetCardDetailsUseCase(mock_card_repository)
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Unauthorized"):
            await use_case.execute(user_id='user_12345', card_id='card_123')


# ============================================================================
# Integration Tests - Use Cases Together
# ============================================================================

class TestCardUseCasesIntegration:
    """Integration tests for multiple use cases working together"""

    @pytest.mark.asyncio
    async def test_add_then_list_cards(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should be able to add a card and then list it"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        from src.application.card_use_cases.list_user_cards import ListUserCardsUseCase
        from src.domain.models import Card
        
        # Setup: Add card
        add_use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        result = await add_use_case.execute(valid_card_data)
        
        # Setup: Mock repository to return the added card
        mock_card_repository.find_by_user_id.return_value = [result]
        
        # Execute: List cards
        list_use_case = ListUserCardsUseCase(mock_card_repository)
        cards = await list_use_case.execute(user_id='user_12345')
        
        # Verify
        assert len(cards) == 1
        assert cards[0].card_number == valid_card_data['card_number']

    @pytest.mark.asyncio
    async def test_add_then_remove_card(self, valid_card_data, mock_card_repository, mock_audit_publisher):
        """Should be able to add a card and then remove it"""
        from src.application.card_use_cases.add_card import AddCardUseCase
        from src.application.card_use_cases.remove_card import RemoveCardUseCase
        
        # Setup: Add card
        add_use_case = AddCardUseCase(mock_card_repository, mock_audit_publisher)
        result = await add_use_case.execute(valid_card_data)
        card_id = result.card_id
        
        # Setup: Mock repository to return the added card
        mock_card_repository.find_by_id.return_value = result
        
        # Execute: Remove card
        remove_use_case = RemoveCardUseCase(mock_card_repository, mock_audit_publisher)
        await remove_use_case.execute(user_id='user_12345', card_id=card_id)
        
        # Verify soft_delete was called
        mock_card_repository.soft_delete.assert_called_once()
