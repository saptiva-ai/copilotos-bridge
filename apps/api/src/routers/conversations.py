"""
Conversations API endpoints as specified in saptiva-chat-fixes-v3.yaml.
"""

from datetime import datetime
from typing import Optional
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel

from ..models.chat import ChatSession as ChatSessionModel, ConversationState
from ..schemas.chat import ChatSessionListResponse, ChatSession

logger = structlog.get_logger(__name__)
router = APIRouter()


class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = None
    model: str = "SAPTIVA_CORTEX"


class ConversationUpdateRequest(BaseModel):
    """Request to update conversation metadata."""
    title: Optional[str] = None
    model: Optional[str] = None


class ConversationResponse(BaseModel):
    """Response for conversation operations."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    model: str


@router.get("/conversations", response_model=ChatSessionListResponse, tags=["conversations"])
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    http_request: Request = None
) -> ChatSessionListResponse:
    """
    GET /api/conversations -> lista compacta (id,title,updatedAt)

    Returns a compact list of conversations for the sidebar.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Build query
        query = ChatSessionModel.find(ChatSessionModel.user_id == user_id)

        # Apply search filter if provided
        if search:
            query = query.find({"title": {"$regex": search, "$options": "i"}})

        # Get total count
        total_count = await query.count()

        # Get sessions with pagination, ordered by most recent update
        sessions_docs = await query.sort(-ChatSessionModel.updated_at).skip(offset).limit(limit).to_list()

        # Convert to response schema
        sessions = []
        for session in sessions_docs:
            sessions.append(ChatSession(
                id=session.id,
                title=session.title,
                user_id=session.user_id,
                created_at=session.created_at,
                updated_at=session.updated_at,
                first_message_at=session.first_message_at,  # Progressive Commitment
                last_message_at=session.last_message_at,    # Progressive Commitment
                message_count=session.message_count,
                settings=session.settings.model_dump() if hasattr(session.settings, 'model_dump') else session.settings,
                pinned=session.pinned,
                state=session.state  # P0-BE-UNIQ-EMPTY: Include state
            ))

        has_more = offset + len(sessions) < total_count

        logger.info(
            "Retrieved conversations list",
            user_id=user_id,
            count=len(sessions),
            total=total_count
        )

        return ChatSessionListResponse(
            sessions=sessions,
            total_count=total_count,
            has_more=has_more
        )

    except Exception as e:
        logger.error("Error retrieving conversations", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["conversations"])
