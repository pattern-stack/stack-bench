"""Tests for GCP client dataclasses and protocol."""

from __future__ import annotations

import pytest

from molecules.services.gcp_client import (
    CloudRunServiceInfo,
    GCSBucketInfo,
    ResourceProfileConfig,
)


# ---------------------------------------------------------------------------
# ResourceProfileConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resource_profile_light() -> None:
    """Light profile: 1 CPU, 512Mi, 1 max instance."""
    config = ResourceProfileConfig.from_profile("light")
    assert config.cpu == "1"
    assert config.memory == "512Mi"
    assert config.max_instances == 1
    assert config.timeout_seconds == 300


@pytest.mark.unit
def test_resource_profile_standard() -> None:
    """Standard profile: 2 CPU, 1Gi, 1 max instance."""
    config = ResourceProfileConfig.from_profile("standard")
    assert config.cpu == "2"
    assert config.memory == "1Gi"
    assert config.max_instances == 1
    assert config.timeout_seconds == 600


@pytest.mark.unit
def test_resource_profile_heavy() -> None:
    """Heavy profile: 4 CPU, 2Gi, 2 max instances."""
    config = ResourceProfileConfig.from_profile("heavy")
    assert config.cpu == "4"
    assert config.memory == "2Gi"
    assert config.max_instances == 2
    assert config.timeout_seconds == 900


@pytest.mark.unit
def test_resource_profile_invalid() -> None:
    """Unknown profile raises ValueError."""
    with pytest.raises(ValueError, match="Unknown resource profile"):
        ResourceProfileConfig.from_profile("turbo")


# ---------------------------------------------------------------------------
# CloudRunServiceInfo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_cloud_run_service_info_fields() -> None:
    """Verify dataclass fields and defaults."""
    info = CloudRunServiceInfo(
        name="ws-a1b2c3d4",
        url="https://ws-a1b2c3d4-xyz.a.run.app",
        region="northamerica-northeast2",
        status="READY",
    )
    assert info.name == "ws-a1b2c3d4"
    assert info.url == "https://ws-a1b2c3d4-xyz.a.run.app"
    assert info.region == "northamerica-northeast2"
    assert info.status == "READY"
    assert info.revision is None


@pytest.mark.unit
def test_cloud_run_service_info_with_revision() -> None:
    """Verify revision field is set correctly."""
    info = CloudRunServiceInfo(
        name="ws-test",
        url="https://ws-test.run.app",
        region="us-central1",
        status="READY",
        revision="ws-test-00001-abc",
    )
    assert info.revision == "ws-test-00001-abc"


# ---------------------------------------------------------------------------
# GCSBucketInfo
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_gcs_bucket_info_fields() -> None:
    """Verify dataclass fields and defaults."""
    info = GCSBucketInfo(
        name="stack-bench-ws-a1b2c3d4-e5f6g7h8",
        location="northamerica-northeast2",
    )
    assert info.name == "stack-bench-ws-a1b2c3d4-e5f6g7h8"
    assert info.location == "northamerica-northeast2"
    assert info.exists is True


@pytest.mark.unit
def test_gcs_bucket_info_not_exists() -> None:
    """Verify exists=False."""
    info = GCSBucketInfo(
        name="missing-bucket",
        location="us-central1",
        exists=False,
    )
    assert info.exists is False
