"""
Phase 1 - RED: Failing tests for Card domain models and validators
Following TDD approach: Write tests first, watch them fail

Test Pyramid Level: Unit Tests (Pure domain logic, no framework dependencies)
Coverage Target: 100% of domain/models/card.py and domain/validation/card_validators.py
"""
import pytest
from dataclasses import FrozenInstanceError
import sys
from pathlib import Path

# Add services/fraud-evaluation-service/src to sys.path for imports
_repo_root = Path(__file__).resolve().parents[2]
_fraud_service_src = _repo_root / 'services' / 'fraud-evaluation-service' / 'src'
if str(_fraud_service_src) not in sys.path:
    sys.path.insert(0, str(_fraud_service_src))


# ============================================================================
# Test Fixtures for reusable data
# ============================================================================

@pytest.fixture
def valid_card_data():
    """Standard valid card data for happy path tests"""
    return {
        'card_number': '4532015112830366',  # Valid 16-digit card
        'card_holder_name': 'John Doe',
        'expiry_date': '12/27',  # MM/YY format
        'card_type': 'DEBIT',
        'nickname': 'Main Debit Card',
        'user_id': 'user_12345',
    }


@pytest.fixture
def minimal_card_data():
    """Minimal valid card data (nickname optional)"""
    return {
        'card_number': '5425233010103442',
        'card_holder_name': 'Jane Smith',
        'expiry_date': '06/27',
        'card_type': 'CREDIT',
        'user_id': 'user_67890',
    }


# ============================================================================
# Test Suite 1: Card Entity Model (Frozen Dataclass)
# Tests: TASK-001 - Ensure immutability and basic entity properties
# ============================================================================

class TestCardEntity:
    """Test suite for Card entity (frozen dataclass with immutability)"""

    def test_card_entity_creation_with_all_fields(self, valid_card_data):
        """Should create Card entity with all fields when valid data provided"""
        # This test will fail until Card class is defined in domain/models/card.py
        from src.domain.models import Card
        
        card = Card(**valid_card_data)
        
        assert card.card_number == '4532015112830366'
        assert card.card_holder_name == 'John Doe'
        assert card.expiry_date == '12/27'
        assert card.card_type == 'DEBIT'
        assert card.nickname == 'Main Debit Card'
        assert card.user_id == 'user_12345'
        assert card.status == 'ACTIVE'  # Should default to ACTIVE

    def test_card_entity_creation_without_optional_nickname(self, minimal_card_data):
        """Should create Card entity without nickname field (optional)"""
        from src.domain.models import Card
        
        card = Card(**minimal_card_data)
        
        assert card.card_number == '5425233010103442'
        assert card.card_holder_name == 'Jane Smith'
        assert card.nickname is None  # Optional, should be None if not provided

    def test_card_entity_is_frozen_immutable(self, valid_card_data):
        """Should prevent modification of Card fields (frozen dataclass)"""
        from src.domain.models import Card
        
        card = Card(**valid_card_data)
        
        # Attempting to modify a frozen dataclass should raise FrozenInstanceError
        with pytest.raises(FrozenInstanceError):
            card.card_number = '1234567890123456'

    def test_card_entity_has_timestamps(self, valid_card_data):
        """Should automatically create created_at and updated_at timestamps"""
        from src.domain.models import Card
        from datetime import datetime, timedelta
        
        before = datetime.utcnow()
        card = Card(**valid_card_data)
        after = datetime.utcnow()
        
        assert hasattr(card, 'created_at')
        assert hasattr(card, 'updated_at')
        assert before <= card.created_at <= after
        assert before <= card.updated_at <= after
        # Timestamps should be very close (within 100ms of each other)
        # Both are created during Card instantiation so they're nearly identical
        assert abs((card.updated_at - card.created_at).total_seconds()) < 0.1


# ============================================================================
# Test Suite 2: Card Validator - Card Number (16 digits)
# Tests: TASK-002 - Validate card number format
# ============================================================================

