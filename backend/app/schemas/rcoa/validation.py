NUMERIC_CODE_PATTERN = r"^\d+$"
CUSTOMER_NAME_PATTERN = r"^[A-Za-z]+$"


def is_ascii_letters(value: str) -> bool:
    return bool(value) and value.isascii() and value.isalpha()
