"""Pipeline exception types."""


class ValidationError(ValueError):
    """Raised when pipeline data fails validation checks.

    Covers: invalid slugs, short articles, truncated content,
    oversized TG posts, pre-publish gate failures.
    """
