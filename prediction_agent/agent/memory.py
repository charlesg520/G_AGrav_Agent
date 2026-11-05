"""
Persistent Multi-Session Conversational Memory for the Trading Agent.
Stores and retrieves conversation histories across sessions from SQLite.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from prediction_agent.database.db import db
from prediction_agent.database.models import ChatMessageModel, ChatSessionModel

class ChatMemoryManager:
    def __init__(self):
        self.db = db

    async def get_or_create_session(self, session_id: str, title: str = "Trading Session") -> ChatSessionModel:
        return await self.db.get_or_create_chat_session(session_id, title)

    async def list_sessions(self, limit: int = 20) -> List[ChatSessionModel]:
        return await self.db.list_chat_sessions(limit)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatMessageModel:
        msg = ChatMessageModel(
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
            created_at=datetime.now(timezone.utc)
        )
        await self.db.add_chat_message(msg)
        return msg

    async def get_session_history(self, session_id: str, limit: int = 30) -> List[ChatMessageModel]:
        return await self.db.get_chat_messages(session_id, limit)

    async def get_cross_session_summary(self, current_session_id: str, limit: int = 5) -> str:
        """
        Retrieves a context summary of recent past chat sessions so the agent remembers past context.
        """
        sessions = await self.list_sessions(limit=limit + 1)
        other_sessions = [s for s in sessions if s.id != current_session_id][:limit]
        
        if not other_sessions:
            return "No previous chat sessions found."

        summary_lines = ["Recent Past Conversations:"]
        for s in other_sessions:
            msgs = await self.get_session_history(s.id, limit=3)
            last_msg = msgs[-1].content[:80] + "..." if msgs else "No messages"
            summary_lines.append(f"- Session '{s.title}' ({s.updated_at.strftime('%Y-%m-%d %H:%M')}): Last topic: {last_msg}")

        return "\n".join(summary_lines)
