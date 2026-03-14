"""
OpenTelemetry Instrumentation for the Prediction Graph

Strands SDK has native OTEL support — it automatically creates spans for each
agent invocation with token counts, model IDs, cycle tracking, and timing.
We don't need to manually instrument individual agents.

This module handles:
1. Initializing StrandsTelemetry with the appropriate exporter (OTLP for
   production/CloudWatch, console for local development)
2. Providing a graph-level parent span that wraps the full 4-agent execution
   and carries the prompt version manifest as custom attributes
3. Helper to record prompt version manifest on any span

STRANDS NATIVE SPANS (automatic, no code needed):
- Agent span: gen_ai.agent.name, gen_ai.usage.input_tokens, gen_ai.usage.output_tokens,
  gen_ai.request.model, gen_ai.event.start_time, gen_ai.event.end_time
- Cycle spans: event_loop.cycle_id, gen_ai.user.message, gen_ai.choice
- Model invoke spans: gen_ai.usage.prompt_tokens, gen_ai.usage.completion_tokens
- Tool spans: gen_ai.tool.name, tool.status

OUR CUSTOM ADDITIONS:
- prompt.version.parser, prompt.version.categorizer, prompt.version.vb, prompt.version.review
- graph.round (round number for multi-round tracking)
- graph.prediction_text (first 100 chars for trace searchability)

EXPORTER MODES:
- "otlp": Send to OTLP endpoint (CloudWatch ADOT collector, Jaeger, etc.)
- "console": Print spans to stdout (local development)
- "none": Disable telemetry (unit tests, dry-run)
"""

import logging
import os
from typing import Dict, Optional, Any
from contextlib import contextmanager

from opentelemetry import trace

logger = logging.getLogger(__name__)

# Module-level state — initialized once, reused across invocations
_telemetry_initialized = False
_tracer: Optional[trace.Tracer] = None


def init_otel(mode: str = None) -> trace.Tracer:
    """
    Initialize Strands OTEL telemetry and return a Tracer for custom spans.

    Uses Strands' built-in StrandsTelemetry which automatically instruments
    all Agent invocations with spans, token counts, and timing. We just need
    to configure the exporter.

    Args:
        mode: Exporter mode — "otlp", "console", or "none".
              Defaults to OTEL_EXPORT_MODE env var, then "console".

    Returns:
        An OpenTelemetry Tracer for creating custom graph-level spans.
    """
    global _telemetry_initialized, _tracer

    if _telemetry_initialized and _tracer is not None:
        return _tracer

    export_mode = mode or os.environ.get("OTEL_EXPORT_MODE", "console")

    try:
        if export_mode == "none":
            logger.info("OTEL telemetry disabled (mode=none)")
            _tracer = trace.get_tracer("calledit.prediction_graph")
            _telemetry_initialized = True
            return _tracer

        from strands.telemetry import StrandsTelemetry
        telemetry = StrandsTelemetry()

        if export_mode == "otlp":
            telemetry.setup_otlp_exporter()
            logger.info("OTEL telemetry initialized with OTLP exporter")
        elif export_mode == "console":
            telemetry.setup_console_exporter()
            logger.info("OTEL telemetry initialized with console exporter")
        else:
            logger.warning(f"Unknown OTEL_EXPORT_MODE '{export_mode}', defaulting to console")
            telemetry.setup_console_exporter()

        _tracer = trace.get_tracer("calledit.prediction_graph")
        _telemetry_initialized = True
        return _tracer

    except Exception as e:
        # OTEL init failure is non-fatal — graph execution continues without tracing
        logger.error(f"Failed to initialize OTEL telemetry: {e}", exc_info=True)
        _tracer = trace.get_tracer("calledit.prediction_graph")
        _telemetry_initialized = True
        return _tracer


def record_prompt_version_manifest(span: trace.Span, manifest: Dict[str, str]) -> None:
    """
    Record prompt version manifest as span attributes.

    Args:
        span: The OTEL span to annotate.
        manifest: Dict like {"parser": "3", "categorizer": "5", "vb": "2", "review": "4"}
    """
    for agent_name, version in manifest.items():
        span.set_attribute(f"prompt.version.{agent_name}", str(version))


def read_prompt_version_manifest(span: trace.Span) -> Dict[str, str]:
    """
    Read prompt version manifest back from span attributes.
    Used for testing round-trip correctness (Property 12).

    Args:
        span: The OTEL span to read from.

    Returns:
        Dict like {"parser": "3", "categorizer": "5", "vb": "2", "review": "4"}
    """
    manifest = {}
    agent_names = ["parser", "categorizer", "vb", "review"]
    if hasattr(span, 'attributes') and span.attributes:
        for name in agent_names:
            key = f"prompt.version.{name}"
            if key in span.attributes:
                manifest[name] = str(span.attributes[key])
    return manifest


@contextmanager
def graph_trace_span(
    tracer: trace.Tracer,
    prompt_version_manifest: Dict[str, str],
    round_num: int = 1,
    prediction_text: str = "",
):
    """
    Context manager that creates a parent span for a full graph execution.

    Strands automatically creates child spans for each agent. This parent
    span wraps the entire graph execution and carries:
    - Prompt version manifest (which prompt versions are in use)
    - Round number (1 for initial, 2+ for refinement)
    - Prediction text snippet (for trace searchability)

    Usage:
        tracer = init_otel()
        with graph_trace_span(tracer, manifest, round_num=1, prediction_text="...") as span:
            result = graph(prompt)

    Args:
        tracer: OTEL Tracer from init_otel().
        prompt_version_manifest: Current prompt versions.
        round_num: Round number (1, 2, ...).
        prediction_text: The prediction being processed (truncated to 100 chars).

    Yields:
        The active OTEL Span.
    """
    with tracer.start_as_current_span("prediction_graph.execute") as span:
        try:
            span.set_attribute("graph.round", round_num)
            span.set_attribute("graph.prediction_text", prediction_text[:100])
            record_prompt_version_manifest(span, prompt_version_manifest)
            yield span
        except Exception as e:
            span.set_attribute("graph.error", str(e))
            span.set_status(trace.StatusCode.ERROR, str(e))
            raise
