"""Configuration for the Azure MCP toolkit, read from environment variables.

Every field is optional: a backend is only wired up when its configuration is present, so
you can run a server exposing just blobs, or just Key Vault, by setting only those vars.
"""
from __future__ import annotations

import os

from pydantic import BaseModel

ENV_STORAGE_ACCOUNT_URL = "AZURE_STORAGE_ACCOUNT_URL"
ENV_KEY_VAULT_URL = "AZURE_KEY_VAULT_URL"
ENV_SERVICE_BUS_NAMESPACE = "AZURE_SERVICE_BUS_NAMESPACE"
ENV_SUBSCRIPTION_ID = "AZURE_SUBSCRIPTION_ID"


class ToolkitConfig(BaseModel):
    """Resolved configuration. Unset services are ``None`` and are not registered."""

    storage_account_url: str | None = None
    key_vault_url: str | None = None
    service_bus_namespace: str | None = None
    subscription_id: str | None = None

    @classmethod
    def from_env(cls) -> ToolkitConfig:
        return cls(
            storage_account_url=os.environ.get(ENV_STORAGE_ACCOUNT_URL),
            key_vault_url=os.environ.get(ENV_KEY_VAULT_URL),
            service_bus_namespace=os.environ.get(ENV_SERVICE_BUS_NAMESPACE),
            subscription_id=os.environ.get(ENV_SUBSCRIPTION_ID),
        )

    def enabled_services(self) -> list[str]:
        """Names of the services that are configured."""
        services = []
        if self.storage_account_url:
            services.append("blob")
        if self.key_vault_url:
            services.append("keyvault")
        if self.service_bus_namespace:
            services.append("servicebus")
        if self.subscription_id:
            services.append("resources")
        return services
