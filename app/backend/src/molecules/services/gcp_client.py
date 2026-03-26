"""GCP client abstraction for workspace provisioning.

Defines a Protocol for GCP operations (Cloud Run + GCS) and dataclasses
for cloud resource info. The production GCPClient class wraps the
google-cloud SDK with asyncio.to_thread for non-blocking calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


@dataclass
class CloudRunServiceInfo:
    """Returned after deploying or querying a Cloud Run service."""

    name: str  # e.g. "ws-a1b2c3d4"
    url: str  # e.g. "https://ws-a1b2c3d4-xyz.a.run.app"
    region: str
    status: str  # "READY", "DEPLOYING", "NOT_FOUND", etc.
    revision: str | None = None


@dataclass
class GCSBucketInfo:
    """Returned after creating or querying a GCS bucket."""

    name: str  # e.g. "stack-bench-ws-a1b2c3d4-e5f6g7h8"
    location: str  # e.g. "northamerica-northeast2"
    exists: bool = True


@dataclass
class ResourceProfileConfig:
    """Cloud Run resource limits per profile."""

    cpu: str  # e.g. "1", "2", "4"
    memory: str  # e.g. "512Mi", "1Gi", "2Gi"
    max_instances: int  # e.g. 1, 2, 4
    timeout_seconds: int = 300

    @classmethod
    def from_profile(cls, profile: str) -> ResourceProfileConfig:
        profiles = {
            "light": cls(cpu="1", memory="512Mi", max_instances=1, timeout_seconds=300),
            "standard": cls(cpu="2", memory="1Gi", max_instances=1, timeout_seconds=600),
            "heavy": cls(cpu="4", memory="2Gi", max_instances=2, timeout_seconds=900),
        }
        if profile not in profiles:
            raise ValueError(f"Unknown resource profile: {profile}. Must be one of: {list(profiles.keys())}")
        return profiles[profile]


class GCPClientProtocol(Protocol):
    """Protocol for GCP operations. Mocked in tests."""

    async def create_gcs_bucket(
        self,
        bucket_name: str,
        region: str,
    ) -> GCSBucketInfo: ...

    async def delete_gcs_bucket(
        self,
        bucket_name: str,
    ) -> None: ...

    async def bucket_exists(
        self,
        bucket_name: str,
    ) -> bool: ...

    async def deploy_cloud_run_service(
        self,
        service_name: str,
        image: str,
        region: str,
        env_vars: dict[str, str],
        resources: ResourceProfileConfig,
        gcs_bucket: str | None = None,
    ) -> CloudRunServiceInfo: ...

    async def delete_cloud_run_service(
        self,
        service_name: str,
        region: str,
    ) -> None: ...

    async def get_cloud_run_service(
        self,
        service_name: str,
        region: str,
    ) -> CloudRunServiceInfo | None: ...

    async def scale_cloud_run_service(
        self,
        service_name: str,
        region: str,
        min_instances: int,
        max_instances: int,
    ) -> None: ...


class GCPClient:
    """Production GCP client using google-cloud SDK.

    Uses async wrappers around the sync SDK via asyncio.to_thread.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    async def create_gcs_bucket(self, bucket_name: str, region: str) -> GCSBucketInfo:
        from google.cloud import storage  # type: ignore[import-not-found]

        def _create() -> GCSBucketInfo:
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(bucket_name)
            bucket.storage_class = "STANDARD"
            client.create_bucket(bucket, location=region)
            return GCSBucketInfo(name=bucket_name, location=region)

        return await asyncio.to_thread(_create)

    async def delete_gcs_bucket(self, bucket_name: str) -> None:
        from google.cloud import storage

        def _delete() -> None:
            client = storage.Client(project=self.project_id)
            bucket = client.bucket(bucket_name)
            bucket.delete(force=True)

        await asyncio.to_thread(_delete)

    async def bucket_exists(self, bucket_name: str) -> bool:
        from google.cloud import storage

        def _exists() -> bool:
            client = storage.Client(project=self.project_id)
            return bool(client.bucket(bucket_name).exists())

        return await asyncio.to_thread(_exists)

    async def deploy_cloud_run_service(
        self,
        service_name: str,
        image: str,
        region: str,
        env_vars: dict[str, str],
        resources: ResourceProfileConfig,
        gcs_bucket: str | None = None,
    ) -> CloudRunServiceInfo:
        """Deploy or update a Cloud Run service.

        Uses the Cloud Run Admin v2 API. Sets container image, env vars,
        CPU/memory from resource profile, GCS volume mount if provided,
        and min_instances=0 for scale-to-zero.
        """
        from google.cloud import run_v2

        def _deploy() -> CloudRunServiceInfo:
            client = run_v2.ServicesClient()
            parent = f"projects/{self.project_id}/locations/{region}"

            container = run_v2.Container(
                image=image,
                env=[run_v2.EnvVar(name=k, value=v) for k, v in env_vars.items()],
                resources=run_v2.ResourceRequirements(
                    limits={"cpu": resources.cpu, "memory": resources.memory},
                ),
            )

            volumes = []
            volume_mounts = []
            if gcs_bucket:
                volumes.append(
                    run_v2.Volume(
                        name="workspace-storage",
                        gcs=run_v2.GcsVolumeSource(bucket=gcs_bucket),
                    )
                )
                volume_mounts.append(
                    run_v2.VolumeMount(name="workspace-storage", mount_path="/workspace/storage")
                )
                container.volume_mounts = volume_mounts

            template = run_v2.RevisionTemplate(
                containers=[container],
                volumes=volumes or None,
                scaling=run_v2.RevisionScaling(
                    min_instance_count=0,
                    max_instance_count=resources.max_instances,
                ),
                timeout=f"{resources.timeout_seconds}s",
            )

            service = run_v2.Service(
                template=template,
            )

            operation = client.create_service(
                parent=parent,
                service=service,
                service_id=service_name,
            )
            result = operation.result()

            return CloudRunServiceInfo(
                name=service_name,
                url=result.uri or "",
                region=region,
                status="READY",
                revision=result.latest_ready_revision,
            )

        return await asyncio.to_thread(_deploy)

    async def delete_cloud_run_service(self, service_name: str, region: str) -> None:
        from google.cloud import run_v2

        def _delete() -> None:
            client = run_v2.ServicesClient()
            name = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            operation = client.delete_service(name=name)
            operation.result()

        await asyncio.to_thread(_delete)

    async def get_cloud_run_service(self, service_name: str, region: str) -> CloudRunServiceInfo | None:
        from google.cloud import run_v2

        def _get() -> CloudRunServiceInfo | None:
            client = run_v2.ServicesClient()
            name = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            try:
                service = client.get_service(name=name)
                return CloudRunServiceInfo(
                    name=service_name,
                    url=service.uri or "",
                    region=region,
                    status="READY" if service.latest_ready_revision else "DEPLOYING",
                    revision=service.latest_ready_revision,
                )
            except Exception:
                return None

        return await asyncio.to_thread(_get)

    async def scale_cloud_run_service(
        self,
        service_name: str,
        region: str,
        min_instances: int,
        max_instances: int,
    ) -> None:
        """Update scaling config. min=0, max=0 effectively stops the service."""
        from google.cloud import run_v2

        def _scale() -> None:
            client = run_v2.ServicesClient()
            name = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            service = client.get_service(name=name)
            service.template.scaling.min_instance_count = min_instances
            service.template.scaling.max_instance_count = max_instances
            operation = client.update_service(service=service)
            operation.result()

        await asyncio.to_thread(_scale)
