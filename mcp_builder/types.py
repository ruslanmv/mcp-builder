"""Shared Pydantic models (P2)."""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class RunnerModel(BaseModel):
    type: Literal["stdio", "sse"]
    command: Optional[List[str]] = None
    url: Optional[str] = None
    env: dict = Field(default_factory=dict)
    limits: dict = Field(default_factory=dict)
    security: dict = Field(default_factory=dict)


class TransportModel(BaseModel):
    type: Literal["stdio", "sse"]
    url: Optional[str] = None
    health: Optional[str] = None


class McpManifestModel(BaseModel):
    schemaVersion: str | int
    name: str
    version: str
    transports: List[TransportModel]
    tools: List[str | dict] = Field(default_factory=list)
    limits: dict = Field(default_factory=dict)
    security: dict = Field(default_factory=dict)
    build: dict = Field(default_factory=dict)
    digest: Optional[dict] = None


class ArtifactSpec(BaseModel):
    kind: Literal["zip", "git", "pypi", "oci", "npm"]
    spec: dict


class PlanModel(BaseModel):
    id: str
    artifacts: List[ArtifactSpec]
    mcp_registration: Optional[dict] = None
