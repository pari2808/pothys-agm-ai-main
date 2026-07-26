from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import check_role
from app.models.user import User
from app.schemas.email import EmailGenerationRequest, EmailResponse
from app.services.rag_engine import rag_engine

router = APIRouter()

@router.post("/generate", response_model=EmailResponse)
async def generate_email_draft(
    payload: EmailGenerationRequest,
    current_user: User = Depends(check_role(["AGM"]))
):
    """
    Generate professional email drafts using OpenAI.
    Only accessible by the AGM to draft announcements, reminders, and follow-ups.
    """
    # 1. Enforce domain keyword guardrail
    if not rag_engine.is_query_in_domain(payload.context):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="As the Pothys AGM AI Assistant, my operations are restricted to Pothys business operations. I cannot assist with external queries."
        )

    system_instruction = (
        "You are the \"Pothys AGM AI Executive Assistant\", an enterprise AI built for the Assistant General Manager (AGM) of Pothys Swarna Mahal.\n\n"
        "Your task is to write a highly professional, polite, and grammatically correct email from the AGM of Pothys Swarna Mahal. "
        "The email must strictly relate to Pothys business operations, branches, managers, tasks, or meetings.\n\n"
        "Please format the output in JSON format with exactly two keys: \"subject\" and \"body\". "
        "The body should use professional email formatting with proper greetings and sign-offs. "
        "Do not output markdown code blocks or formatting other than a raw JSON block."
    )

    user_prompt = f"TEMPLATE TYPE: {payload.template_type}\nCONTEXT AND FACTS: {payload.context}"

    if rag_engine.client:
        try:
            import json
            response = rag_engine.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            email_data = json.loads(response.choices[0].message.content)
            return EmailResponse(
                subject=email_data.get("subject", "Pothys Operations Update"),
                body=email_data.get("body", "Please review the attached notes.")
            )
        except Exception as e:
            print(f"Failed to generate email via OpenAI: {e}")
            # Fall through to mock
            
    # Mock template builder for local development
    t_type = payload.template_type.upper()
    if "INVITE" in t_type:
        subject = "Invitation to Scheduled Pothys Swarna Mahal Operations Meeting"
        body = (
            f"Dear Team,\n\n"
            f"Please accept this invitation to attend our upcoming review meeting.\n"
            f"Context details: {payload.context}\n\n"
            f"Regards,\nAGM Swarna Mahal\nPothys Corporate"
        )
    elif "REMINDER" in t_type:
        subject = "Action Required: Pending Operational Tasks Notification"
        body = (
            f"Dear Branch Manager,\n\n"
            f"This is a formal reminder regarding your assigned duties.\n"
            f"Details: {payload.context}\n"
            f"Please update the task status in the mobile assistant app as soon as possible.\n\n"
            f"Regards,\nAGM Swarna Mahal\nPothys Corporate"
        )
    else:
        subject = "Pothys Swarna Mahal Management Announcement"
        body = (
            f"Dear Team,\n\n"
            f"Please find the latest management announcement below:\n"
            f"Context: {payload.context}\n\n"
            f"Best regards,\nAGM Swarna Mahal\nPothys Corporate"
        )

    return EmailResponse(subject=subject, body=body)
