"""
Card Validators - Pure functions for card data validation
Clean Architecture: Domain layer, NO framework dependencies

Validation Functions:
- validate_card_number(): 16-digit format check
- validate_expiry_date(): MM/YY format check
- validate_card_holder_name(): 3-50 chars, alphanumeric + spaces
- validate_card_nickname(): Optional, max 20 chars
- get_last_four_digits(): Extract last 4 digits
- mask_card_number(): Mask for display (security)

All functions follow fail-fast pattern: raise ValueError on invalid input

Design Principles:
- Single Responsibility: Each function validates one aspect
- Immutability: No side effects, pure functions
- Fail-Fast: Raise exceptions immediately on invalid input
- Explicitness: Clear error messages for debugging
- Composability: Functions can be combined (e.g., validate all fields before creating Card)

Post-MVP Enhancements:
- Luhn algorithm validation (credit card checksum)
- Card issuer detection (Visa, Mastercard, etc.)
- BIN (Bank Identification Number) validation
- Speed of transaction checks (velocity limits)
"""
import re
from datetime import date
from typing import Optional


# ============================================================================
# Card Number Validation
# ============================================================================

def validate_card_number(card_number: str) -> bool:
    """
    Validate card number format for MVP (basic checks only)
    
    MVP Rules (Security: Format validation only):
    - Exactly 16 digits
    - Numeric only (no spaces, hyphens, or special characters)
    - Not an empty string
    
    Post-MVP Enhancements:
    - Luhn algorithm (prevent typos/checksums)
    - Card brand detection (Visa: starts with 4, Mastercard: 51-55, etc.)
    - BIN validation against known card issuers
    
    Args:
        card_number: String to validate
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If validation fails with descriptive message
        
    Examples:
        >>> validate_card_number('4532015112830366')
        True
        >>> validate_card_number('1234')
        ValueError: Card number must be exactly 16 digits
        >>> validate_card_number('453201511283036a')
        ValueError: Card number must contain only digits
    """
    if not card_number:
        raise ValueError("Card number cannot be empty")

    if not card_number.isdigit():
        raise ValueError("Card number must contain only digits")

    if len(card_number) != 16:
        raise ValueError("Card number must be exactly 16 digits")

    return True


# ============================================================================
# Expiry Date Validation
# ============================================================================

def validate_expiry_date(expiry_date: str) -> bool:
    """
    Validate expiry date format for MVP (format only)
    
    MVP Rules (No future date validation in MVP):
    - MM/YY format (e.g., "12/25" for December 2025)
    - Month: 01-12 (leading zero required)
    - Year: 00-99 (2-digit year, year 00 = year 2000)
    - No validation that expiry is in future (handled in business logic)
    
    Post-MVP Enhancements:
    - Validate expiry is in the future (card not expired)
    - Handle leap years for billing dates
    - Time zone handling for monthly billing cycles
    
    Args:
        expiry_date: String in MM/YY format
        
    Returns:
        True if valid format
        
    Raises:
        ValueError: If format invalid or range invalid
        
    Examples:
        >>> validate_expiry_date('12/25')
        True
        >>> validate_expiry_date('01/26')
        True
        >>> validate_expiry_date('12-25')
        ValueError: Expiry date must be in MM/YY format
        >>> validate_expiry_date('13/25')
        ValueError: Month must be between 01 and 12
    """
    # Check format: MM/YY (exactly 5 characters: 2 digits, slash, 2 digits)
    if not re.match(r'^\d{2}/\d{2}$', expiry_date):
        raise ValueError("Expiry date must be in MM/YY format")

    month, year = expiry_date.split('/')
    month_int = int(month)
    year_int = int(year)

    # Validate month range (01-12)
    if not (1 <= month_int <= 12):
        raise ValueError("Month must be between 01 and 12")

    # Validate card has not expired
    today = date.today()
    current_year = today.year % 100  # 2-digit year
    current_month = today.month
    if year_int < current_year or (year_int == current_year and month_int < current_month):
        raise ValueError("Card has expired")

    return True


# ============================================================================
# Card Holder Name Validation
# ============================================================================

