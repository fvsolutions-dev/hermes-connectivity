"""Round-trip tests for BurstLinkEncoder / BurstLinkNode."""

import time

from hermes_framing_nodes import BurstLinkEncoder, BurstLinkNode, encode_packet
from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.port import CallbackPort, DirectPort


async def _drive_decoder(payload_chunks: list[bytes]) -> list[bytes]:
    """Feed bytes into a fresh BurstLinkNode and return the payloads it emits."""
    decoder = BurstLinkNode(BurstLinkNode.Config(source=DirectPort.Config()))
    received: list[bytes] = []
    decoder.base_link.add_target(
        CallbackPort(
            config=CallbackPort.Config(),
            callback=lambda p: received.append(p.data),
        )
    )
    await decoder.attempt_init()
    try:
        for chunk in payload_chunks:
            decoder.handle_data(BinaryDataPacket(source="t", timestamp=time.time(), data=chunk))
    finally:
        await decoder.recursive_deinit()
    return received


async def test_encoder_then_decoder_round_trip():
    """Three payloads: encode each, concatenate the frames, decode in one pass."""
    encoder = BurstLinkEncoder(BurstLinkEncoder.Config(source=DirectPort.Config()))
    encoded: list[bytes] = []
    encoder.base_link.add_target(
        CallbackPort(config=CallbackPort.Config(), callback=lambda p: encoded.append(p.data))
    )
    await encoder.attempt_init()
    try:
        for payload in [b"alpha", b"beta", b"gamma"]:
            encoder.handle_data(BinaryDataPacket(source="t", timestamp=time.time(), data=payload))
    finally:
        await encoder.recursive_deinit()

    assert len(encoded) == 3
    decoded = await _drive_decoder([b"".join(encoded)])
    assert decoded == [b"alpha", b"beta", b"gamma"]


async def test_decoder_buffers_partial_frame():
    """Splitting a single frame across two chunks must not lose the payload."""
    frame = encode_packet(b"split-me")
    chunk_a, chunk_b = frame[: len(frame) // 2], frame[len(frame) // 2 :]
    decoded = await _drive_decoder([chunk_a, chunk_b])
    assert decoded == [b"split-me"]


async def test_decoder_drops_crc_failures_and_keeps_decoding():
    """A frame with a corrupt CRC is dropped, but later frames still decode."""
    good = encode_packet(b"good-one")

    # Build a frame, flip one byte of payload; the trailing CRC will no longer match.
    bad = encode_packet(b"bad-one")
    bad_corrupt = bytes([bad[0] ^ 0x42]) + bad[1:]

    after_bad = encode_packet(b"after-bad")

    decoded = await _drive_decoder([good + bad_corrupt + after_bad])
    assert decoded == [b"good-one", b"after-bad"]
