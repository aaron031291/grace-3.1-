"""Tests for historical data store."""

import pytest
import tempfile
import shutil
from datetime import datetime

from business_intelligence.historical.data_store import HistoricalDataStore
from business_intelligence.models.data_models import (
    IntelligenceSnapshot, MarketDataPoint, PainPoint, CampaignResult,
)


class TestHistoricalDataStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = HistoricalDataStore(storage_dir=self.tmpdir, retention_days=365)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_save_and_load_snapshot(self):
        snapshot = IntelligenceSnapshot(
            data_points_collected=42,
            active_niches=["ai tools"],
            phase="collect",
            summary="Test snapshot",
        )
        path = await self.store.save_snapshot(snapshot)
        assert path != ""

        loaded = await self.store.load_snapshots(days_back=1)
        assert len(loaded) == 1
        assert loaded[0]["data_points_collected"] == 42

    @pytest.mark.asyncio
    async def test_save_market_data(self):
        data = [
            MarketDataPoint(metric_name="test", metric_value=100.0),
            MarketDataPoint(metric_name="test2", metric_value=200.0),
        ]
        count = await self.store.save_market_data(data, niche="test_niche")
        assert count == 2

        loaded = await self.store.load_market_data(niche="test_niche")
        assert len(loaded) == 2

    @pytest.mark.asyncio
    async def test_save_pain_points(self):
        points = [PainPoint(description=f"problem {i}") for i in range(5)]
        count = await self.store.save_pain_points(points, niche="test")
        assert count == 5

        loaded = await self.store.load_pain_point_history(niche="test")
        assert len(loaded) == 5

    @pytest.mark.asyncio
    async def test_save_campaign_results(self):
        results = [CampaignResult(campaign_name="test", ad_spend=50.0)]
        count = await self.store.save_campaign_results(results)
        assert count == 1

    @pytest.mark.asyncio
    async def test_timeline_empty(self):
        timeline = await self.store.get_timeline(days_back=30)
        assert timeline["total_snapshots"] == 0

    @pytest.mark.asyncio
    async def test_timeline_with_data(self):
        import time
        for i in range(3):
            snap = IntelligenceSnapshot(
                data_points_collected=i * 10,
                phase="collect",
                timestamp=datetime.utcnow(),
            )
            snap.timestamp = datetime(2026, 2, 21, 10, 0, i)
            await self.store.save_snapshot(snap)
        timeline = await self.store.get_timeline(days_back=1)
        assert timeline["total_snapshots"] == 3

    @pytest.mark.asyncio
    async def test_cleanup(self):
        result = await self.store.cleanup_old_data()
        assert isinstance(result, dict)


class TestSecretsVault:
    def test_vault_without_passphrase(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase=None, vault_path="/tmp/test_vault.enc")
        assert not vault._initialized

    def test_vault_with_passphrase(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase="test_pass_123", vault_path="/tmp/test_vault2.enc")
        assert vault._initialized

    def test_store_and_retrieve(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase="test_pass", vault_path="/tmp/test_vault3.enc")
        vault.store("TEST_KEY", "secret_value_123")
        retrieved = vault.retrieve("TEST_KEY")
        assert retrieved == "secret_value_123"

    def test_retrieve_nonexistent(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase="test", vault_path="/tmp/test_vault4.enc")
        assert vault.retrieve("MISSING") is None

    def test_delete(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase="test", vault_path="/tmp/test_vault5.enc")
        vault.store("DEL_KEY", "value")
        assert vault.delete("DEL_KEY")
        assert vault.retrieve("DEL_KEY") is None

    def test_list_keys(self):
        from business_intelligence.utils.secrets_vault import SecretsVault
        vault = SecretsVault(passphrase="test", vault_path="/tmp/test_vault6.enc")
        vault.store("KEY1", "val1")
        vault.store("KEY2", "val2")
        keys = vault.list_keys()
        assert len(keys) == 2
        key_names = [k["key"] for k in keys]
        assert "KEY1" in key_names
        assert "KEY2" in key_names
