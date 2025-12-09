# Copyright 2023 Actualize, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import io
import os
import weakref
from dataclasses import dataclass
from typing import Any

import aiohttp
import av

from livekit import rtc
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIError,
    APIStatusError,
    APITimeoutError,
    tts,
    utils,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, NotGivenOr
from livekit.agents.utils import is_given

from .log import logger
from .models import TTSModels

# Faseeh uses 24kHz PCM16 for streaming
SAMPLE_RATE = 24000

DEFAULT_VOICE_ID = "ar-hijazi-female-2"
API_BASE_URL = "https://api.faseeh.ai/api/v1"
API_KEY_HEADER = "x-api-key"


@dataclass
class VoiceSettings:
    stability: float  # [0.0 - 1.0]


@dataclass
class Voice:
    id: str
    name: str
    language: str


class TTS(tts.TTS):
    def __init__(
        self,
        *,
        voice_id: str = DEFAULT_VOICE_ID,
        model: TTSModels | str = "faseeh-v1-preview",
        stability: float = 1,
        api_key: NotGivenOr[str] = NOT_GIVEN,
        base_url: NotGivenOr[str] = NOT_GIVEN,
        http_session: aiohttp.ClientSession | None = None,
    ) -> None:
        """
        Create a new instance of Faseeh TTS.

        Args:
            voice_id (str): Voice ID. Defaults to `DEFAULT_VOICE_ID`.
            model (TTSModels | str): TTS model to use. Defaults to "faseeh-v1-preview".
            stability (float): Voice stability (0.0 to 1.0). Higher values produce more consistent output. Defaults to 1.
            api_key (NotGivenOr[str]): Faseeh API key. Can be set via argument or `FASEEH_API_KEY` environment variable.
            base_url (NotGivenOr[str]): Custom base URL for the API. Optional.
            http_session (aiohttp.ClientSession | None): Custom HTTP session for API requests. Optional.
        """
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=True,
            ),
            sample_rate=SAMPLE_RATE,
            num_channels=1,
        )

        faseeh_api_key = api_key if is_given(api_key) else os.environ.get("FASEEH_API_KEY")
        if not faseeh_api_key:
            raise ValueError(
                "Faseeh API key is required, either as argument or set FASEEH_API_KEY environmental variable"
            )

        if not 0.0 <= stability <= 1.0:
            raise ValueError("stability must be between 0.0 and 1.0")

        self._opts = _TTSOptions(
            voice_id=voice_id,
            model=model,
            stability=stability,
            api_key=faseeh_api_key,
            base_url=base_url if is_given(base_url) else API_BASE_URL,
        )
        self._session = http_session
        self._streams = weakref.WeakSet[SynthesizeStream]()

    @property
    def model(self) -> str:
        return self._opts.model

    @property
    def provider(self) -> str:
        return "Faseeh"

    def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session:
            self._session = utils.http_context.http_session()
        return self._session

    def update_options(
        self,
        *,
        voice_id: NotGivenOr[str] = NOT_GIVEN,
        model: NotGivenOr[TTSModels | str] = NOT_GIVEN,
        stability: NotGivenOr[float] = NOT_GIVEN,
    ) -> None:
        """
        Update TTS options.

        Args:
            voice_id (NotGivenOr[str]): Voice ID.
            model (NotGivenOr[TTSModels | str]): TTS model to use.
            stability (NotGivenOr[float]): Voice stability (0.0 to 1.0).
        """
        if is_given(voice_id):
            self._opts.voice_id = voice_id

        if is_given(model):
            self._opts.model = model

        if is_given(stability):
            if not 0.0 <= stability <= 1.0:
                raise ValueError("stability must be between 0.0 and 1.0")
            self._opts.stability = stability

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> ChunkedStream:
        return ChunkedStream(tts=self, input_text=text, conn_options=conn_options)

    def stream(
        self, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> SynthesizeStream:
        stream = SynthesizeStream(tts=self, conn_options=conn_options)
        self._streams.add(stream)
        return stream

    async def aclose(self) -> None:
        for stream in list(self._streams):
            await stream.aclose()
        self._streams.clear()

        if self._session:
            await self._session.close()


class ChunkedStream(tts.ChunkedStream):
    """Synthesize using the non-streaming API endpoint (returns WAV file)"""

    def __init__(self, *, tts: TTS, input_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts: TTS = tts
        self._opts = tts._opts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        url = f"{self._opts.base_url}/text-to-speech/{self._opts.model}"
        headers = {
            API_KEY_HEADER: self._opts.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "voice_id": self._opts.voice_id,
            "text": self._input_text,
            "stability": self._opts.stability,
            "streaming": False,
        }

        try:
            async with self._tts._ensure_session().post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(
                    total=30,
                    sock_connect=self._conn_options.timeout,
                ),
            ) as resp:
                if resp.status == 400:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Bad request: {error_data.get('errorMessage', 'Unknown error')}"
                    )
                elif resp.status == 401:
                    raise APIStatusError(
                        message="Unauthorized - invalid API key",
                        status_code=401,
                        request_id=None,
                        body=None,
                    )
                elif resp.status == 402:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Payment required: {error_data.get('errorMessage', 'Insufficient balance')}"
                    )
                elif resp.status == 403:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Forbidden: {error_data.get('errorMessage', 'Access denied')}"
                    )
                elif resp.status == 404:
                    raise APIStatusError(
                        message="Model or voice not found",
                        status_code=404,
                        request_id=None,
                        body=None,
                    )
                elif resp.status == 429:
                    raise APIStatusError(
                        message="Rate limit exceeded",
                        status_code=429,
                        request_id=None,
                        body=None,
                    )

                resp.raise_for_status()

                if not resp.content_type.startswith("audio/"):
                    content = await resp.text()
                    raise APIError(message="Faseeh returned non-audio data", body=content)

                output_emitter.initialize(
                    request_id=utils.shortuuid(),
                    sample_rate=SAMPLE_RATE,
                    num_channels=1,
                    mime_type="audio/wav",
                )

                # Stream WAV chunks to output emitter
                async for data, _ in resp.content.iter_chunks():
                    output_emitter.push(data)

        except asyncio.TimeoutError as e:
            raise APITimeoutError() from e
        except aiohttp.ClientResponseError as e:
            raise APIStatusError(
                message=e.message,
                status_code=e.status,
                request_id=None,
                body=None,
            ) from e
        except APIError:
            raise
        except APIStatusError:
            raise
        except Exception as e:
            raise APIConnectionError() from e


