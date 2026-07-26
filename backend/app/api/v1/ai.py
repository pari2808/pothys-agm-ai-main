import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.db.session import get_db
from app.api.deps import get_current_user, check_role
from app.models.user import User
from app.models.conversation import AIMessage
from app.models.report import DailyReport
from app.models.document import Document, DocumentChunk
from app.repositories.conversation import ConversationRepository
from app.repositories.document import DocumentRepository
from app.schemas.ai import AIQueryRequest, AIMessageResponse, AIConversationResponse, AIConversationDetailResponse

# New architecture imports
from app.services.intent_classifier import (
    IntentClassifier, IntentCategory, StaticIntent,
    intent_classifier, BusinessIntent
)
from app.services.business_query_executor import business_executor

router = APIRouter()


def _safe_print(msg: str) -> None:
    """Print to terminal safely on Windows (cp1252) by replacing unencodable chars."""
    import sys
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))



# ─────────────────────────────────────────────
# Static Response Handlers
# ─────────────────────────────────────────────

def _get_static_response(intent: str) -> str:
    """Return hardcoded responses for static intents."""
    from datetime import datetime

    if intent == StaticIntent.OUT_OF_DOMAIN:
        return (
            "I am the Pothys AGM AI Assistant. My responses are restricted to Pothys business operations. "
            "I can only assist with branch operations, reports, meetings, sales and business insights."
        )
    elif intent == StaticIntent.IDENTITY:
        return (
            "I am the Pothys AGM AI Assistant. I assist AGM executives with branch operations, "
            "reports, meetings, sales insights and operational decision support."
        )
    elif intent == StaticIntent.GREETING:
        hour = datetime.now().hour
        time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        return f"Good {time_of_day}, Sir. How can I assist you today?"
    elif intent == StaticIntent.HELP:
        return (
            "I am the Pothys AGM AI Assistant. I can assist you with the following business queries:\n\n"
            "• **Reports**: Check today's report status across all branches.\n"
            "• **Branch Report**: View a specific branch's full daily report.\n"
            "• **Sales & Revenue**: Check today's sales or compare branches.\n"
            "• **Attendance**: Check how many staff members are present.\n"
            "• **Alerts**: Find today's operational alerts or issues.\n"
            "• **Complaints**: View customer complaints across branches.\n"
            "• **Remarks**: Get the latest remarks from branch managers.\n"
            "• **Meetings**: Retrieve scheduled corporate or branch meetings.\n"
            "• **Tasks**: Trace pending or completed action items.\n"
            "• **Top Performer**: Find today's highest performing executive.\n"
            "• **Top Branch**: Find the branch with the highest revenue."
        )
    elif intent == StaticIntent.ACKNOWLEDGMENT:
        return "Certainly, Sir. How can I help you next?"
    return "I'm sorry, I could not understand your query."


