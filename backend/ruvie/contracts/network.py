"""Strict, reusable admin networking draft; no ambient proxy or implicit direct."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from ruvie.adapters.network import normalize_proxy_url, InvalidNetworkConfiguration

class NetworkConfig(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=False)
    mode: Literal['direct', 'proxy']
    proxy_url: str | None  # Required even for direct: must be explicit null.

    @model_validator(mode='after')
    def check_endpoint(self):
        if self.mode == 'direct':
            if self.proxy_url is not None:
                raise ValueError('invalid_network_configuration')
        elif self.proxy_url is None:
            raise ValueError('invalid_network_configuration')
        else:
            try:
                self.proxy_url = normalize_proxy_url(self.proxy_url)
            except InvalidNetworkConfiguration:
                raise ValueError('invalid_network_configuration') from None
        return self
