"""Deployment provider registry with an offline-safe v1 default."""
from pathlib import Path

from agency.providers.deploy import DeploymentProvider, LocalStaticDeploymentProvider


def get_deployment_provider(name: str = "local_static") -> DeploymentProvider:
    if name == "local_static":
        return LocalStaticDeploymentProvider(
            dist_root=Path(__file__).resolve().parents[5] / ".artifacts" / "deploys"
        )
    raise NotImplementedError(f"Deployment provider '{name}' is not registered")
