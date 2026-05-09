"""Hermes nodes for byte-stream framing protocols."""

from .burst_link import BurstLinkEncoder, BurstLinkNode, decode_packet, encode_packet

NODES = [BurstLinkNode, BurstLinkEncoder]

__all__ = [
    "BurstLinkNode",
    "BurstLinkEncoder",
    "encode_packet",
    "decode_packet",
    "NODES",
]
