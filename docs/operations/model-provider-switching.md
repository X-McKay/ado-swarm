# Model Provider Switching

The base architecture exposes model inference through `ModelGateway`. The default `fake` provider is deterministic and is used for tests and agent evaluations. Real providers should be enabled behind the same gateway rather than called directly from agents.

| Provider | Intended use | Environment shape |
|---|---|---|
| `fake` | CI, local tests, deterministic evaluations. | `MODEL_PROVIDER=fake`, `MODEL_ID=fake-deterministic`. |
| `ollama` | Local LLM smoke testing. | `MODEL_PROVIDER=ollama`, `MODEL_BASE_URL=http://localhost:11434`, `MODEL_ID=<ollama-model>`. |
| `openai_compatible` | vLLM, LM Studio, or cluster ingress exposing OpenAI-compatible APIs. | `MODEL_PROVIDER=openai_compatible`, `MODEL_BASE_URL=<endpoint>/v1`, `MODEL_ID=<model>`. |
| `bedrock` | AWS-hosted inference. | `MODEL_PROVIDER=bedrock`, `MODEL_ID=<bedrock-model-id>`, AWS credentials in the runtime environment. |
| `litellm` | Unified gateway/proxy routing. | `MODEL_PROVIDER=litellm`, `MODEL_BASE_URL=<proxy-url>`, `MODEL_ID=<provider/model>`. |

Only the fake provider is fully active in the initial base architecture. The real provider adapters should be added after the orchestration, source-provider, and audit boundaries are stable. This keeps tests fast and prevents accidental paid or remote inference calls during early development.
