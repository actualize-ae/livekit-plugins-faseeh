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

@server.rtc_session()
async def my_agent(ctx: agents.JobContext):
    # Create Faseeh TTS instance
    session = AgentSession(
        stt=openai.STT(),  # Arabic STT
        llm=openai.LLM(model="gpt-5.1"),
        tts=faseeh.TTS(),  # Faseeh TTS for Arabic
        vad=silero.VAD.load(),
    )

    await session.start(
        room=ctx.room,
        agent=ArabicAssistant(),
    )

    # Greet in Arabic
    await session.generate_reply(
        instructions="رحب بالمستخدم باللغة العربية وقدم المساعدة."
    )
    @session.on("metrics_collected")
    def _on_metrics_collected(event):
        log_metrics(metrics=event.metrics)


def log_metrics(metrics: AgentMetrics) -> None:
    metadata: dict[str, str | float] = {}
    if metrics.metadata:
        metadata |= {
            "model_name": metrics.metadata.model_name or "unknown",
            "model_provider": metrics.metadata.model_provider or "unknown",
        }

    if isinstance(metrics, LLMMetrics):
        logger.info(
            "LLM metrics",
            extra=metadata
                  | {
                      "ttft": round(metrics.ttft, 2),
                      "prompt_tokens": metrics.prompt_tokens,
                      "prompt_cached_tokens": metrics.prompt_cached_tokens,
                      "completion_tokens": metrics.completion_tokens,
                      "tokens_per_second": round(metrics.tokens_per_second, 2),
                  },
        )
    elif isinstance(metrics, RealtimeModelMetrics):
        logger.info(
            "RealtimeModel metrics",
            extra=metadata
                  | {
                      "ttft": round(metrics.ttft, 2),
                      "input_tokens": metrics.input_tokens,
                      "cached_input_tokens": metrics.input_token_details.cached_tokens,
                      "output_tokens": metrics.output_tokens,
                      "total_tokens": metrics.total_tokens,
                      "tokens_per_second": round(metrics.tokens_per_second, 2),
                  },
        )
    elif isinstance(metrics, TTSMetrics):
        logger.info(
            "TTS metrics",
            extra=metadata
                  | {
                      "ttfb": metrics.ttfb,
                      "audio_duration": round(metrics.audio_duration, 2),
                  },
        )
    elif isinstance(metrics, EOUMetrics):
        logger.info(
            "EOU metrics",
            extra=metadata
                  | {
                      "end_of_utterance_delay": round(metrics.end_of_utterance_delay, 2),
                      "transcription_delay": round(metrics.transcription_delay, 2),
                  },
        )
    elif isinstance(metrics, STTMetrics):
        logger.info(
            "STT metrics",
            extra=metadata
                  | {
                      "audio_duration": round(metrics.audio_duration, 2),
                  },
        )

if __name__ == "__main__":
    agents.cli.run_app(server)
