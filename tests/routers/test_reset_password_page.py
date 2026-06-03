"""Tests for the GET /reset-password HTML page (the target of the emailed link)."""

import pytest


@pytest.mark.asyncio
async def test_reset_password_page_served(async_client):
    """The page is served at the root path the reset link points to, returns HTML,
    and contains the form that posts to the reset API."""
    response = await async_client.get("/reset-password")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "Set a new password" in body
    assert "/api/v1/auth/reset-password" in body
