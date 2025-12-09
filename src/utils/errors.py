"""Error handling utilities."""

from typing import Optional


class ArchieOSError(Exception):
    """Base exception for ArchieOS backend."""
    pass


class SlackVerificationError(ArchieOSError):
    """Slack signature verification failed."""
    pass


class ClassificationError(ArchieOSError):
    """LLM classification error."""
    pass


class IntakeError(ArchieOSError):
    """Intake processing error."""
    pass


class SupabaseError(ArchieOSError):
    """Supabase operation error."""
    pass

