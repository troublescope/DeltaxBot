import base64
import uuid


def format_number(number: float) -> str:
    formatted_number = f"{number:,.0f}".replace(",", ".")

    if number.is_integer():
        return formatted_number
    else:
        return f"{number:,.2f}".replace(",", ".").rstrip("0").rstrip(".")


def shorten_id(original_id: str) -> str:
    uuid_bytes = uuid.UUID(original_id).bytes
    return base64.urlsafe_b64encode(uuid_bytes).rstrip(b"=").decode("utf-8")


def expand_id(short_id: str) -> str:
    id_bytes = base64.urlsafe_b64decode(short_id + "==")
    return str(uuid.UUID(bytes=id_bytes))