@router.post("/query", response_model=AIMessageResponse)
async def query_copilot(
    payload: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """
    AI Copilot Chat Query — Instrumented LLM-driven Tool Calling Architecture.
    """
    import time
    import traceback

    start_time = time.time()
    print(f"\n[DEBUG_CHAT] STAGE 1: Request received at {start_time}")
    print(f"[DEBUG_CHAT] STAGE 3: User message: {payload.content}")

    try:
        conv_repo = ConversationRepository(db)

        # 1. Resolve or create chat conversation thread
        stage_2_start = time.time()
        if payload.conversation_id:
            conversation = await conv_repo.get_conversation(payload.conversation_id)
            if not conversation or conversation.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation thread not found"
                )
        else:
            title = payload.content[:50] + "..." if len(payload.content) > 50 else payload.content
            conversation = await conv_repo.create_conversation(current_user.id, title)
        
        print(f"[DEBUG_CHAT] STAGE 2: Conversation ID resolved: {conversation.id} (took {time.time() - stage_2_start:.4f}s)")

        # Save user query message to DB
        save_msg_start = time.time()
        await conv_repo.create_message(
            conversation_id=conversation.id,
            role="user",
            content=payload.content
        )
        print(f"[DEBUG_CHAT] Saved user query message to DB (took {time.time() - save_msg_start:.4f}s)")

        # ── MEETING FLOW INTERCEPT ───────────────────────────────────────────
        # If there's an active meeting creation flow, skip Groq entirely and route
        # directly to the meeting handler. This prevents short words like "ok",
        # "no", "yes" from being misclassified as ACKNOWLEDGMENT/OUT_OF_DOMAIN.
        in_meeting_flow = False
        if conversation.id:
            from app.models.ai_memory import AIMemory
            state_key = f"meeting_creation_{conversation.id}"
            stmt_mf = select(AIMemory).where(AIMemory.key == state_key)
            res_mf = await db.execute(stmt_mf)
            _mem = res_mf.scalars().first()
            in_meeting_flow = _mem is not None
            if _mem:
                print(f"[DEBUG_CHAT] Meeting state found for key={state_key}, value={_mem.value}")
            else:
                print(f"[DEBUG_CHAT] No meeting state for key={state_key}")
        else:
            print(f"[DEBUG_CHAT] No conversation.id — cannot check meeting state")

        # Patterns for messages that should NOT be intercepted during meeting flow
        # (static intents like help/joke, knowledge queries like return policy)
        _SKIP_PATTERNS = (
            "help", "joke", "hello", "hi ", "hey", "thank", "bye",
            "what is", "what are", "how do", "how can", "tell me",
            "return policy", "refund", "exchange", "rule", "regulation",
        )
        _STATIC_FIRST_WORDS = {"help", "joke", "hello", "hi", "hey", "thanks", "thank", "bye", "goodbye", "tell"}

        if in_meeting_flow:
            # Only intercept messages that look like meeting-flow responses.
            # Skip static intents (help, joke, greeting) and knowledge queries (policy, return).
            _q_lower = payload.content.strip().lower()
            _words = _q_lower.split()
            _is_numeric = _q_lower.replace(".", "").replace(",", "").replace(" ", "").isdigit()

            _should_skip = any(_q_lower.startswith(p) or _q_lower == p.rstrip() for p in _SKIP_PATTERNS)
            # Also skip if the first word is a static-intent keyword
            if _words and _words[0] in _STATIC_FIRST_WORDS:
                _should_skip = True

            _is_short = len(_words) <= 5

            if not _should_skip and (_is_short or _is_numeric):
                print(f"[DEBUG_CHAT] Active meeting flow detected — routing directly to meeting handler")
                from app.services.intent_classifier import QuerySlots
                from app.services.business_query_executor import CreateMeetingHandler, _format_deterministic, strip_markdown
                from datetime import date as _date
                handler = CreateMeetingHandler()
                data_result = await handler.handle(
                    db=db,
                    slots=QuerySlots(intent=BusinessIntent.CREATE_MEETING, category=IntentCategory.BUSINESS, time="today"),
                    query=payload.content,
                    query_date=_date.today(),
                    date_label="today",
                    current_user=current_user,
                    conversation_id=conversation.id,
                )
                if isinstance(data_result, dict):
                    answer = strip_markdown(_format_deterministic(data_result))
                else:
                    answer = str(data_result) if data_result else ""

                assistant_msg = await conv_repo.create_message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=answer,
                )
                return AIMessageResponse(
                    id=assistant_msg.id,
                    conversation_id=conversation.id,
                    role="assistant",
                    content=answer,
                    retrieved_sources=[],
                    created_at=assistant_msg.created_at,
                )
            else:
                print(f"[DEBUG_CHAT] Meeting flow active but message is long/unrelated — continuing normal flow")

        # Fetch past messages to build history (cap to last 20 to stay within Groq token limits)
        history_start = time.time()
        db_messages = await db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation.id)
            .order_by(AIMessage.created_at.desc())
            .limit(20)
        )
        all_msgs = list(reversed(db_messages.scalars().all()))
        history = []
        for msg in all_msgs:
            history.append({"role": msg.role, "content": msg.content})
        
        print(f"[DEBUG_CHAT] STAGE 4: History length: {len(history)} (took {time.time() - history_start:.4f}s)")

        # Call Gemini first using chat_with_gemini
        from app.services.gemini_service import gemini_service
        
        print(f"[DEBUG_CHAT] STAGE 5: Gemini request started")
        gemini_start = time.time()
        res_json = await gemini_service.chat_with_gemini(history)
        print(f"[DEBUG_CHAT] STAGE 6: Gemini request completed (took {time.time() - gemini_start:.4f}s)")

        answer = ""
        citations = []

        if res_json and "candidates" in res_json and res_json["candidates"]:
            parts = res_json["candidates"][0]["content"].get("parts", [])
            function_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]

            if function_calls:
                # Check if this is a casual/acknowledgment phrase — skip tool execution
                # (Meeting flow is already intercepted above, so no conflict here)
                CASUAL_PHRASES = {
                    "okay", "ok", "done", "thanks", "thank you", "got it", "alright",
                    "cool", "nice", "great", "good", "superb", "perfect", "wonderful",
                    "fine", "noted", "understood", "sure", "yes", "yeah", "yep", "no",
                    "nope", "nah", "bye", "goodbye", "see you", "see ya",
                }
                from app.services.intent_classifier import IntentCategory as IC2
                local_cat2, local_int2, _ = await intent_classifier.classify_async(payload.content)
                if local_cat2 == IC2.STATIC:
                    print(f"[DEBUG_CHAT] Static intent ({local_int2}) detected, skipping tool execution")
                    answer = _get_static_response(local_int2)
                elif local_cat2 == IC2.KNOWLEDGE:
                    # Knowledge query — don't let Groq handle it with tools, route to RAG
                    print(f"[DEBUG_CHAT] Knowledge intent detected, skipping tool execution, routing to RAG")
                    answer = ""
                elif local_cat2 == IC2.OUT_OF_DOMAIN:
                    # Out-of-domain query — don't let Groq hallucinate business data
                    print(f"[DEBUG_CHAT] Out-of-domain intent detected, skipping tool execution")
                    answer = _get_static_response(local_int2)
                else:
                    # Execute tool calls requested by Groq
                    tool_results = []
                    for fc in function_calls:
                        name = fc.get("name")
                        args = fc.get("args") or {}

                        if name == "retrieve_business_data":
                            print(f"[DEBUG_CHAT] STAGE 7: SQL retrieval started")
                            sql_start = time.time()
                            queries = args.get("queries") or []

                            # Deduplicate queries by (intent, branch, time) to prevent repeated responses
                            seen_q = set()
                            deduped = []
                            for q in queries:
                                key = (q.get("intent"), q.get("branch"), q.get("time"))
                                if key not in seen_q:
                                    seen_q.add(key)
                                    deduped.append(q)

                            # Smart dedup: if GET_BRANCH_REPORT exists for a branch,
                            # skip sub-metric queries (revenue, gold, silver, attendance) for same branch
                            SUB_METRIC_INTENTS = {"GET_BRANCH_REVENUE", "GET_GOLD_SALES", "GET_SILVER_SALES", "GET_ATTENDANCE"}
                            report_branches = set()
                            for q in deduped:
                                if q.get("intent") == "GET_BRANCH_REPORT" and q.get("branch"):
                                    report_branches.add((q.get("branch"), q.get("time")))
                            smart_deduped = []
                            for q in deduped:
                                if q.get("intent") in SUB_METRIC_INTENTS and q.get("branch"):
                                    if (q.get("branch"), q.get("time")) in report_branches:
                                        print(f"[DEBUG_CHAT] Skipping {q.get('intent')} for {q.get('branch')} (full report already queried)")
                                        continue
                                smart_deduped.append(q)

                            # Safety net: if user message clearly asks to create/add/schedule a meeting
                            # but Groq called a different intent (e.g. SHOW_TODAYS_AGENDA), override to CREATE_MEETING
                            _msg_lower = payload.content.lower()
                            _meeting_create_kw = ("add meeting", "create meeting", "schedule meeting", "arrange meeting",
                                                   "set up meeting", "new meeting", "plan meeting", "book meeting")
                            if any(kw in _msg_lower for kw in _meeting_create_kw):
                                for q in smart_deduped:
                                    if q.get("intent") != "CREATE_MEETING":
                                        print(f"[DEBUG_CHAT] Override intent {q.get('intent')} -> CREATE_MEETING (user asked to schedule)")
                                        q["intent"] = "CREATE_MEETING"

                            if len(smart_deduped) < len(deduped):
                                print(f"[DEBUG_CHAT] Smart dedup: {len(deduped)} -> {len(smart_deduped)}")
                            queries = smart_deduped

                            results_list = []
                            for q in queries:
                                intent = q.get("intent")
                                branch = q.get("branch")
                                time_val = q.get("time")

                                if not branch:
                                    from app.services.intent_classifier import extract_branch_name
                                    branch = extract_branch_name(payload.content)

                                from app.services.intent_classifier import QuerySlots
                                slots = QuerySlots(
                                    intent=intent,
                                    category=IntentCategory.BUSINESS,
                                    branch=branch,
                                    branches=[branch] if branch else [],
                                    time=time_val or "today"
                                )

                                from datetime import date, timedelta
                                import re
                                query_date = date.today()
                                date_label = "today"
                                if slots.time == "yesterday":
                                    query_date = date.today() - timedelta(days=1)
                                    date_label = "yesterday"
                                elif slots.time and re.match(r"^\d{4}-\d{2}-\d{2}$", slots.time):
                                    query_date = date.fromisoformat(slots.time)
                                    date_label = slots.time

                                from app.services.business_query_executor import HANDLERS
                                handler = HANDLERS.get(intent)
                                if not handler:
                                    handler = HANDLERS.get(intent.replace("GET_", "").replace("SHOW_", ""))
                                if not handler:
                                    from app.services.business_query_executor import ShowTodaysAgendaHandler
                                    handler = ShowTodaysAgendaHandler()

                                data_result = await handler.handle(
                                    db=db,
                                    slots=slots,
                                    query=payload.content,
                                    query_date=query_date,
                                    date_label=date_label,
                                    current_user=current_user,
                                    conversation_id=conversation.id
                                )

                                results_list.append({
                                    "intent": intent,
                                    "branch": branch,
                                    "time": time_val,
                                    "data": data_result
                                })

                            tool_results.append({
                                "functionCall": fc,
                                "functionResponse": {
                                    "name": "retrieve_business_data",
                                    "response": {"output": {"results": results_list}}
                                }
                            })
                            print(f"[DEBUG_CHAT] STAGE 8: SQL retrieval completed (took {time.time() - sql_start:.4f}s)")

                        elif name == "search_knowledge_base":
                            print(f"[DEBUG_CHAT] RAG search started")
                            rag_start = time.time()
                            query_str = args.get("query")
                            from app.services.rag_engine import rag_engine
                            query_vector = await rag_engine.get_embedding(query_str)
                            doc_repo = DocumentRepository(db)
                            raw_chunks = await doc_repo.semantic_search(query_vector=query_vector, limit=8)

                            context_chunks = []
                            for chunk in raw_chunks:
                                if current_user.role == "MANAGER":
                                    if chunk.report_id:
                                        stmt = select(DailyReport).where(DailyReport.id == chunk.report_id)
                                        res = await db.execute(stmt)
                                        report = res.scalars().first()
                                        if report and report.branch_id != current_user.branch_id:
                                            continue
                                context_chunks.append(chunk.content)

                            tool_results.append({
                                "functionCall": fc,
                                "functionResponse": {
                                    "name": "search_knowledge_base",
                                    "response": {"output": {"chunks": context_chunks}}
                                }
                            })
                            print(f"[DEBUG_CHAT] RAG search completed (took {time.time() - rag_start:.4f}s)")

                    # Build follow-up chat history
                    follow_up_history = list(history)
                    for tr in tool_results:
                        follow_up_history.append({
                            "role": "assistant",
                            "functionCall": tr["functionCall"]
                        })
                        follow_up_history.append({
                            "role": "function",
                            "functionResponse": tr["functionResponse"]
                        })

                    # Format response deterministically from tool results
                    from app.services.business_query_executor import _format_deterministic, strip_markdown
                    answer_parts = []
                    for tr in tool_results:
                        resp_data = tr["functionResponse"].get("response", {}).get("output", {})
                        results = resp_data.get("results", [])
                        for r in results:
                            data = r.get("data")
                            if isinstance(data, dict):
                                formatted = _format_deterministic(data)
                                answer_parts.append(strip_markdown(formatted))
                            elif isinstance(data, str):
                                answer_parts.append(strip_markdown(data))
                    answer = "\n\n".join(answer_parts) if answer_parts else ""
            else:
                # No tools requested: check if this should have been a business query
                # Groq sometimes returns conversational text instead of calling the tool
                from app.services.intent_classifier import IntentCategory as IC

                local_category, local_intent, local_branch = await intent_classifier.classify_async(payload.content)
                if local_category == IC.BUSINESS:
                    print(f"[DEBUG_CHAT] Groq returned text but local classifier detected business intent: {local_intent}")
                    answer = ""
                elif local_category == IC.KNOWLEDGE:
                    # Don't trust Groq's text for knowledge queries — route to RAG fallback
                    print(f"[DEBUG_CHAT] Groq returned text but local classifier detected knowledge intent, routing to RAG")
                    answer = ""
                elif local_category == IC.STATIC:
                    answer = _get_static_response(local_intent)
                elif local_category == IC.OUT_OF_DOMAIN:
                    print(f"[DEBUG_CHAT] Out-of-domain intent detected in else path")
                    answer = _get_static_response(local_intent)
                elif parts and "text" in parts[0]:
                    answer = parts[0]["text"].strip()

        # Deterministic fallback / offline mock fallback
        if not answer:
            print(f"[DEBUG_CHAT] Entering offline / mock fallback routing")
            fallback_start = time.time()
            category, intent, branch_name = await intent_classifier.classify_async(payload.content)
            
            # Build pre-classified slots to avoid double Groq classification
            from app.services.intent_classifier import QuerySlots
            pre_slots = await intent_classifier.classify_slots_async(payload.content)
            
            # Check if meeting flow active — only override for short messages
            _words_fallback = payload.content.strip().split()
            _is_short_fallback = len(_words_fallback) <= 5
            _is_numeric_fallback = payload.content.strip().replace(".", "").replace(",", "").isdigit()

            # Skip meeting flow override for static/knowledge intents (help, joke, return policy, etc.)
            _fb_skip = any(payload.content.lower().startswith(p) or payload.content.lower() == p.rstrip() for p in _SKIP_PATTERNS)
            if _words_fallback and _words_fallback[0] in _STATIC_FIRST_WORDS:
                _fb_skip = True

            if conversation.id and not _fb_skip and (_is_short_fallback or _is_numeric_fallback):
                from app.models.ai_memory import AIMemory
                state_key = f"meeting_creation_{conversation.id}"
                stmt = select(AIMemory).where(AIMemory.key == state_key)
                res = await db.execute(stmt)
                mem = res.scalars().first()
                if mem:
                    category = IntentCategory.BUSINESS
                    intent = BusinessIntent.CREATE_MEETING

            # Safety net: if user message clearly asks to create/add/schedule a meeting
            _fb_msg_lower = payload.content.lower()
            _fb_meeting_kw = ("add meeting", "create meeting", "schedule meeting", "arrange meeting",
                              "set up meeting", "new meeting", "plan meeting", "book meeting")
            if any(kw in _fb_msg_lower for kw in _fb_meeting_kw):
                print(f"[DEBUG_CHAT] Fallback: meeting creation keywords detected, overriding intent to CREATE_MEETING")
                category = IntentCategory.BUSINESS
                intent = BusinessIntent.CREATE_MEETING
                pre_slots.intent = BusinessIntent.CREATE_MEETING

            if category == IntentCategory.STATIC:
                answer = _get_static_response(intent)
            elif category == IntentCategory.BUSINESS:
                answer = await business_executor.execute(
                    intent=intent,
                    query=payload.content,
                    db=db,
                    branch_name=branch_name,
                    current_user=current_user,
                    conversation_id=conversation.id,
                    pre_classified_slots=pre_slots,
                )
            elif category == IntentCategory.KNOWLEDGE:
                try:
                    from app.services.rag_engine import rag_engine
                    query_vector = await rag_engine.get_embedding(payload.content)

                    doc_repo = DocumentRepository(db)
                    raw_chunks = await doc_repo.semantic_search(query_vector=query_vector, limit=8)

                    context_chunks = []
                    for chunk in raw_chunks:
                        if current_user.role == "MANAGER":
                            if chunk.report_id:
                                stmt = select(DailyReport).where(DailyReport.id == chunk.report_id)
                                res = await db.execute(stmt)
                                report = res.scalars().first()
                                if report and report.branch_id != current_user.branch_id:
                                    continue
                        context_chunks.append(chunk.content)

                    chat_history = []
                    if payload.conversation_id:
                        db_messages = await db.execute(
                            select(AIMessage)
                            .where(AIMessage.conversation_id == conversation.id)
                            .order_by(AIMessage.created_at.asc())
                        )
                        for msg in db_messages.scalars().all():
                            chat_history.append({"role": msg.role, "content": msg.content})

                    answer, citations = await rag_engine.generate_response(
                        query=payload.content,
                        context_chunks=context_chunks,
                        chat_history=chat_history,
                    )
                except Exception as e:
                    print(f"[DEBUG_CHAT] RAG pipeline error: {e}")
                    traceback.print_exc()
                    answer = "I couldn't retrieve the requested information at the moment. Please try again."
            print(f"[DEBUG_CHAT] Offline / mock fallback finished (took {time.time() - fallback_start:.4f}s)")

        print(f"[DEBUG_CHAT] STAGE 9: Response generation completed")

        # Strip markdown from response
        from app.services.business_query_executor import strip_markdown
        answer = strip_markdown(answer)

        # Save assistant answer to DB
        save_assistant_start = time.time()
        assistant_msg = await conv_repo.create_message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            retrieved_sources=citations
        )
        print(f"[DEBUG_CHAT] Saved assistant message to DB (took {time.time() - save_assistant_start:.4f}s)")

        print(f"[DEBUG_CHAT] STAGE 10: Response returned. Total request execution time: {time.time() - start_time:.4f}s")
        return AIMessageResponse(
            id=assistant_msg.id,
            conversation_id=conversation.id,
            role="assistant",
            content=answer,
            retrieved_sources=citations,
            created_at=assistant_msg.created_at
        )

    except Exception as e:
        print(f"[DEBUG_CHAT] EXCEPTION OCCURRED:")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )



