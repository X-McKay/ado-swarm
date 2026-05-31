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


def retry_policy(profile: ActivityRetryProfile = ActivityRetryProfile.DEFAULT) -> RetryPolicy:
    if profile == ActivityRetryProfile.MODEL:
        return RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=4,
            non_retryable_error_types=["PolicyDenied", "InvalidModelRequest"],
        )
    if profile == ActivityRetryProfile.PROVIDER_WRITE:
        return RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(minutes=2),
            maximum_attempts=3,
            non_retryable_error_types=["PolicyDenied", "ApprovalRequired", "InvalidMutation"],
        )
    if profile == ActivityRetryProfile.PROVIDER_READ:
        return RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=20),
            maximum_attempts=5,
        )
    return RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(seconds=30),
        maximum_attempts=3,
        non_retryable_error_types=["PolicyDenied", "ValidationFailed"],
    )
