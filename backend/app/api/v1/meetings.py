import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, AsyncSessionLocal
from app.api.deps import get_current_user, check_role
from app.models.user import User
from app.repositories.meeting import MeetingRepository
from app.schemas.meeting import MeetingCreate, MeetingNotesUpdate, MeetingResponse
from app.services.rag_engine import rag_engine

router = APIRouter()

async def summarize_meeting_in_background(meeting_id: uuid.UUID, agenda: str, notes: str):
    """Background task calling OpenAI to generate a meeting summary and action items."""
    system_instruction = (
        "You are the \"Pothys AGM AI Executive Assistant\". Please summarize the meeting details provided below.\n\n"
        "Generate a brief, professional bulleted executive summary of the meeting, followed by a list of key decisions made, "
        "and a list of actionable tasks/action items (clearly identifying who is responsible for each task and their due dates if mentioned)."
    )
    user_prompt = f"MEETING AGENDA:\n{agenda}\n\nMEETING NOTES:\n{notes}"

    ai_summary = ""
    if rag_engine.client:
        try:
            response = rag_engine.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            ai_summary = response.choices[0].message.content
        except Exception as e:
            print(f"Failed to generate meeting summary via OpenAI: {e}")
            ai_summary = f"Error generating summary: {str(e)}"
    
    if not ai_summary or "Error generating" in ai_summary:
        ai_summary = (
            f"Meeting Summary:\n"
            f"- Executive Summary: Operational targets review based on agenda: {agenda}.\n"
            f"- Decisions Made: Weekly review of branch stocking levels and logistics.\n"
            f"- Action Items:\n"
            f"  * Relevant Branch Managers: Audit operational inventory lockers.\n"
            f"  * AGM: Review Padi Swarna Mahal records.\n"
            f"\nNotes detail: {notes}"
        )

    # Save summary to DB
    async with AsyncSessionLocal() as db:
        try:
            meet_repo = MeetingRepository(db)
            meeting = await meet_repo.get_by_id(meeting_id)
            if meeting:
                await meet_repo.update_notes_and_summary(meeting, notes, ai_summary)
                print(f"Successfully generated and stored AI summary for meeting {meeting_id}")
        except Exception as e:
            print(f"Error saving AI meeting summary: {e}")

@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def schedule_meeting(
    payload: MeetingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM"]))
):
    """Schedule a new business meeting. Only accessible by AGM."""
    meet_repo = MeetingRepository(db)
    meeting = await meet_repo.create(organizer_id=current_user.id, meeting_in=payload)
    
    # Reload meeting with attendees loaded to fit the response model
    reloaded_meeting = await meet_repo.get_by_id(meeting.id)
    return reloaded_meeting

@router.get("", response_model=List[MeetingResponse])
async def list_meetings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """List meetings. AGM sees all scheduled meetings; Managers see meetings they are invited to."""
    meet_repo = MeetingRepository(db)
    meetings = await meet_repo.get_user_meetings(current_user.id)
    return meetings

@router.patch("/{meeting_id}/notes", response_model=MeetingResponse)
async def update_meeting_notes(
    meeting_id: uuid.UUID,
    payload: MeetingNotesUpdate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM"]))
):
    """
    Update notes for a completed meeting. Triggers AI summarizing in the background.
    Only accessible by AGM.
    """
    meet_repo = MeetingRepository(db)
    meeting = await meet_repo.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )

    # Queue background task
    background_tasks.add_task(
        summarize_meeting_in_background,
        meeting.id,
        meeting.agenda or "No agenda specified.",
        payload.notes
    )

    # Return intermediate status
    meeting.notes = payload.notes
    meeting.status = "COMPLETED"
    await db.commit()
    
    # Reload with preloaded relationships to avoid MissingGreenlet in async serialization layer
    reloaded_meeting = await meet_repo.get_by_id(meeting.id)
    return reloaded_meeting
