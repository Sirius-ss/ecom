from datetime import UTC, datetime
from uuid import uuid4


def get_uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def get_utcnow() -> datetime:
    return datetime.now(UTC)


def normalized_resource_id(resource_id: str) -> str:
    """去除前后空格，转大写，-转_"""
    return resource_id.strip().upper().replace('-', '_')
