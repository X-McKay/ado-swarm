

def ${name}_impl(payload: dict) -> dict:
    """Return a deterministic echo result for the generated tool contract."""
    return {"result": payload}


@tool
def ${name}(payload: dict) -> dict:
    """Process a JSON payload deterministically.

    Args:
        payload: JSON-compatible input for the tool.

    Returns:
        A JSON object containing the deterministic result.
    """
    return ${name}_impl(payload)
