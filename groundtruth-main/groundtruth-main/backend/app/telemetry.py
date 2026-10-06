"""OpenTelemetry instrumentation using the GenAI semantic conventions
(the gen_ai.* attribute namespace, stable as of OTel semconv v1.37).

This is the standard LLM telemetry vocabulary as of 2026 -- traces tagged
this way are readable by Langfuse, Arize Phoenix, Datadog, and any other
OTLP-compatible backend, without writing per-backend integration code.

Zero setup by default: spans print to the console. Set
OTEL_EXPORTER_OTLP_ENDPOINT to a real collector (a free Langfuse or Phoenix
instance, for example) to send them there instead -- also requires
`pip install opentelemetry-exporter-otlp-proto-http`.
"""
import os
from contextlib import contextmanager
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

_provider = None


def _init():
    global _provider
    if _provider is not None:
        return _provider

    provider = TracerProvider(resource=Resource.create({"service.name": "groundtruth"}))

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


@contextmanager
def chat_span(*, model: str):
    """Wraps the actual LLM call, so the span's own start/end time reflects
    real elapsed time -- not just the instant of attaching attributes after
    the call already finished. That distinction matters: a trace viewer's
    flame graph is built from span duration, not from an attribute.

    Set gen_ai.* result attributes (response model, token usage) and
    groundtruth.* attributes (latency_ms, cost_usd) on the yielded span
    once they're known, before the `with` block ends.
    """
    _init()
    tracer = trace.get_tracer("groundtruth")
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", "dashscope")
        span.set_attribute("gen_ai.request.model", model)
        yield span
