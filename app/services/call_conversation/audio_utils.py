"""
Audio format conversion utilities for Twilio ↔ ElevenLabs bridging.

Twilio uses:    mulaw (G.711) 8kHz mono
ElevenLabs uses: PCM 16-bit 16kHz mono
"""

import base64
import struct

# Use audioop-lts which is a drop-in replacement for the removed audioop module in Python 3.13+
try:
    import audioop
except ImportError:
    import audioop_lts as audioop  # type: ignore[no-redef]


def mulaw_to_pcm16k(mulaw_bytes: bytes) -> bytes:
    """Convert 8kHz mulaw audio to 16kHz 16-bit linear PCM.

    Steps:
      1. Decode mulaw → 16-bit linear PCM at 8kHz
      2. Upsample 8kHz → 16kHz
    """
    # mulaw → linear PCM 16-bit at 8kHz
    pcm_8k = audioop.ulaw2lin(mulaw_bytes, 2)

    # Upsample 8kHz → 16kHz
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)

    return pcm_16k


def pcm16k_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16kHz 16-bit linear PCM to 8kHz mulaw.

    Steps:
      1. Downsample 16kHz → 8kHz
      2. Encode linear PCM → mulaw
    """
    # Downsample 16kHz → 8kHz
    pcm_8k, _ = audioop.ratecv(pcm_bytes, 2, 1, 16000, 8000, None)

    # Linear PCM → mulaw
    mulaw = audioop.lin2ulaw(pcm_8k, 2)

    return mulaw


def twilio_media_to_pcm(payload: str) -> bytes:
    """Decode Twilio base64 media payload to PCM 16kHz bytes."""
    mulaw_bytes = base64.b64decode(payload)
    return mulaw_to_pcm16k(mulaw_bytes)


def pcm_to_twilio_media(pcm_bytes: bytes) -> str:
    """Convert PCM 16kHz bytes to Twilio base64 media payload."""
    mulaw_bytes = pcm16k_to_mulaw(pcm_bytes)
    return base64.b64encode(mulaw_bytes).decode("ascii")


def chunk_audio(audio_bytes: bytes, chunk_size: int = 160) -> list[bytes]:
    """Split audio bytes into fixed-size chunks for streaming.

    Twilio expects 160-byte frames (20ms of 8kHz mulaw audio).
    Pads the last chunk with silence (0xFF for mulaw) if needed.
    """
    chunks = []
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]
        if len(chunk) < chunk_size:
            # Pad with mulaw silence (0xFF)
            chunk = chunk + b'\xff' * (chunk_size - len(chunk))
        chunks.append(chunk)
    return chunks
