"""Frame serializer for audio frames sent to/by Altur."""

import base64
import json

from pydantic import BaseModel

from pipecat.audio.utils import create_default_resampler, pcm_to_ulaw, ulaw_to_pcm
from pipecat.frames.frames import (
    AudioRawFrame,
    Frame,
    InputAudioRawFrame,
    InputDTMFFrame,
    KeypadEntry,
    StartInterruptionFrame,
    TransportMessageFrame,
    TransportMessageUrgentFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType


class AlturFrameSerializer(FrameSerializer):
    """Frame serializer for audio frames sent to/by Altur."""

    class InputParams(BaseModel):
        """Parameters for the AlturFrameSerializer."""

        altur_sample_rate: int = 8000
        sample_rate: int = 16000

    def __init__(self, call_id: str, params: InputParams = InputParams()):
        """Initialize the AlturFrameSerializer."""
        self._call_id = call_id
        self._params = params

        self._resampler = create_default_resampler()

    @property
    def type(self) -> FrameSerializerType:
        """Return the type of the AlturFrameSerializer."""
        return FrameSerializerType.TEXT

    async def serialize(self, frame: Frame) -> str | bytes | None:
        """Serialize a frame to a string."""
        if isinstance(frame, StartInterruptionFrame):
            # TODO: Implement this
            pass
        if isinstance(frame, AudioRawFrame):
            data = frame.audio

            serialized_data = await pcm_to_ulaw(
                data, frame.sample_rate, self._params.altur_sample_rate, self._resampler
            )
            payload = base64.b64encode(serialized_data).decode("utf-8")
            response = {
                "call_id": self._call_id,
                "payload": payload,
            }

            return json.dumps(response)
        elif isinstance(frame, (TransportMessageFrame, TransportMessageUrgentFrame)):
            return json.dumps(frame.message)

    async def deserialize(self, data: str | bytes) -> Frame | None:
        """Deserialize a string to a frame."""
        payload = json.loads(data)

        if payload["call_id"] != self._call_id:
            return None

        payload = base64.b64decode(payload["payload"])
        deserialized_data = await ulaw_to_pcm(
            payload, self._params.altur_sample_rate, self._params.sample_rate, self._resampler
        )
        audio_frame = InputAudioRawFrame(
            audio=deserialized_data, num_channels=1, sample_rate=self._params.sample_rate
        )

        return audio_frame
