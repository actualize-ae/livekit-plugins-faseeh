# Quick Start Guide

## Setup in 3 Minutes

### 1. Create a New Repository on GitHub

```bash
# On GitHub.com:
# 1. Click "New Repository"
# 2. Name: livekit-plugins-faseeh
# 3. Make it public
# 4. Don't initialize with README (we already have one)
```

### 2. Initialize and Push

```bash
cd livekit-plugins-faseeh-standalone

# Initialize git
git init
git add .
git commit -m "Initial commit: Faseeh TTS plugin for LiveKit"

git remote add origin https://github.com/actualize-ae/livekit-plugins-faseeh.git
git branch -M main
git push -u origin main
```

### 3. Publish to PyPI

```bash
# Install build tools
pip install --upgrade build twine

# Build the package
python -m build

# Upload to PyPI (you'll need a PyPI account)
python -m twine upload dist/*
```

That's it! Your package is now on PyPI.

## Test Installation

```bash
# Create a new virtual environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install your package
pip install livekit-plugins-faseeh

# Test it
python -c "from livekit.plugins import faseeh; print('✅ Plugin installed!', faseeh.__version__)"
```

## First Voice Agent

Create `my_agent.py`:

```python
import os
from livekit.plugins import faseeh

# Set your API key
os.environ["FASEEH_API_KEY"] = "your-api-key-here"

# Create TTS instance
tts = faseeh.TTS(
    voice_id="ar-hijazi-female-2",
    model="faseeh-mini-v1-preview",
    stability=0.5,
)

print(f"✅ Using {tts.provider} TTS with model: {tts.model}")
```

Run it:
```bash
python my_agent.py
```

## Next Steps

- Read [PUBLISHING.md](PUBLISHING.md) for detailed publishing instructions
- Check [README.md](README.md) for full documentation
- See [example.py](example.py) for usage examples
- Star the repo if you find it useful! ⭐

## Need Help?

- **Issues**: https://github.com/actualize-ae/livekit-plugins-faseeh/issues
- **Faseeh AI**: apps@actualize.pro
- **LiveKit Docs**: https://docs.livekit.io