async def get_conversation(
    conversation_id: str,
    http_request: Request = None
) -> ConversationResponse:
    """
    GET /api/conversations/:id -> conversation details

    Returns conversation metadata without full message history.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Get conversation
        conversation = await ChatSessionModel.get(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check access
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation"
            )

        # Extract model from settings
        model = "SAPTIVA_CORTEX"  # default
        if hasattr(conversation.settings, 'model'):
            model = conversation.settings.model
        elif isinstance(conversation.settings, dict) and 'model' in conversation.settings:
            model = conversation.settings['model']

        logger.info(
            "Retrieved conversation details",
            conversation_id=conversation_id,
            user_id=user_id
        )

        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=conversation.message_count,
            model=model
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving conversation", error=str(e), conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.post("/conversations", response_model=ConversationResponse, tags=["conversations"])
async def create_conversation(
    request: ConversationCreateRequest,
    http_request: Request = None
) -> ConversationResponse:
    """
    POST /api/conversations -> crea nueva conversación o reusa draft existente

    P0-BE-POST-REUSE: Reuses existing empty DRAFT conversation if one exists for the user.
    This prevents creating multiple empty conversations when user clicks "New" repeatedly.

    The unique index 'unique_draft_per_user' in MongoDB enforces one DRAFT per user.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # P0-BE-POST-REUSE: Check if user already has a DRAFT conversation
        existing_draft = await ChatSessionModel.find_one(
            ChatSessionModel.user_id == user_id,
            ChatSessionModel.state == "draft"
        )

        if existing_draft:
            # If draft is empty (0 messages), reuse it
            if existing_draft.message_count == 0:
                logger.info(
                    "Reusing existing empty draft conversation",
                    conversation_id=existing_draft.id,
                    user_id=user_id
                )

                # Extract model from settings
                model = request.model
                if hasattr(existing_draft.settings, 'model'):
                    model = existing_draft.settings.model
                elif isinstance(existing_draft.settings, dict) and 'model' in existing_draft.settings:
                    model = existing_draft.settings['model']

                return ConversationResponse(
                    id=existing_draft.id,
                    title=existing_draft.title,
                    created_at=existing_draft.created_at,
                    updated_at=existing_draft.updated_at,
                    message_count=existing_draft.message_count,
                    model=model
                )
            else:
                # Draft has messages, convert it to ACTIVE state to allow new draft creation
                logger.info(
                    "Converting non-empty draft to active state",
                    conversation_id=existing_draft.id,
                    user_id=user_id,
                    message_count=existing_draft.message_count,
                    state_from="draft",
                    state_to="active"
                )
                await existing_draft.update({"$set": {
                    "state": ConversationState.ACTIVE.value,
                    "updated_at": datetime.utcnow()
                }})

        # Generate conversation ID and title
        conversation_id = str(uuid.uuid4())
        title = request.title or f"Nueva conversación {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Create conversation in DRAFT state (enforced by unique index)
        conversation = ChatSessionModel(
            id=conversation_id,
            user_id=user_id,
            title=title,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            message_count=0,
            settings={"model": request.model},
            state="draft"  # P0-BE-UNIQ-EMPTY: Explicit DRAFT state
        )

        await conversation.insert()

        logger.info(
            "Created new draft conversation",
            conversation_id=conversation_id,
            user_id=user_id,
            title=title,
            model=request.model,
            state="draft"
        )

        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=conversation.message_count,
            model=request.model
        )

    except Exception as e:
        # Handle duplicate key error (E11000) from unique_draft_per_user index
        if "E11000" in str(e) and "unique_draft_per_user" in str(e):
            logger.warning(
                "Duplicate draft detected, attempting to fix orphaned draft",
                error=str(e),
                user_id=user_id
            )

            # Try to fix by transitioning existing draft with messages to ACTIVE
            try:
                existing_draft_with_msgs = await ChatSessionModel.find_one(
                    ChatSessionModel.user_id == user_id,
                    ChatSessionModel.state == ConversationState.DRAFT.value
                )

                if existing_draft_with_msgs and existing_draft_with_msgs.message_count > 0:
                    # Transition to ACTIVE
                    await existing_draft_with_msgs.update({"$set": {
                        "state": ConversationState.ACTIVE.value,
                        "updated_at": datetime.utcnow()
                    }})

                    logger.info(
                        "Fixed orphaned draft, transitioned to active",
                        conversation_id=existing_draft_with_msgs.id,
                        user_id=user_id,
                        message_count=existing_draft_with_msgs.message_count
                    )

                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="An existing draft was fixed. Please try creating a new conversation again."
                    )
            except HTTPException:
                raise
            except Exception as fix_error:
                logger.error("Failed to fix orphaned draft", error=str(fix_error), user_id=user_id)

        logger.error("Error creating conversation", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["conversations"])
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    http_request: Request = None
) -> ConversationResponse:
    """
    PATCH /api/conversations/:id -> rename/meta

    Updates conversation metadata (title, model, etc.).
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Get conversation
        conversation = await ChatSessionModel.get(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check access
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation"
            )

        # Prepare updates
        updates = {"updated_at": datetime.utcnow()}

        if request.title is not None:
            updates["title"] = request.title

        if request.model is not None:
            # Update settings
            settings = conversation.settings
            if isinstance(settings, dict):
                settings["model"] = request.model
            else:
                settings = {"model": request.model}
            updates["settings"] = settings

        # Apply updates
        await conversation.update({"$set": updates})

        # Refresh conversation data
        updated_conversation = await ChatSessionModel.get(conversation_id)

        # Extract model from settings
        model = "SAPTIVA_CORTEX"  # default
        if hasattr(updated_conversation.settings, 'model'):
            model = updated_conversation.settings.model
        elif isinstance(updated_conversation.settings, dict) and 'model' in updated_conversation.settings:
            model = updated_conversation.settings['model']

        logger.info(
            "Updated conversation",
            conversation_id=conversation_id,
            user_id=user_id,
            updates=list(updates.keys())
        )

        return ConversationResponse(
            id=updated_conversation.id,
            title=updated_conversation.title,
            created_at=updated_conversation.created_at,
            updated_at=updated_conversation.updated_at,
            message_count=updated_conversation.message_count,
            model=model
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating conversation", error=str(e), conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation"
        )


@router.delete("/conversations/{conversation_id}", tags=["conversations"])
async def delete_conversation(
    conversation_id: str,
    http_request: Request = None
):
    """
    DELETE /api/conversations/:id -> delete conversation

    Deletes a conversation and all its messages.
    """
    user_id = getattr(http_request.state, 'user_id', 'anonymous')

    try:
        # Get conversation
        conversation = await ChatSessionModel.get(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check access
        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to conversation"
            )

        # Delete conversation (this should cascade to messages)
        await conversation.delete()

        logger.info(
            "Deleted conversation",
            conversation_id=conversation_id,
            user_id=user_id
        )

        return {"message": "Conversation deleted successfully", "id": conversation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting conversation", error=str(e), conversation_id=conversation_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation"
        )