class SynthesizeStream(tts.SynthesizeStream):
    """Streaming TTS using Faseeh's streaming API (returns PCM16 chunks)"""

    def __init__(self, *, tts: TTS, conn_options: APIConnectOptions):
        super().__init__(tts=tts, conn_options=conn_options)
        self._tts: TTS = tts
        self._opts = tts._opts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = utils.shortuuid()
        url = f"{self._opts.base_url}/text-to-speech/{self._opts.model}"
        headers = {
            API_KEY_HEADER: self._opts.api_key,
            "Content-Type": "application/json",
        }

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=SAMPLE_RATE,
            num_channels=1,
            stream=True,
            mime_type="audio/pcm",
        )
        output_emitter.start_segment(segment_id=request_id)

        try:
            # Collect all text from input channel
            text_chunks: list[str] = []
            async for data in self._input_ch:
                if isinstance(data, self._FlushSentinel):
                    continue
                text_chunks.append(data)

            full_text = "".join(text_chunks)
            if not full_text:
                return

            payload = {
                "voice_id": self._opts.voice_id,
                "text": full_text,
                "stability": self._opts.stability,
                "streaming": True,
            }

            async with self._tts._ensure_session().post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(
                    total=None,  # No timeout for streaming
                    sock_connect=self._conn_options.timeout,
                ),
            ) as resp:
                if resp.status == 400:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Bad request: {error_data.get('errorMessage', 'Unknown error')}"
                    )
                elif resp.status == 401:
                    raise APIStatusError(
                        message="Unauthorized - invalid API key",
                        status_code=401,
                        request_id=None,
                        body=None,
                    )
                elif resp.status == 402:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Payment required: {error_data.get('errorMessage', 'Insufficient balance')}"
                    )
                elif resp.status == 403:
                    error_data = await resp.json()
                    raise APIError(
                        message=f"Forbidden: {error_data.get('errorMessage', 'Access denied')}"
                    )
                elif resp.status == 404:
                    raise APIStatusError(
                        message="Model or voice not found",
                        status_code=404,
                        request_id=None,
                        body=None,
                    )
                elif resp.status == 429:
                    raise APIStatusError(
                        message="Rate limit exceeded",
                        status_code=429,
                        request_id=None,
                        body=None,
                    )

                resp.raise_for_status()

                # Stream PCM16 chunks
                async for chunk, _ in resp.content.iter_chunks():
                    if chunk:
                        output_emitter.push(chunk)
                        self._mark_started()

                output_emitter.flush()

        except asyncio.TimeoutError as e:
            raise APITimeoutError() from e
        except aiohttp.ClientResponseError as e:
            raise APIStatusError(
                message=e.message,
                status_code=e.status,
                request_id=None,
                body=None,
            ) from e
        except APIError as e:
            logger.error(e)
            raise
        except APIStatusError as w:
            raise
        except Exception as e:
            raise APIConnectionError() from e
        finally:
            output_emitter.end_segment()


@dataclass
class _TTSOptions:
    api_key: str
    voice_id: str
    model: TTSModels | str
    stability: float
    base_url: str
