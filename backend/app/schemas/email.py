from pydantic import BaseModel, Field

class EmailGenerationRequest(BaseModel):
    template_type: str = Field(..., description="MEETING_INVITE, MEETING_FOLLOWUP, TASK_REMINDER, or GENERAL_ANNOUNCEMENT")
    context: str = Field(..., description="Key facts, details, or notes to include in the email draft")

class EmailResponse(BaseModel):
    subject: str
    body: str
