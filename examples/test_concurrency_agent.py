"""
Faseeh TTS Concurrency & Streaming Test Agent

Tests concurrent streaming, flush handling, and interruption resilience:
1. FlushSentinel correctly flushes short buffers (short responses play audio)
2. Concurrent _read_input/_send_chunks (interruptions don't crash)
3. TTFB accuracy (measured before HTTP request, includes network round trip)

Run a specific test by speaking its number:
  "test one"   → 1-2 word response (FlushSentinel fix)
  "test two"   → Short sentence (below soft threshold)
  "test three" → Long response (concurrent streaming)
  "test four"  → Very long response, interrupt it mid-speech
  "test five"  → Rapid-fire: say it, interrupt, say it again

Watch logs for:
  ✅ TTS metrics with TTFB > 0ms
  ❌ "no audio frames were pushed" = BUG STILL PRESENT
"""

import logging

from dotenv import load_dotenv
from livekit.agents.metrics import STTMetrics, EOUMetrics, TTSMetrics, RealtimeModelMetrics, LLMMetrics, AgentMetrics

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent
from livekit.plugins import silero, openai
from livekit.plugins import faseeh

load_dotenv(".env.local")

# Force LLM to produce controlled output lengths via system instructions
SYSTEM_PROMPT = """\
You are a test assistant that responds ONLY in Arabic. Your job is to follow
length instructions precisely.

RULES:
- ALWAYS respond in Arabic only.
- When told to give a "short" answer: respond with EXACTLY 1-3 Arabic words. Nothing more.
- When told to give a "medium" answer: respond with EXACTLY 1 Arabic sentence (8-15 words).
- When told to give a "long" answer: respond with a long Arabic paragraph (50+ words). Keep going.
- When told to give a "very long" answer: respond with multiple Arabic paragraphs (100+ words). Do not stop early.

TEST COMMANDS (respond to these exactly):
- "test one" → Reply with exactly 2 Arabic words. Example: "مرحبا بك"
- "test two" → Reply with exactly one short Arabic sentence (8-12 words).
- "test three" → Reply with a long Arabic paragraph about the desert (50+ words).
- "test four" → Reply with a very long Arabic story about a traveler (100+ words). Keep going, do not stop.
- "test five" → Reply with exactly 3 Arabic words.

For any other input, reply with one medium Arabic sentence.
"""

server = AgentServer()
logger = logging.getLogger("test_tts_fixes")
logging.basicConfig(level=logging.INFO)

# Enable debug logs from the Faseeh TTS plugin
logging.getLogger("livekit.plugins.faseeh").setLevel(logging.DEBUG)

tts_call_count = 0
tts_total_ttfb = 0.0
cancelled_count = 0


class TestTurnTracker:
    """Tracks per-turn latency and flags concurrency/flush issues."""

    def __init__(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self.eou_ms: float | None = None
        self.llm_ttft_ms: float | None = None
        self.tts_ttfb_ms: float | None = None
        self.tts_audio_s: float | None = None
        self.cancelled: bool = False

    def record(self, metrics: AgentMetrics) -> None:
        global tts_call_count, tts_total_ttfb, cancelled_count

        if isinstance(metrics, EOUMetrics):
            self.eou_ms = round(metrics.end_of_utterance_delay * 1000)
            logger.info(f"  EOU: {self.eou_ms}ms")

        elif isinstance(metrics, (RealtimeModelMetrics, LLMMetrics)):
            ttft = metrics.ttft
            if ttft > 0:
                self.llm_ttft_ms = round(ttft * 1000)
                logger.info(f"  LLM TTFT: {self.llm_ttft_ms}ms")

        elif isinstance(metrics, TTSMetrics):
            tts_call_count += 1
            ttfb_ms = round(metrics.ttfb * 1000)
            tts_total_ttfb += metrics.ttfb
            audio_dur = round(metrics.audio_duration, 2)

            self.tts_ttfb_ms = ttfb_ms
            self.tts_audio_s = audio_dur
            self.cancelled = metrics.cancelled

            # Concurrency fix validation
            status = "✅" if ttfb_ms > 5 else "⚠️  SUSPICIOUS (near 0ms — _mark_started may be wrong)"
            cancel_tag = " [CANCELLED — concurrency fix kept it clean]" if metrics.cancelled else ""
            logger.info(
                f"  TTS #{tts_call_count} {status} "
                f"TTFB={ttfb_ms}ms | audio={audio_dur}s{cancel_tag}"
            )

            if metrics.cancelled:
                cancelled_count += 1
                logger.info(
                    f"  ℹ️  Stream was interrupted/cancelled ({cancelled_count} total). "
                    f"No crash = concurrency fix working."
                )

            self._print_summary()

    def _print_summary(self) -> None:
        parts = []
        total = 0.0

        if self.eou_ms is not None:
            parts.append(f"EOU {self.eou_ms}ms")
            total += self.eou_ms

        if self.llm_ttft_ms is not None:
            parts.append(f"LLM {self.llm_ttft_ms}ms")
            total += self.llm_ttft_ms

        if self.tts_ttfb_ms is not None:
            parts.append(f"TTS {self.tts_ttfb_ms}ms")
            total += self.tts_ttfb_ms

        total_s = round(total / 1000, 2)
        audio_info = f" | audio={self.tts_audio_s}s" if self.tts_audio_s else ""
        cancel_info = " [CANCELLED]" if self.cancelled else ""
        summary = " + ".join(parts)

        logger.info(f"  --- Turn latency: {summary} = {total_s}s{audio_info}{cancel_info} ---")

        # Running average
        if tts_call_count > 0:
            avg_ttfb = round((tts_total_ttfb / tts_call_count) * 1000)
            logger.info(f"  --- Avg TTFB over {tts_call_count} calls: {avg_ttfb}ms | cancelled: {cancelled_count} ---")

        self._reset()


turn_tracker = TestTurnTracker()


@server.rtc_session()
async def test_agent(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(modalities=["text"]),
        tts=faseeh.TTS(),
        vad=silero.VAD.load(),
    )

    @session.on("metrics_collected")
    def _on_metrics(event):
        turn_tracker.record(event.metrics)

    await session.start(
        room=ctx.room,
        agent=Agent(instructions=SYSTEM_PROMPT),
    )

    # Auto-trigger test 1 on connect (short response = FlushSentinel test)
    logger.info("=" * 60)
    logger.info("TEST AGENT STARTED — speak a test command")
    logger.info("  'test one'   → 2 words (FlushSentinel fix)")
    logger.info("  'test two'   → short sentence")
    logger.info("  'test three' → long paragraph (streaming)")
    logger.info("  'test four'  → very long, INTERRUPT it (concurrency fix)")
    logger.info("  'test five'  → 3 words, rapid interrupt test")
    logger.info("")
    logger.info("WHAT TO VERIFY:")
    logger.info("  ✅ All tests produce TTS TTFB > 5ms")
    logger.info("  ✅ test one/five: audio plays (FlushSentinel flushes short buffers)")
    logger.info("  ✅ test four interrupted: no crash, 'CANCELLED' in logs")
    logger.info("  ❌ 'no audio frames were pushed' = BUG STILL PRESENT")
    logger.info("=" * 60)

    await session.generate_reply(
        instructions="قل فقط: مرحبا"
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
