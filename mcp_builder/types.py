"""Shared Pydantic models (P2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RunnerModel(BaseModel):
    type: Literal["stdio", "sse"]
    command: list[str] | None = None
    url: str | None = None
    env: dict = Field(default_factory=dict)
    limits: dict = Field(default_factory=dict)
    security: dict = Field(default_factory=dict)


class TransportModel(BaseModel):
    type: Literal["stdio", "sse"]
    url: str | None = None
    health: str | None = None


class McpManifestModel(BaseModel):
    schemaVersion: str | int
    name: str
    version: str
    transports: list[TransportModel]
    tools: list[str | dict] = Field(default_factory=list)
    limits: dict = Field(default_factory=dict)
    security: dict = Field(default_factory=dict)
    build: dict = Field(default_factory=dict)
    digest: dict | None = None


class ArtifactSpec(BaseModel):
    kind: Literal["zip", "git", "pypi", "oci", "npm"]
    spec: dict


class PlanModel(BaseModel):
    id: str
    artifacts: list[ArtifactSpec]
    mcp_registration: dict | None = None
