from app.db.base_class import Base

# Import all models here so that Alembic's target_metadata can discover them.
from app.models.branch import Branch
from app.models.user import User
from app.models.report import DailyReport
from app.models.document import Document, DocumentChunk
from app.models.meeting import Meeting, meeting_attendees
from app.models.task import Task
from app.models.notification import Notification
from app.models.conversation import AIConversation, AIMessage
from app.models.audit import AuditLog
from app.models.ai_memory import AIMemory
from app.models.employee import Employee
from app.models.employee_performance import EmployeePerformance
from app.models.scheme_summary import SchemeSummary
