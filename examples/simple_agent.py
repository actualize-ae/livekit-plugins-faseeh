"""
Simple Arabic Voice Assistant using Faseeh TTS

This example demonstrates a basic voice assistant that:
- Listens to user speech (using any STT provider)
- Processes with an LLM
- Responds in Arabic using Faseeh TTS
"""
import logging

from dotenv import load_dotenv
from livekit.agents.metrics import STTMetrics, EOUMetrics, TTSMetrics, RealtimeModelMetrics, LLMMetrics, AgentMetrics

from livekit import agents
from livekit.agents import AgentServer, AgentSession, Agent
from livekit.plugins import silero, openai
from livekit.plugins import faseeh

load_dotenv(".env.local")


class ArabicAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""be funny""",
        )

server = AgentServer()

logger = logging.getLogger("simple_agent")


# Turn latency tracker — collects per-component metrics and prints a summary
class TurnTracker:
    def __init__(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self.eou_ms: float | None = None
        self.llm_ttft_ms: float | None = None
        self.tts_ttfb_ms: float | None = None
        self.tts_audio_s: float | None = None

    def record(self, metrics: AgentMetrics) -> None:
        if isinstance(metrics, EOUMetrics):
            self.eou_ms = round(metrics.end_of_utterance_delay * 1000)

        elif isinstance(metrics, (RealtimeModelMetrics, LLMMetrics)):
            ttft = metrics.ttft
            if ttft > 0:
                self.llm_ttft_ms = round(ttft * 1000)

        elif isinstance(metrics, TTSMetrics):
            self.tts_ttfb_ms = round(metrics.ttfb * 1000)
            self.tts_audio_s = round(metrics.audio_duration, 1)
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
        summary = " + ".join(parts)

        logger.info(f"--- Turn latency: {summary} = {total_s}s{audio_info} ---")
        self._reset()


turn_tracker = TurnTracker()


@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(modalities=['text']),
        tts=faseeh.TTS(),
        vad=silero.VAD.load(),
    )

    @session.on("metrics_collected")
    def _on_metrics_collected(event):
        turn_tracker.record(event.metrics)
        log_metrics(metrics=event.metrics)

    await session.start(
        room=ctx.room,
        agent=ArabicAssistant(),
    )

    await session.generate_reply(
        instructions="رحب بالمستخدم باللغة العربية وقدم المساعدة."
    )


def log_metrics(metrics: AgentMetrics) -> None:
    if isinstance(metrics, (RealtimeModelMetrics, LLMMetrics)):
        ttft = metrics.ttft if isinstance(metrics, LLMMetrics) else metrics.ttft
        logger.info(f"  LLM TTFT: {round(ttft * 1000)}ms")
    elif isinstance(metrics, TTSMetrics):
        logger.info(f"  TTS TTFB: {round(metrics.ttfb * 1000)}ms | audio: {round(metrics.audio_duration, 1)}s")
    elif isinstance(metrics, EOUMetrics):
        logger.info(f"  EOU: {round(metrics.end_of_utterance_delay * 1000)}ms")

if __name__ == "__main__":
    agents.cli.run_app(server)
