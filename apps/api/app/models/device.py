from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    id: str
    brand: str
    appliance_type: str
    model_name: str | None
    display_name: str
    status: str
    created_at: str
    updated_at: str