class TestCardNumberValidator:
    """Test suite for card number validation (16 digits, numeric only)"""

    def test_validate_card_number_16_digits_valid(self):
        """Should accept card number with exactly 16 digits"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        # Should not raise exception
        result = validate_card_number('4532015112830366')
        assert result is True

    def test_validate_card_number_rejects_less_than_16_digits(self):
        """Should reject card number with less than 16 digits"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        with pytest.raises(ValueError, match="Card number must be exactly 16 digits"):
            validate_card_number('1234')

    def test_validate_card_number_rejects_more_than_16_digits(self):
        """Should reject card number with more than 16 digits"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        with pytest.raises(ValueError, match="Card number must be exactly 16 digits"):
            validate_card_number('12345678901234567')

    def test_validate_card_number_rejects_non_numeric(self):
        """Should reject card number with non-numeric characters"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        with pytest.raises(ValueError, match="Card number must contain only digits"):
            validate_card_number('453201511283036a')

    def test_validate_card_number_rejects_empty_string(self):
        """Should reject empty string"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        with pytest.raises(ValueError):
            validate_card_number('')

    def test_validate_card_number_rejects_spaces(self):
        """Should reject card number with spaces (even though formatted)"""
        from src.domain.validation.card_validators import (
            validate_card_number
        )
        
        with pytest.raises(ValueError):
            validate_card_number('4532 0151 1283 0366')


# ============================================================================
# Test Suite 3: Card Validator - Expiry Date (MM/YY format)
# Tests: TASK-003 - Validate expiry date format
# ============================================================================

class TestExpiryDateValidator:
    """Test suite for expiry date validation (MM/YY format)"""

    def test_validate_expiry_date_valid_format(self):
        """Should accept expiry date in MM/YY format"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )
        
        result = validate_expiry_date('12/27')
        assert result is True

    def test_validate_expiry_date_valid_month_range(self):
        """Should accept all valid months (01-12)"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )

        for month in ['01', '06', '12']:
            result = validate_expiry_date(f'{month}/27')
            assert result is True

    def test_validate_expiry_date_rejects_invalid_month_00(self):
        """Should reject month 00"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )
        
        with pytest.raises(ValueError, match="Month must be between 01 and 12"):
            validate_expiry_date('00/25')

    def test_validate_expiry_date_rejects_invalid_month_13(self):
        """Should reject month 13"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )
        
        with pytest.raises(ValueError, match="Month must be between 01 and 12"):
            validate_expiry_date('13/25')

    def test_validate_expiry_date_rejects_wrong_format(self):
        """Should reject dates not in MM/YY format"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )
        
        with pytest.raises(ValueError, match="Expiry date must be in MM/YY format"):
            validate_expiry_date('12-25')

    def test_validate_expiry_date_rejects_single_digit_month(self):
        """Should reject single digit month (needs leading zero)"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )
        
        with pytest.raises(ValueError):
            validate_expiry_date('1/25')

    def test_validate_expiry_date_rejects_two_digit_year(self):
        """Should accept 2-digit year (YY format)"""
        from src.domain.validation.card_validators import (
            validate_expiry_date
        )

        result = validate_expiry_date('06/27')
        assert result is True

    def test_validate_expiry_date_rejects_past_year(self):
        """Should reject a card expired in a previous year"""
        from src.domain.validation.card_validators import validate_expiry_date

        with pytest.raises(ValueError, match="expired"):
            validate_expiry_date('01/20')  # January 2020 — always in the past

    def test_validate_expiry_date_rejects_past_month_current_year(self):
        """Should reject a card whose expiry month has already passed this year"""
        from src.domain.validation.card_validators import validate_expiry_date
        from datetime import date

        today = date.today()
        # Build a date one month before today
        if today.month == 1:
            past_month = 12
            past_year = (today.year - 1) % 100
        else:
            past_month = today.month - 1
            past_year = today.year % 100
        expiry = f"{past_month:02d}/{past_year:02d}"

        with pytest.raises(ValueError, match="expired"):
            validate_expiry_date(expiry)

    def test_validate_expiry_date_accepts_current_month(self):
        """Should accept a card expiring in the current month"""
        from src.domain.validation.card_validators import validate_expiry_date
        from datetime import date

        today = date.today()
        expiry = f"{today.month:02d}/{today.year % 100:02d}"
        result = validate_expiry_date(expiry)
        assert result is True

    def test_validate_expiry_date_accepts_future_date(self):
        """Should accept a card expiring well in the future"""
        from src.domain.validation.card_validators import validate_expiry_date

        result = validate_expiry_date('12/99')  # December 2099 — always in the future
        assert result is True


# ============================================================================
# Test Suite 4: Card Validator - Card Holder Name
# Tests: TASK-004 - Validate card holder name (3-50 chars, alphanumeric + spaces)
# ============================================================================

class TestCardHolderNameValidator:
    """Test suite for card holder name validation"""

    def test_validate_card_holder_name_valid(self):
        """Should accept valid card holder name"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        result = validate_card_holder_name('John Doe')
        assert result is True

    def test_validate_card_holder_name_minimum_length_3(self):
        """Should accept name with exactly 3 characters"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        result = validate_card_holder_name('Joe')
        assert result is True

    def test_validate_card_holder_name_maximum_length_50(self):
        """Should accept name with exactly 50 characters"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        result = validate_card_holder_name('A' * 50)
        assert result is True

    def test_validate_card_holder_name_rejects_too_short(self):
        """Should reject name with less than 3 characters"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        with pytest.raises(ValueError, match="Card holder name must be 3-50 characters"):
            validate_card_holder_name('Jo')

    def test_validate_card_holder_name_rejects_too_long(self):
        """Should reject name with more than 50 characters"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        with pytest.raises(ValueError, match="Card holder name must be 3-50 characters"):
            validate_card_holder_name('A' * 51)

    def test_validate_card_holder_name_accepts_spaces(self):
        """Should accept spaces in card holder name"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        result = validate_card_holder_name('John Michael Doe')
        assert result is True

    def test_validate_card_holder_name_rejects_special_characters(self):
        """Should reject special characters (except spaces)"""
        from src.domain.validation.card_validators import (
            validate_card_holder_name
        )
        
        with pytest.raises(ValueError):
            validate_card_holder_name('John@Doe')


# ============================================================================
# Test Suite 5: Card Type Enum
# Tests: TASK-005 - Validate CardType enum (DEBIT/CREDIT)
# ============================================================================

class TestCardTypeEnum:
    """Test suite for CardType enum"""

    def test_card_type_debit_exists(self):
        """Should have DEBIT card type"""
        from src.domain.models import CardType
        
        assert CardType.DEBIT.value == 'DEBIT'

    def test_card_type_credit_exists(self):
        """Should have CREDIT card type"""
        from src.domain.models import CardType
        
        assert CardType.CREDIT.value == 'CREDIT'

    def test_card_type_enum_string_representation(self):
        """Should convert to string properly"""
        from src.domain.models import CardType
        
        assert str(CardType.DEBIT) == 'CardType.DEBIT'


# ============================================================================
# Test Suite 6: Card Status Enum
# Tests: TASK-005 - Validate CardStatus enum (ACTIVE/INACTIVE)
# ============================================================================

class TestCardStatusEnum:
    """Test suite for CardStatus enum"""

    def test_card_status_active_exists(self):
        """Should have ACTIVE status"""
        from src.domain.models import CardStatus
        
        assert CardStatus.ACTIVE.value == 'ACTIVE'

    def test_card_status_inactive_exists(self):
        """Should have INACTIVE status"""
        from src.domain.models import CardStatus
        
        assert CardStatus.INACTIVE.value == 'INACTIVE'


# ============================================================================
# Test Suite 7: Card Nickname Validation (Optional field)
# ============================================================================

class TestCardNicknameValidator:
    """Test suite for optional card nickname validation"""

    def test_validate_card_nickname_valid(self):
        """Should accept valid nickname (max 20 chars)"""
        from src.domain.validation.card_validators import (
            validate_card_nickname
        )
        
        result = validate_card_nickname('My Main Card')
        assert result is True

    def test_validate_card_nickname_none_is_valid(self):
        """Should accept None for nickname (optional)"""
        from src.domain.validation.card_validators import (
            validate_card_nickname
        )
        
        result = validate_card_nickname(None)
        assert result is True

    def test_validate_card_nickname_max_length_20(self):
        """Should accept nickname with exactly 20 characters"""
        from src.domain.validation.card_validators import (
            validate_card_nickname
        )
        
        result = validate_card_nickname('A' * 20)
        assert result is True

    def test_validate_card_nickname_rejects_exceeds_20_chars(self):
        """Should reject nickname exceeding 20 characters"""
        from src.domain.validation.card_validators import (
            validate_card_nickname
        )
        
        with pytest.raises(ValueError, match="Card nickname must not exceed 20 characters"):
            validate_card_nickname('A' * 21)


# ============================================================================
# Test Suite 8: Last 4 Digits Extraction (For duplicate detection)
# ============================================================================

class TestLastFourDigitsExtraction:
    """Test suite for extracting last 4 digits from card number"""

    def test_extract_last_four_digits(self):
        """Should extract last 4 digits from card number"""
        from src.domain.validation.card_validators import (
            get_last_four_digits
        )
        
        result = get_last_four_digits('4532015112830366')
        assert result == '0366'

    def test_extract_last_four_digits_different_cards(self):
        """Should correctly extract from different cards"""
        from src.domain.validation.card_validators import (
            get_last_four_digits
        )
        
        result = get_last_four_digits('5425233010103442')
        assert result == '3442'


# ============================================================================
# Test Suite 9: Mask Card Number For Display
# ============================================================================

class TestMaskCardNumber:
    """Test suite for masking card number (security - show only last 4 digits)"""

    def test_mask_card_number_shows_only_last_four(self):
        """Should show only last 4 digits and mask the rest"""
        from src.domain.validation.card_validators import (
            mask_card_number
        )
        
        result = mask_card_number('4532015112830366')
        assert result == '****0366'

    def test_mask_card_number_consistent(self):
        """Should mask consistently"""
        from src.domain.validation.card_validators import (
            mask_card_number
        )
        
        result = mask_card_number('5425233010103442')
        assert result == '****3442'
