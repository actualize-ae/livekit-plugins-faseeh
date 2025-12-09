# Faseeh TTS Examples

This directory contains practical examples of using the Faseeh TTS plugin with LiveKit Agents.

## Setup

1. **Install dependencies**:
   ```bash
   pip install livekit-plugins-faseeh
   pip install livekit-agents livekit-plugins-deepgram livekit-plugins-openai livekit-plugins-silero
   pip install python-dotenv
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API keys
   ```

3. **Run an example**:
   ```bash
   python simple_agent.py dev
   ```

## Examples

### 1. Simple Agent (`simple_agent.py`)

A basic Arabic voice assistant using Faseeh TTS.

**Features**:
- Arabic speech-to-text (Deepgram)
- OpenAI GPT for responses
- Faseeh TTS for Arabic voice output
- Voice activity detection (Silero VAD)

**Run**:
```bash
python simple_agent.py dev
```

**Use case**: Simple Arabic conversational AI for customer support, education, or general assistance.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `LIVEKIT_URL` | LiveKit server URL | Yes |
| `LIVEKIT_API_KEY` | LiveKit API key | Yes |
| `LIVEKIT_API_SECRET` | LiveKit API secret | Yes |
| `FASEEH_API_KEY` | Faseeh AI API key | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes |

## Configuration Options

### Faseeh TTS Settings

```python
faseeh_tts = faseeh.TTS(
    voice_id="ar-hijazi-female-2",      # Voice to use
    model="faseeh-mini-v1-preview",     # or "faseeh-v1-preview"
    stability=0.6,                       # 0.0 to 1.0 (higher = more consistent)
)
```

### Available Models

- **`faseeh-mini-v1-preview`**: Faster, lower latency (recommended for real-time)
- **`faseeh-v1-preview`**: Higher quality, slightly higher latency

### Voice IDs

Check the [Faseeh AI dashboard](https://app.faseeh.ai) for available voices, or use:
- `ar-hijazi-female-2` (default)
- More voices available from Faseeh AI

## Testing Locally

Use LiveKit CLI to test locally:

```bash
# Start the agent
python simple_agent.py dev

# In another terminal, connect a participant
lk room join --url wss://your-server --token your-token
```

## Common Issues

### "FASEEH_API_KEY not found"

Make sure you've set the environment variable:
```bash
export FASEEH_API_KEY=your-api-key
```

Or add it to your `.env.local` file.

### "Model not enabled for account"

Contact Faseeh AI support to enable the model:
- Email: apps@actualize.pro
- Website: https://faseeh.ai

### "Rate limit exceeded"

You've hit the API rate limit. Check your Faseeh AI dashboard for limits, or:
- Add retry logic
- Reduce request frequency
- Upgrade your plan

## Production Deployment

For production deployment:

1. **Use environment-specific configs**:
   ```bash
   # .env.production
   LIVEKIT_URL=wss://prod.livekit.cloud
   ```

2. **Run with worker mode**:
   ```bash
   python simple_agent.py start
   ```

3. **Deploy with Docker** (see [LiveKit docs](https://docs.livekit.io/agents/deployment/))

4. **Monitor usage**:
   - LiveKit dashboard: https://cloud.livekit.io
   - Faseeh dashboard: https://app.faseeh.ai

## Resources

- **Faseeh AI**: https://faseeh.ai
- **LiveKit Agents**: https://docs.livekit.io/agents/
- **Plugin Source**: https://github.com/actualize-ae/livekit-plugins-faseeh

## Support

- **Plugin Issues**: https://github.com/actualize-ae/livekit-plugins-faseeh/issues
- **Faseeh AI**: apps@actualize.ae
- **LiveKit**: https://livekit.io/support
