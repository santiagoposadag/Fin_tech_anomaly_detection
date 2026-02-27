"""
Phase 4 - RED: API Gateway endpoint tests for Card Management
Following TDD approach: Write tests first, watch them fail

Test Pyramid Level: Integration Tests (API layer)
Framework: FastAPI with Pydantic validation
Coverage Target: 100% of api_gateway/src/routes/cards.py endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime
import json
from unittest.mock import AsyncMock, Mock, patch
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
def valid_add_card_request():
    """Valid request payload for adding a card"""
    return {
        'card_number': '4532015112830366',
        'card_holder_name': 'John Doe',
        'expiry_date': '12/27',
        'card_type': 'DEBIT',
        'nickname': 'Main Card',
    }


@pytest.fixture
def card_response():
    """Sample card response from API"""
    return {
        'card_id': 'card_001',
        'card_number': '****0366',  # Masked
        'card_holder_name': 'John Doe',
        'expiry_date': '12/27',
        'card_type': 'DEBIT',
        'nickname': 'Main Card',
        'status': 'ACTIVE',
        'created_at': datetime.utcnow().isoformat(),
    }


@pytest.fixture
async def client():
    """FastAPI test client"""
    pytest.skip("API Gateway routes not yet implemented")
    # Will import and create client after routes are implemented


# ============================================================================
# Test Suite 1: POST /cards - Add Card Endpoint
# ============================================================================

class TestAddCardEndpoint:
    """Tests for POST /cards endpoint"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_returns_201_created(self, valid_add_card_request):
        """Should accept POST /cards and return 201 Created with card data"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # This test will fail until the endpoint is implemented
        # Expected: POST /cards with valid card data → 201 status + card response with masked number

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_masks_card_number_in_response(self, valid_add_card_request):
        """Should return masked card number (****0366) in response"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # Card number must be masked for security (show only last 4 digits)
        # Request: 4532015112830366 → Response: ****0366

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_validates_card_number_format(self):
        """Should reject invalid card number with 400 Bad Request"""
        pytest.skip("API Gateway routes not yet implemented")
        
        invalid_request = {
            'card_number': '1234',  # Too short
            'card_holder_name': 'John Doe',
            'expiry_date': '12/27',
            'card_type': 'DEBIT',
        }
        # Expected: 400 with validation error details

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_validates_expiry_date_format(self):
        """Should reject invalid expiry date with 400 Bad Request"""
        pytest.skip("API Gateway routes not yet implemented")
        
        invalid_request = {
            'card_number': '4532015112830366',
            'card_holder_name': 'John Doe',
            'expiry_date': '12-25',  # Wrong format
            'card_type': 'DEBIT',
        }
        # Expected: 400 with validation error

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_returns_duplicate_card_error(self):
        """Should return 409 Conflict if card with same last 4 digits exists"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # If AddCardUseCase raises ValueError about duplicate, API should return 409

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_add_card_returns_max_cards_error(self):
        """Should return 400 Bad Request if user has 10 cards already"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # If AddCardUseCase raises ValueError about max limit, return 400


# ============================================================================
# Test Suite 2: GET /cards - List User Cards Endpoint
# ============================================================================

class TestListCardsEndpoint:
    """Tests for GET /cards endpoint"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_cards_returns_200_ok_with_cards_array(self):
        """Should return 200 with list of user's cards"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # GET /cards → 200 with array of card objects
        # Card numbers must be masked in response

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_cards_returns_empty_array_if_no_cards(self):
        """Should return 200 with empty array if user has no cards"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # GET /cards for user with no cards → 200 with []

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_cards_masks_all_card_numbers(self):
        """Should mask card numbers for all cards in response"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # All card_number fields should be masked (****XXXX format)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_cards_requires_authentication(self):
        """Should return 401 Unauthorized if no auth token provided"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # Missing authentication → 401


# ============================================================================
# Test Suite 3: GET /cards/{card_id} - Get Card Details Endpoint
# ============================================================================

class TestGetCardDetailsEndpoint:
    """Tests for GET /cards/{card_id} endpoint"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_card_details_returns_200_ok(self):
        """Should return 200 with card details"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # GET /cards/card_001 → 200 with card object (masked number)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_card_details_returns_404_if_not_found(self):
        """Should return 404 Not Found if card doesn't exist"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # GET /cards/nonexistent → 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_card_details_prevents_unauthorized_access(self):
        """Should return 403 Forbidden if user doesn't own the card"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # User A tries to access User B's card → 403

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_card_details_masks_card_number(self):
        """Should return masked card number in response"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # Card number must be masked (****0366)


# ============================================================================
# Test Suite 4: DELETE /cards/{card_id} - Remove Card Endpoint
# ============================================================================

class TestRemoveCardEndpoint:
    """Tests for DELETE /cards/{card_id} endpoint"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_remove_card_returns_204_no_content(self):
        """Should return 204 No Content on successful deletion"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # DELETE /cards/card_001 → 204 (no body)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_remove_card_returns_404_if_not_found(self):
        """Should return 404 Not Found if card doesn't exist"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # DELETE /cards/nonexistent → 404

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_remove_card_prevents_unauthorized_deletion(self):
        """Should return 403 Forbidden if user doesn't own the card"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # User A tries to delete User B's card → 403

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_remove_card_publishes_audit_event(self):
        """Should publish CARD_REMOVED event to RabbitMQ"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # RemoveCardUseCase should publish event (verified via audit_publisher mock)


# ============================================================================
# Test Suite 5: Error Handling & Validation
# ============================================================================

class TestCardEndpointErrorHandling:
    """Tests for error handling and edge cases"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_json_request_returns_400(self):
        """Should return 400 Bad Request for invalid JSON"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # POST /cards with malformed JSON → 400

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_422(self):
        """Should return 422 Unprocessable Entity for missing fields"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # POST /cards without card_number → 422
        # Pydantic validation should catch this

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_error_returns_500(self):
        """Should return 500 Internal Server Error on database failure"""
        pytest.skip("API Gateway routes not yet implemented")
        
        # If MongoDB connection fails, return 500 with error message
