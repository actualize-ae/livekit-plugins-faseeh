# Faseeh Plugin for LiveKit Agents

[![PyPI version](https://badge.fury.io/py/livekit-plugins-faseeh.svg)](https://badge.fury.io/py/livekit-plugins-faseeh)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This plugin provides Arabic text-to-speech capabilities using [Faseeh AI](https://faseeh.ai) for [LiveKit Agents](https://github.com/livekit/agents).

## Installation

### From PyPI (once published)

```bash
pip install livekit-plugins-faseeh
```

### From Source

```bash
git clone https://github.com/yourusername/livekit-plugins-faseeh.git
cd livekit-plugins-faseeh
pip install -e .
```

## Quick Start

### Basic Usage

```python
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent
from livekit.plugins import silero, deepgram, openai, faseeh

load_dotenv()

class ArabicAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="أنت مساعد صوتي ذكي يتحدث العربية."
        )

server = AgentServer()

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Create Faseeh TTS instance
    faseeh_tts = faseeh.TTS(
        voice_id="ar-hijazi-female-2",
        model="faseeh-mini-v1-preview",
        stability=0.6,
    )

    session = AgentSession(
        stt=deepgram.STT(language="ar"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=faseeh_tts,  # Use Faseeh for Arabic TTS
        vad=silero.VAD.load(),
    )

    await session.start(room=ctx.room, agent=ArabicAssistant())

    # Greet in Arabic
    await session.generate_reply(
        instructions="رحب بالمستخدم وقدم المساعدة."
    )

if __name__ == "__main__":
    agents.cli.run_app(server)
```

### Run the Agent

```bash
# Set environment variables
export FASEEH_API_KEY=your-api-key
export OPENAI_API_KEY=your-openai-key

# Run in development mode
python agent.py dev
```

See the [examples/](examples/) directory for more complete examples including bilingual support, noise cancellation, and dynamic voice switching.

## Configuration

### Environment Variables

Set your Faseeh API key:

```bash
export FASEEH_API_KEY=your_api_key_here
```

### TTS Options

The `TTS` class accepts the following parameters:

- `voice_id` (str): Voice ID to use. Default: `"ar-hijazi-female-2"`
- `model` (str): Model to use. Options:
  - `"faseeh-v1-preview"` - Full model
  - `"faseeh-mini-v1-preview"` - Faster, lighter model (default)
- `stability` (float): Voice stability from 0.0 to 1.0. Higher values produce more consistent output. Default: `0.5`
- `api_key` (str, optional): API key. If not provided, uses `FASEEH_API_KEY` environment variable
- `base_url` (str, optional): Custom API base URL
- `http_session` (aiohttp.ClientSession, optional): Custom HTTP session

### Update Options

You can update TTS options dynamically:

```python
faseeh_tts.update_options(
    voice_id="ar-hijazi-female-2",
    model="faseeh-v1-preview",
    stability=0.7,
)
```

### Streaming Mode

For real-time applications, use streaming mode:

```python
# Create streaming instance
stream = faseeh_tts.stream()

# Push text incrementally
stream.push_text("مرحبا ")
stream.push_text("كيف حالك")

# Flush and end input
stream.flush()
stream.end_input()

# Receive audio chunks as they're generated
async for event in stream:
    # Process audio frames in real-time
    if hasattr(event, "frame"):
        audio_frame = event.frame
```

## Features

- ✅ Arabic text-to-speech synthesis
- ✅ Multiple voice options
- ✅ Adjustable voice stability
- ✅ Two model options (standard and mini)
- ✅ 24kHz PCM16 audio output
- ✅ Both streaming and non-streaming modes
- ✅ Low-latency streaming for real-time applications

## Models

| Model | Description |
|-------|-------------|
| `faseeh-v1-preview` | Full-featured model with highest quality |
| `faseeh-mini-v1-preview` | Faster, lighter model for low-latency applications |

## Error Handling

The plugin handles the following error codes:

- **400**: Bad request (invalid parameters)
- **401**: Unauthorized (invalid API key)
- **402**: Payment required (insufficient wallet balance)
- **403**: Forbidden (model not enabled for account)
- **404**: Model or voice not found
- **429**: Rate limit exceeded

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues or questions:
- **Plugin Issues**: [GitHub Issues](https://github.com/yourusername/livekit-plugins-faseeh/issues)
- **Faseeh AI**: [apps@actualize.pro](mailto:apps@actualize.pro)
- **LiveKit**: [https://docs.livekit.io](https://docs.livekit.io)

## Acknowledgments

- [Faseeh AI](https://faseeh.ai) for providing the Arabic TTS API
- [LiveKit](https://livekit.io) for the Agents framework

## License

Apache License 2.0 - see [LICENSE](LICENSE) file for details
