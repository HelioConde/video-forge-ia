"""Gerentes independentes por canal, com YouTube read-only e antirrepetição."""
from .strategy import select_idea, editorial_fingerprint, DuplicateTopic
from .youtube import YouTubeReadOnly, YouTubeReadError

__all__ = ["select_idea", "editorial_fingerprint", "DuplicateTopic",
           "YouTubeReadOnly", "YouTubeReadError"]
