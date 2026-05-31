from __future__ import annotations

from ado_swarm.temporal.policies import ActivityRetryProfile, retry_policy


def test_retry_policy_has_bounded_model_attempts() -> None:
    policy = retry_policy(ActivityRetryProfile.MODEL)
    assert policy.maximum_attempts == 4
    assert "PolicyDenied" in list(policy.non_retryable_error_types or [])
