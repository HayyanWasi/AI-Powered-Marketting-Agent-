"""Platform & Operations Module

This module provides production observability, telemetry, governance, and
operational monitoring for AI workflows. It is a pure observer — it never
executes workflows, generates AI content, or modifies execution state.

Public interface: PlatformOperationsService
"""

from .interfaces.operations import PlatformOperationsService

__all__ = ["PlatformOperationsService"]
