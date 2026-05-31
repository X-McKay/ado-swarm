# ADR-0003: Model gateway

## Status

Accepted for the base architecture.

## Context

The runtime must be able to switch between local, hosted, and cloud model providers. Expected targets include deterministic fake models for CI, Ollama for local testing, OpenAI-compatible endpoints such as vLLM, Bedrock for AWS deployment, and LiteLLM for gateway-based routing.

## Decision

Agents depend on `ModelGateway` rather than provider SDKs. The gateway is configured by `MODEL_PROVIDER`, `MODEL_ID`, and optional provider-specific environment variables. The initial implementation activates the deterministic `fake` provider so local checks and CI cannot accidentally call remote or paid services.

## Consequences

The deterministic fake profile makes agent evaluations repeatable. Real provider adapters can be added without changing agent implementations, and model switching remains a configuration concern rather than a prompt or agent-code concern.
