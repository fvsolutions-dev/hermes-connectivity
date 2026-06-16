"""Round-trip tests for BurstLinkEncoder / BurstLinkNode."""

import time

from burst_link_protocol import BurstInterfaceC
from hermes_framing_nodes import BurstLinkEncoder, BurstLinkNode
from node_hermes_core.datatypes import BinaryDataPacket
from node_hermes_core.generic_node.port import CallbackPort, DirectPort


def _frame(payload: bytes) -> bytes:
    """Encode a single payload as a BURST frame using a fresh interface."""
    return BurstInterfaceC().encode([payload])


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
    frame = _frame(b"split-me")
    chunk_a, chunk_b = frame[: len(frame) // 2], frame[len(frame) // 2 :]
    decoded = await _drive_decoder([chunk_a, chunk_b])
    assert decoded == [b"split-me"]


async def test_decoder_drops_crc_failures_and_keeps_decoding():
    """A frame with a corrupt payload is dropped, but later frames still decode.

    Flipping a byte after the COBS overhead breaks the CRC; `BurstInterfaceC`
    silently skips the bad frame (with `fail_on_crc_error=False`) and keeps
    decoding from the next 0x00 terminator.
    """
    good = _frame(b"good-one")
    bad = _frame(b"bad-one")
    # Flip a payload byte (the second-to-last byte before the CRC + terminator).
    bad_corrupt = bad[:-3] + bytes([bad[-3] ^ 0x42]) + bad[-2:]
    after_bad = _frame(b"after-bad")

    decoded = await _drive_decoder([good + bad_corrupt + after_bad])
    assert decoded == [b"good-one", b"after-bad"]