@router.get("/conversations", response_model=List[AIConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """Retrieve all chat threads started by the current user."""
    conv_repo = ConversationRepository(db)
    conversations = await conv_repo.get_user_conversations(current_user.id)
    return conversations


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetailResponse)
async def get_conversation_details(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """Fetch all messages inside a specific conversation thread."""
    conv_repo = ConversationRepository(db)
    conversation = await conv_repo.get_conversation(conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found"
        )
    return conversation


# ─────────────────────────────────────────────
# Debug Endpoints (Phase 1 Verification)
# ─────────────────────────────────────────────

@router.get("/debug-gemini")
async def debug_gemini():
    """
    Direct Gemini API test. Calls Gemini with a simple prompt
    without intent detection, database queries, or fallbacks.
    Returns the raw response or full error.
    """
    from app.services.gemini_service import gemini_service
    result = await gemini_service.debug_direct_call("Reply with exactly: Gemini is working.")
    status_code = result.get("status_code") or 500
    if status_code == 200:
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=status_code if isinstance(status_code, int) else 500)


@router.get("/debug-status")
async def debug_status(db: AsyncSession = Depends(get_db)):
    """
    Returns JSON status of database connectivity and Gemini service state.
    """
    from app.services.gemini_service import gemini_service

    # Check database connectivity
    db_connected = False
    try:
        await db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return JSONResponse(content={
        "database_connected": db_connected,
        "gemini_key_detected": bool(gemini_service.api_key and not gemini_service.api_key.startswith("mock")),
        "gemini_called_successfully": gemini_service.gemini_called_successfully,
        "last_http_status": gemini_service.last_http_status,
        "current_model": gemini_service.last_model_used,
        "last_error": gemini_service.last_error,
    })
