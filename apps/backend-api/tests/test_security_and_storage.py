from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import get_current_user
from app.services.storage import ObjectStorage


@pytest.mark.asyncio
async def test_development_identity_and_missing_token() -> None:
    settings = Settings(auth_disabled=True, app_env="test")
    user = await get_current_user(None, settings, "00000000-0000-0000-0000-000000000099")
    assert user.id == UUID("00000000-0000-0000-0000-000000000099")
    assert user.role == "admin"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(None, Settings(auth_disabled=False), None)
    assert exc_info.value.status_code == 401


def test_storage_generates_urls_and_forwards_operations() -> None:
    client = Mock()
    client.generate_presigned_url.side_effect = ["https://upload", "https://download"]
    storage = ObjectStorage(client, "documents")

    assert storage.presign_put("owner/file.pdf", "application/pdf", 900) == "https://upload"
    assert storage.presign_get("owner/file.pdf", 300) == "https://download"
    storage.head("owner/file.pdf")
    storage.delete("owner/file.pdf")

    client.head_object.assert_called_once_with(Bucket="documents", Key="owner/file.pdf")
    client.delete_object.assert_called_once_with(Bucket="documents", Key="owner/file.pdf")
