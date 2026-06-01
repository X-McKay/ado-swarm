from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

from temporalio.common import RetryPolicy


class ActivityRetryProfile(StrEnum):
    MODEL = "model"
    PROVIDER_READ = "provider_read"
    PROVIDER_WRITE = "provider_write"
    GRAPH_WRITE = "graph_write"
    SANDBOX = "sandbox"
    DEFAULT = "default"


NON_RETRYABLE_BY_PROFILE = {
    ActivityRetryProfile.MODEL: [
        "PolicyDenied",
        "ApprovalRequired",
        "ValidationFailed",
        "InvalidModelRequest",
    ],
    ActivityRetryProfile.PROVIDER_WRITE: ["PolicyDenied", "ApprovalRequired", "InvalidMutation"],
    ActivityRetryProfile.PROVIDER_READ: ["PolicyDenied"],
    ActivityRetryProfile.GRAPH_WRITE: ["PolicyDenied", "ValidationFailed"],
    ActivityRetryProfile.SANDBOX: ["PolicyDenied", "ApprovalRequired"],
    ActivityRetryProfile.DEFAULT: ["PolicyDenied", "ApprovalRequired", "ValidationFailed"],
}

_TIMING_BY_PROFILE = {
    ActivityRetryProfile.MODEL: (2, 30, 4),
    ActivityRetryProfile.PROVIDER_WRITE: (5, 120, 3),
    ActivityRetryProfile.PROVIDER_READ: (1, 20, 5),
    ActivityRetryProfile.GRAPH_WRITE: (1, 30, 3),
    ActivityRetryProfile.SANDBOX: (2, 60, 2),
    ActivityRetryProfile.DEFAULT: (1, 30, 3),
}


def retry_policy(
    profile: ActivityRetryProfile = ActivityRetryProfile.DEFAULT,
    *,
    max_attempts: int | None = None,
) -> RetryPolicy:
    """Build a retry policy for a profile.

    Every profile is mapped explicitly (no silent fall-through to DEFAULT), and
    ``max_attempts`` overrides the profile default so callers can honor a
    per-task ``TaskSpec.max_attempts``.
    """
    initial, maximum, attempts = _TIMING_BY_PROFILE[profile]
    return RetryPolicy(
        initial_interval=timedelta(seconds=initial),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(seconds=maximum),
        maximum_attempts=max_attempts if max_attempts is not None else attempts,
        non_retryable_error_types=NON_RETRYABLE_BY_PROFILE[profile],
    )
