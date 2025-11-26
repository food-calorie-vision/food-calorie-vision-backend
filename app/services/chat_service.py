from typing import Optional
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

from app.db.models import Conversation
from app.core.config import get_settings

class ChatService:
    def __init__(self, redis_client: redis.Redis, db_session: AsyncSession):
        self.redis_client = redis_client
        self.db_session = db_session
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
        self.llm = ChatOpenAI(api_key=settings.openai_api_key, model="gpt-4o-mini", temperature=0)

    async def get_previous_session_id_and_update(
        self, user_id: int, current_session_id: str
    ) -> Optional[str]:
        """
        Updates the user's last seen session ID and returns the previous one.
        """
        if not self.redis_client:
            return None

        redis_key = f"user:{user_id}:last_session"
        old_session_id = await self.redis_client.getset(redis_key, current_session_id)
        
        return old_session_id

    async def summarize_conversation_if_needed(self, session_id: str) -> None:
        """
        Checks if a conversation needs summarization and performs it.
        """
        stmt = select(Conversation).where(Conversation.session_id == session_id)
        result = await self.db_session.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            return

        # Check if summarization is needed
        if conversation.last_message_timestamp and (
            not conversation.last_message_summarized_at or 
            conversation.last_message_timestamp > conversation.last_message_summarized_at
        ):
            # Extract new messages (this logic assumes all_chat is a structured log)
            # For simplicity here, we'll just use the whole chat.
            # A more robust solution would parse messages after the last summary timestamp.
            full_chat_history = conversation.all_chat or ""
            previous_summary = conversation.sum_chat or ""

            new_summary = await self._generate_incremental_summary(
                previous_summary, full_chat_history
            )

            # Update conversation in DB
            conversation.sum_chat = new_summary
            conversation.last_message_summarized_at = conversation.last_message_timestamp
            self.db_session.add(conversation)
            await self.db_session.commit()

    async def _generate_incremental_summary(
        self, old_summary: str, full_chat_history: str
    ) -> str:
        """
        Generates a new summary based on an old summary and new chat messages.
        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a summarization assistant. Your task is to create a concise summary of a user's conversation with a nutritionist chatbot. "
                    "An optional previous summary is provided. Integrate the key information from the full chat history into the previous summary. "
                    "Focus on the user's goals, preferences, questions, and any important conclusions or recommendations made."
                    "The final summary should be a self-contained, coherent paragraph in Korean."
                ),
                ("human", 
                 "Previous Summary:\n"
                 "{old_summary}\n\n"
                 "Full Chat History (use this to update the summary):\n"
                 "{chat_history}"
                ),
            ]
        )
        
        chain = prompt | self.llm | StrOutputParser()
        
        new_summary = await chain.ainvoke({
            "old_summary": old_summary or "이전 요약 없음",
            "chat_history": full_chat_history,
        })
        
        return new_summary
