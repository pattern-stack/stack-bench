"""Local GCP client for development without cloud dependencies.

Implements GCPClientProtocol using local filesystem for storage
and a subprocess for the workspace server. No GCP SDK required.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import signal
import socket
from pathlib import Path

from .gcp_client import (
    CloudRunServiceInfo,
    GCSBucketInfo,
    ResourceProfileConfig,
)

logger = logging.getLogger(__name__)

# Default local workspace root
LOCAL_WORKSPACE_ROOT = Path(os.environ.get("LOCAL_WORKSPACE_ROOT", "/tmp/stack-bench-workspaces"))

# Track running workspace server processes: service_name -> (process, port)
_running_servers: dict[str, tuple[asyncio.subprocess.Process, int]] = {}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


class LocalGCPClient:
    """Development GCP client that uses local filesystem + subprocesses.

    - GCS buckets → local directories under LOCAL_WORKSPACE_ROOT
    - Cloud Run services → workspace-server subprocesses on random ports
    """

    def __init__(self, project_id: str = "local") -> None:
        self.project_id = project_id
        LOCAL_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    async def create_gcs_bucket(self, bucket_name: str, region: str) -> GCSBucketInfo:
        bucket_path = LOCAL_WORKSPACE_ROOT / bucket_name
        bucket_path.mkdir(parents=True, exist_ok=True)
        logger.info("Local bucket created: %s", bucket_path)
        return GCSBucketInfo(name=bucket_name, location=region)

    async def delete_gcs_bucket(self, bucket_name: str) -> None:
        bucket_path = LOCAL_WORKSPACE_ROOT / bucket_name
        if bucket_path.exists():
            shutil.rmtree(bucket_path)
            logger.info("Local bucket deleted: %s", bucket_path)

    async def bucket_exists(self, bucket_name: str) -> bool:
        return (LOCAL_WORKSPACE_ROOT / bucket_name).is_dir()

    async def deploy_cloud_run_service(
        self,
        service_name: str,
        image: str,
        region: str,
        env_vars: dict[str, str],
        resources: ResourceProfileConfig,
        gcs_bucket: str | None = None,
    ) -> CloudRunServiceInfo:
        """Start a local workspace-server process instead of deploying to Cloud Run."""
        # Stop existing server if any
        if service_name in _running_servers:
            await self.delete_cloud_run_service(service_name, region)

        port = _find_free_port()

        # Set up workspace directory
        workspace_dir = LOCAL_WORKSPACE_ROOT / (gcs_bucket or service_name)
        workspace_dir.mkdir(parents=True, exist_ok=True)

        # Clone repo if REPO_URL is set and workspace is empty
        repo_url = env_vars.get("REPO_URL")
        main_dir = workspace_dir / "main"
        if repo_url and not main_dir.exists():
            logger.info("Cloning %s into %s", repo_url, main_dir)
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                repo_url,
                str(main_dir),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.warning("Clone failed: %s", stderr.decode())

        # Try to start workspace server
        server_url = f"http://localhost:{port}"
        try:
            server_env = {**os.environ, **env_vars, "PORT": str(port), "WORKSPACE_ROOT": str(workspace_dir)}
            # Try running the workspace server from infrastructure/
            server_script = Path(__file__).parents[3] / "infrastructure" / "workspace" / "server" / "main.py"
            if server_script.exists():
                process = await asyncio.create_subprocess_exec(
                    "python",
                    str(server_script),
                    env=server_env,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                _running_servers[service_name] = (process, port)
                # Give it a moment to start
                await asyncio.sleep(0.5)
                logger.info("Local workspace server started: %s on port %d", service_name, port)
            else:
                logger.info("No workspace server found at %s — URL will be set but server won't respond", server_script)
        except Exception as exc:
            logger.warning("Failed to start workspace server: %s", exc)

        return CloudRunServiceInfo(
            name=service_name,
            url=server_url,
            region="local",
            status="READY",
            revision="local-dev",
        )

    async def delete_cloud_run_service(self, service_name: str, region: str) -> None:
        if service_name in _running_servers:
            process, port = _running_servers.pop(service_name)
            try:
                process.send_signal(signal.SIGTERM)
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except (ProcessLookupError, TimeoutError):
                process.kill()
            logger.info("Local workspace server stopped: %s (port %d)", service_name, port)

    async def get_cloud_run_service(self, service_name: str, region: str) -> CloudRunServiceInfo | None:
        if service_name in _running_servers:
            _, port = _running_servers[service_name]
            return CloudRunServiceInfo(
                name=service_name,
                url=f"http://localhost:{port}",
                region="local",
                status="READY",
                revision="local-dev",
            )
        return None

    async def scale_cloud_run_service(
        self,
        service_name: str,
        region: str,
        min_instances: int,
        max_instances: int,
    ) -> None:
        if max_instances == 0 and service_name in _running_servers:
            await self.delete_cloud_run_service(service_name, region)
        logger.info("Local scale: %s min=%d max=%d", service_name, min_instances, max_instances)
