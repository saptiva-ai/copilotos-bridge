"""
MongoDB document models using Beanie ODM
"""

from typing import List, Type

from beanie import Document

from .user import User
from .chat import ChatSession, ChatMessage
from .task import Task, DeepResearchTask
from .research import ResearchSource, Evidence
from .history import HistoryEvent, HistoryEventFactory, HistoryQuery

# List of all document models for Beanie initialization
def get_document_models() -> List[Type[Document]]:
    """Get all document models for Beanie initialization"""
    return [
        User,
        ChatSession,
        ChatMessage,
        Task,
        DeepResearchTask,
        ResearchSource,
        Evidence,
        HistoryEvent,
    ]

__all__ = [
    "User",
    "ChatSession",
    "ChatMessage",
    "Task",
    "DeepResearchTask",
    "ResearchSource",
    "Evidence",
    "HistoryEvent",
    "HistoryEventFactory",
    "HistoryQuery",
    "get_document_models",
]