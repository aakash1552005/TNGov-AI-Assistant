"""Automated integration tests for admin endpoints: /admin/stats, /admin/version, /admin/dataset, /admin/feedback."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
class TestAdminEndpoints:
    """Verify diagnostic and audit endpoints."""

    async def test_get_admin_stats(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/stats")
        assert res.status_code == 200
        data = res.json()
        assert "total_chunks" in data
        assert "bm25_indexed_chunks" in data
        assert data["status"] == "healthy"

    async def test_get_admin_version(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/version")
        assert res.status_code == 200
        data = res.json()
        assert "git_commit" in data
        assert "app_version" in data
        assert "llm_provider" in data

    async def test_get_admin_dataset(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/dataset")
        assert res.status_code == 200
        data = res.json()
        assert "total_chunks" in data
        assert "documents" in data
        assert isinstance(data["documents"], list)

    async def test_get_admin_feedback(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.get("/admin/feedback")
        assert res.status_code == 200
        data = res.json()
        assert "total_feedback" in data
        assert "up_count" in data
        assert "down_count" in data
        assert "latest_feedback" in data
