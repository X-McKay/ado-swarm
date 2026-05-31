from __future__ import annotations

from temporalio.exceptions import ApplicationError


def policy_denied(message: str) -> ApplicationError:
    return ApplicationError(message, type="PolicyDenied", non_retryable=True)


def approval_required(message: str) -> ApplicationError:
    return ApplicationError(message, type="ApprovalRequired", non_retryable=True)


def validation_failed(message: str) -> ApplicationError:
    return ApplicationError(message, type="ValidationFailed", non_retryable=True)