def validate_card_holder_name(name: str) -> bool:
    """
    Validate card holder name (as printed on card)
    
    Rules:
    - Required field (cannot be None or empty)
    - 3-50 characters (typically cards show 3-4 word names)
    - Alphanumeric characters and spaces only
    - No special characters (@, #, !, etc.)
    - No leading/trailing spaces (trimmed before validation in practice)
    
    Rationale:
    - Min 3 chars: Prevents single/double letter names (too short, likely typos)
    - Max 50 chars: Card name field is limited, matches most cards' physical capacity
    - Alphanumeric only: Card printing machines typically support limited characters
    
    Args:
        name: Card holder name as it appears on the card
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If validation fails with descriptive message
        
    Examples:
        >>> validate_card_holder_name('John Doe')
        True
        >>> validate_card_holder_name('Mary Jane Smith')
        True
        >>> validate_card_holder_name('Jo')
        ValueError: Card holder name must be 3-50 characters
        >>> validate_card_holder_name('John@Doe')
        ValueError: Card holder name can only contain letters, numbers, and spaces
    """
    if not name:
        raise ValueError("Card holder name is required")

    if not (3 <= len(name) <= 50):
        raise ValueError("Card holder name must be 3-50 characters")

    # Allow only letters, numbers, and spaces (no special characters)
    if not re.match(r'^[a-zA-Z0-9\s]+$', name):
        raise ValueError("Card holder name can only contain letters, numbers, and spaces")

    return True


# ============================================================================
# Card Nickname Validation (Optional)
# ============================================================================

def validate_card_nickname(nickname: Optional[str]) -> bool:
    """
    Validate card nickname (optional, user-friendly label)
    
    Rules:
    - Optional (None is valid - user can skip providing a nickname)
    - Max 20 characters if provided
    - No format restrictions (can contain special characters, emojis, etc.)
    
    Rationale:
    - Max 20 chars: Suitable for small display areas in UI (cards list, dropdown)
    - No content restrictions: User-facing text, can be any language/characters
    
    Args:
        nickname: Optional nickname for the card (e.g., "My Main Card")
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If exceeds max length
        
    Examples:
        >>> validate_card_nickname('My Main Card')
        True
        >>> validate_card_nickname(None)
        True
        >>> validate_card_nickname('Travel Card 🌍')
        True
        >>> validate_card_nickname('A' * 21)
        ValueError: Card nickname must not exceed 20 characters
    """
    if nickname is None:
        return True

    if len(nickname) > 20:
        raise ValueError("Card nickname must not exceed 20 characters")

    return True


# ============================================================================
# Utility Functions - Last 4 Digits & Masking
# ============================================================================

def get_last_four_digits(card_number: str) -> str:
    """
    Extract last 4 digits from card number
    
    Used for:
    1. Display in UI (security: only show last 4 digits to user)
    2. Duplicate detection (last 4 + user_id combo must be unique)
    3. Transaction history (user identification reference)
    
    Security Implication:
    - Last 4 digits are considered "low risk" to display (widely used industry practice)
    - First 12 digits NEVER displayed (contain card brand and bank routing info)
    
    Args:
        card_number: Full 16-digit card number
        
    Returns:
        Last 4 digits as string (e.g., "0366")
        
    Examples:
        >>> get_last_four_digits('4532015112830366')
        '0366'
        >>> get_last_four_digits('5425233010103442')
        '3442'
    """
    return card_number[-4:]


def mask_card_number(card_number: str) -> str:
    """
    Mask card number for display (security - hide most digits)
    
    Format: ****XXXX where XXXX is last 4 digits
    Example: "4532015112830366" -> "****0366"
    
    Use Cases:
    - Audit trail logging (don't log full card numbers)
    - Email/SMS notifications ("Your transaction with card ****0366 was approved")
    - Transaction history UI display
    - Error messages and logs
    
    Security:
    - Complies with PCI DSS requirement: "Do not display more than first 6 and last 4 digits"
    - Prevents accidental exposure of full card numbers in logs/emails
    - Industry standard format (easy for users to recognize which card)
    
    Args:
        card_number: Full 16-digit card number
        
    Returns:
        Masked card number in ****XXXX format (always 8 characters)
        
    Examples:
        >>> mask_card_number('4532015112830366')
        '****0366'
        >>> mask_card_number('5425233010103442')
        '****3442'
    """
    last_four = get_last_four_digits(card_number)
    return f"****{last_four}"

