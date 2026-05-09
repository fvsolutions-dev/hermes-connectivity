"""Hermes nodes for byte-stream framing protocols."""

from .burst_link import BurstLinkEncoder, BurstLinkNode

NODES = [BurstLinkNode, BurstLinkEncoder]

__all__ = ["BurstLinkNode", "BurstLinkEncoder", "NODES"]
