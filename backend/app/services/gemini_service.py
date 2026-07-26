import json
from datetime import date
import logging
import asyncio
from typing import Optional, Any, Dict, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_SYSTEM_PROMPT = (
    "You are the Executive AI Assistant for the AGM of Pothys Swarna Mahal.\n\n"
    "Your responsibility is ONLY to explain business data already provided. "
    "Do NOT invent or extrapolate any business numbers, revenue, attendance, or meetings. "
    "If the database results are empty or missing, politely explain that the data is not available.\n\n"
    "CRITICAL RULE: You MUST ONLY use the exact data returned by the tools. "
    "NEVER fabricate, estimate, or assume any numbers, branch names, or statuses. "
    "If a branch shows status NOT_SUBMITTED, state that the branch has not submitted a report. "
    "Do NOT invent data for branches that have not submitted reports.\n\n"
    "CRITICAL UNIT FORMATTING RULES:\n"
    "- Always display Gold weight in grams (e.g. 1480 g)\n"
    "- Always display Diamond weight in carats (e.g. 105 ct)\n"
    "- Always display Platinum weight in grams (e.g. 320 g)\n"
    "- Always display Silver weight in grams (e.g. 400 g)\n"
    "- Always display Silver MRP and monetary revenue in Indian Rupees with Rs. symbol (e.g. Rs. 5.10L)\n"
    "- Never prefix Gold, Diamond, Platinum, or Silver weight with currency symbols like Rs.\n\n"
    "CRITICAL: Do NOT use ANY Markdown formatting in your response. "
    "Do not use asterisks (e.g. **bold**), hashtags/headers (e.g. ### Header), markdown tables, bullet points, lists, or blockquotes. "
    "Provide plain, natural, professional executive text formatted in clean, professional paragraphs or plain-text bullet items (using standard characters like '-' or simple newlines if needed, but never markdown tags).\n\n"
    "Never mention JSON, SQL, schemas, keys, or internal database fields. "
    "Write concise, executive-level business English responses."
)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_PRIMARY_MODEL = "llama-3.1-8b-instant"
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"

import traceback
import sys


def _safe_print(msg: str) -> None:
    """Print safely on Windows cp1252 terminals."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode(sys.stdout.encoding or 'utf-8', errors='replace').decode(sys.stdout.encoding or 'utf-8', errors='replace'))


def _gemini_text_response(text: str) -> Dict[str, Any]:
    """Wrap a plain text response into Gemini-compatible response shape."""
    return {
        "candidates": [{
            "content": {
                "parts": [{"text": text}],
                "role": "model"
            },
            "finishReason": "STOP"
        }]
    }


def _gemini_function_response(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap a function call into Gemini-compatible response shape."""
    return {
        "candidates": [{
            "content": {
                "parts": [{"functionCall": {"name": name, "args": args}}],
                "role": "model"
            },
            "finishReason": "STOP"
        }]
    }


def _openai_to_gemini_format(openai_resp: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAI-compatible chat completion response to Gemini-compatible shape."""
    choices = openai_resp.get("choices", [])
    if not choices:
        return {"candidates": []}

    message = choices[0].get("message", {})
    parts = []

    # Handle tool calls (function calls)
    tool_calls = message.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        raw_args = func.get("arguments", "{}")
        try:
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            args = {}
        parts.append({"functionCall": {"name": name, "args": args}})

    # Handle text content
    content = message.get("content")
    if content:
        parts.append({"text": content})

    if not parts:
        parts.append({"text": ""})

    return {
        "candidates": [{
            "content": {
                "parts": parts,
                "role": "model"
            },
            "finishReason": "STOP"
        }]
    }


def _parse_groq_json_response(openai_resp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract text from OpenAI-format response and parse as JSON."""
    choices = openai_resp.get("choices", [])
    if not choices:
        return None
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        return None
    text = content.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


class GeminiService:
    """
    Dedicated AI API Service (Groq / OpenAI-compatible backend).
    Transforms structured PostgreSQL JSON query results into professional executive responses.
    Does NOT query database directly or invent figures.
    Fails safely to deterministic fallback on quota limits, timeouts, or invalid keys.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.last_http_status: Optional[int] = None
        self.last_model_used: Optional[str] = None
        self.gemini_called_successfully: bool = False
        self.last_error: Optional[str] = None
        self.last_raw_response: Optional[str] = None
        self.last_request_prompt: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_openai_messages(
        self,
        system_prompt: str,
        user_content: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Build OpenAI-format messages list from system prompt and user content."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_content})
        return messages

    async def format_executive_response(
        self,
        user_query: str,
        structured_data: Dict[str, Any],
        max_retries: int = 1,
        timeout_seconds: float = 10.0
    ) -> Optional[str]:
        """
        Send user query and structured JSON payload to Groq API.
        Returns polished executive response text or None if API fails/quota exceeded.
        """
        if not self.api_key or self.api_key.startswith("mock"):
            logger.info("API key is not configured. Falling back to deterministic formatter.")
            return None

        data_json = json.dumps(structured_data, indent=2, default=str)
        user_prompt = f"User Request: {user_query}\n\nStructured Data Results:\n{data_json}"

        messages = self._build_openai_messages(GEMINI_SYSTEM_PROMPT, user_prompt)
        payload = {
            "model": GROQ_PRIMARY_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 600,
        }

        self.last_request_prompt = user_prompt

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            self.last_model_used = GROQ_PRIMARY_MODEL
            print(f"\n===== CALLING GROQ (format_executive_response) =====")
            print(f"Model: {GROQ_PRIMARY_MODEL}")
            _safe_print(f"Prompt (first 300 chars): {user_prompt[:300]}...")

            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(
                        GROQ_API_URL,
                        json=payload,
                        headers=self._get_headers(),
                    )
                    self.last_http_status = response.status_code
                    self.last_raw_response = response.text[:1000]

                    print(f"\n===== GROQ RESPONSE =====")
                    print(f"Status Code: {response.status_code}")
                    _safe_print(f"Response Body (first 500 chars):\n{response.text[:500]}")

                    if response.status_code == 200:
                        res_json = response.json()
                        choices = res_json.get("choices", [])
                        if choices:
                            text_resp = choices[0].get("message", {}).get("content", "").strip()
                            if text_resp:
                                self.gemini_called_successfully = True
                                self.last_error = None
                                return text_resp

                    elif response.status_code in (401, 403, 429):
                        err_msg = f"Groq API returned status {response.status_code}. Detail: {response.text[:200]}"
                        logger.warning(err_msg)
                        self.gemini_called_successfully = False
                        self.last_error = err_msg
                        return None
                    elif response.status_code == 400:
                        err_msg = f"Groq API returned status 400 (Bad Request). Detail: {response.text[:200]}"
                        logger.warning(err_msg)
                        self.last_error = err_msg
                        break
                    else:
                        err_msg = f"Groq API attempt {attempt+1} failed with status {response.status_code}: {response.text[:200]}"
                        logger.warning(err_msg)
                        self.last_error = err_msg

                except httpx.TimeoutException as te:
                    self.last_error = f"TimeoutException: {te}"
                    print(f"\n===== GROQ EXCEPTION =====")
                    traceback.print_exc()
                    logger.warning(f"Groq API request timed out after {timeout_seconds}s (attempt {attempt+1}).")
                except httpx.RequestError as req_err:
                    self.last_error = f"RequestError: {req_err}"
                    print(f"\n===== GROQ EXCEPTION =====")
                    traceback.print_exc()
                    logger.warning(f"Groq API request network error (attempt {attempt+1}): {req_err}")
                except Exception as e:
                    self.last_error = f"Exception: {e}"
                    print(f"\n===== GROQ EXCEPTION =====")
                    traceback.print_exc()
                    logger.error(f"Unexpected error calling Groq API: {e}", exc_info=True)
                    break

                if attempt < max_retries:
                    await asyncio.sleep(0.5)

        logger.warning("AI Service unable to format response. Returning None for deterministic fallback.")
        self.gemini_called_successfully = False
        return None

    async def extract_meeting_slots(self, chat_history: str) -> Dict[str, Any]:
        """
        Use Groq API to extract meeting parameters from chat history log.
        Returns a dict of extracted fields.
        """
        if not self.api_key or self.api_key.startswith("mock"):
            logger.info("API key is not configured or mock. Skipping slot extraction.")
            return {}

        today_str = date.today().strftime("%Y-%m-%d")
        extraction_prompt = (
            "You are a precise data extraction assistant. Analyze the conversation between the User (AGM) and the Assistant.\n"
            f"Today's date is {today_str}. Resolve relative dates (like 'tomorrow', 'next Monday') relative to this date.\n"
            "Extract the following meeting fields:\n"
            "- title: string or null (the topic or name of the meeting)\n"
            "- date: YYYY-MM-DD string or null\n"
            "- time: HH:MM string or null (24-hour format, parse e.g. '10am' to '10:00', '3:30 PM' to '15:30')\n"
            "- duration: integer minutes or null (convert hours, e.g. '1 hour' to 60, '1.5 hours' to 90)\n"
            "- participants: list of strings (names, emails, or roles like 'Padi manager', 'Chromepet manager' to invite)\n"
            "- branch: string or null (branch name associated with the meeting, if any)\n"
            "- notes: string or null (any additional context or agenda notes)\n\n"
            "Return ONLY a valid JSON object. Do not include markdown formatting, backticks, or explanations."
        )

        user_content = f"Conversation history:\n{chat_history}"
        messages = [{"role": "system", "content": extraction_prompt}, {"role": "user", "content": user_content}]
        payload = {
            "model": GROQ_PRIMARY_MODEL,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        for attempt in range(3):
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    response = await client.post(
                        GROQ_API_URL, json=payload, headers=self._get_headers()
                    )
                    if response.status_code == 200:
                        result = _parse_groq_json_response(response.json())
                        if result:
                            print(f"[MEETING_EXTRACT] Extracted slots (attempt {attempt+1}): {result}")
                            return result
                    elif response.status_code == 429:
                        wait = 2 ** attempt
                        print(f"[MEETING_EXTRACT] Rate limited (attempt {attempt+1}), waiting {wait}s...")
                        import asyncio
                        await asyncio.sleep(wait)
                        continue
                    else:
                        print(f"[MEETING_EXTRACT] Groq returned status {response.status_code}: {response.text[:200]}")
                        break
                except Exception as e:
                    logger.warning(f"Failed to extract meeting slots from Groq (attempt {attempt+1}): {e}")
                    import asyncio
                    await asyncio.sleep(1)
        print(f"[MEETING_EXTRACT] All attempts failed — returning empty dict")
        return {}

    async def extract_query_slots(self, query: str) -> Optional[dict]:
        """
        Use Groq API to classify the intent and extract slots (branch, metrics, time, etc.) from the query.
        Returns a dict of extracted slots or None on API failure.
        """
        if not self.api_key or self.api_key.startswith("mock"):
            logger.info("API key is not configured or mock. Skipping general slot extraction.")
            return None

        today_str = date.today().strftime("%Y-%m-%d")
        prompt = (
            "You are a precise intent classification and slot extraction assistant for the Pothys AGM AI Assistant.\n"
            f"Today's date is {today_str}. Resolve relative dates (like 'yesterday', 'today', 'last Monday') relative to this date.\n\n"
            "Analyze the User query and return a valid JSON object with the following fields:\n"
            "1. 'category': One of 'BUSINESS', 'KNOWLEDGE', 'STATIC'\n"
            "2. 'intent': Must be one of these standard intents:\n"
            "   - 'GET_BRANCH_REPORT' (if requesting the full Daily/Operations report or status for a branch, e.g. 'Padi report', 'Padi summary')\n"
            "   - 'GET_BRANCH_REVENUE' (if requesting revenue or sales amount for a branch or overall, e.g. 'Poonamallee revenue', 'Total revenue today')\n"
            "   - 'GET_GOLD_SALES' (if requesting gold sales/revenue, e.g. 'Gold sales in Poonamallee', 'Poonamallee gold sales')\n"
            "   - 'GET_SILVER_SALES' (if requesting silver sales/revenue, e.g. 'Silver sales today')\n"
            "   - 'GET_ATTENDANCE' (if requesting staff attendance, absentees, present count, e.g. 'Attendance in Poonamallee', 'Total absentees today')\n"
            "   - 'GET_PENDING_REPORTS' (if requesting which branches have NOT submitted today's/yesterday's report, e.g. 'Pending reports')\n"
            "   - 'GET_TOP_BRANCH' (if requesting the highest performing/revenue branch, e.g. 'Highest revenue today', 'Top branch')\n"
            "   - 'GET_TOP_EXECUTIVE' (if requesting the best performing employee or salesperson, e.g. 'Highest performing executive', 'Top performer')\n"
            "   - 'COMPARE_BRANCHES' (if comparing metrics/reports of multiple branches, e.g. 'Compare Padi and Chromepet', 'Padi vs Chromepet')\n"
            "   - 'CREATE_MEETING' (if requesting to schedule/arrange/create a meeting or 'Schedule my agenda', e.g. 'Create a meeting')\n"
            "   - 'UPDATE_MEETING' (if requesting to update/reschedule/edit a meeting)\n"
            "   - 'DELETE_MEETING' (if requesting to cancel/delete/remove a meeting)\n"
            "   - 'SHOW_TODAYS_AGENDA' (if asking for today's agenda, meetings, or tasks, e.g. 'What is my agenda today?')\n"
            "   - 'SHOW_ALERTS' (if asking for complaints, alerts, e.g. 'Show alerts', 'Total complaints today')\n"
            "   - 'SHOW_OPERATIONAL_ISSUES' (if asking for operational issues, e.g. 'Show operational issues today')\n"
            "   - 'DOCUMENT_QUERY' (if asking about general policies, SOPs, manuals, training documents, guidelines, or gold necklace shortage RAG queries)\n"
            "   - 'GREETING', 'HELP', 'IDENTITY', 'OUT_OF_DOMAIN'\n"
            "3. 'branches': list of canonical branch names detected in the query. Must only be from: ['Padi', 'Chromepet', 'Poonamallee', 'Coimbatore', 'Salem', 'Trichy', 'Tirunelveli', 'Trivandrum']. For example: ['Padi', 'Coimbatore'].\n"
            "4. 'metrics': list of specific metrics requested. Can include one or more of: ['gold_sales', 'silver_sales', 'total_revenue', 'attendance', 'complaints', 'issues', 'remarks', 'digigold']. For example, if user asks 'Give only the gold and silver sales', return ['gold_sales', 'silver_sales'].\n"
            "5. 'time': resolved date context in YYYY-MM-DD or 'today' or 'yesterday' (e.g. '2026-07-16').\n\n"
            "Return ONLY a valid JSON object. Do not include markdown block formatting, backticks, or other text."
        )

        messages = [{"role": "system", "content": prompt}, {"role": "user", "content": f"User query: {query}"}]
        payload = {
            "model": GROQ_PRIMARY_MODEL,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        self.last_model_used = GROQ_PRIMARY_MODEL
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    GROQ_API_URL, json=payload, headers=self._get_headers()
                )
                self.last_http_status = response.status_code
                self.last_raw_response = response.text[:1000]

                if response.status_code == 200:
                    self.gemini_called_successfully = True
                    result = _parse_groq_json_response(response.json())
                    return result
            except Exception as e:
                logger.warning(f"Failed to extract slots from Groq: {e}")
        return None

    async def debug_direct_call(self, prompt: str = "Reply with exactly: AI is working.") -> Dict[str, Any]:
        """
        Direct debug call to Groq without intent detection or fallbacks.
        """
        if not self.api_key:
            return {"error": "API key is missing", "status_code": None}

        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": GROQ_PRIMARY_MODEL,
            "messages": messages,
        }
        self.last_model_used = GROQ_PRIMARY_MODEL

        _safe_print(f"\n===== CALLING GROQ (DEBUG ENDPOINT) =====")
        _safe_print(f"Model: {GROQ_PRIMARY_MODEL}")
        _safe_print(f"Prompt: {prompt}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    GROQ_API_URL, json=payload, headers=self._get_headers()
                )
                self.last_http_status = response.status_code
                self.last_raw_response = response.text

                print(f"\n===== GROQ RESPONSE (DEBUG ENDPOINT) =====")
                print(f"Status Code: {response.status_code}")
                _safe_print(f"Response Body:\n{response.text}")

                if response.status_code == 200:
                    self.gemini_called_successfully = True
                    # Return in a format compatible with the consumer
                    return {
                        "status_code": 200,
                        "model": GROQ_PRIMARY_MODEL,
                        "response": response.json()
                    }
                else:
                    self.gemini_called_successfully = False
                    self.last_error = response.text
                    return {
                        "status_code": response.status_code,
                        "model": GROQ_PRIMARY_MODEL,
                        "error_body": response.text
                    }
        except Exception as e:
            print(f"\n===== GROQ EXCEPTION (DEBUG ENDPOINT) =====")
            traceback.print_exc()
            self.gemini_called_successfully = False
            self.last_error = str(e)
            return {
                "status_code": 500,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

    async def chat_with_gemini(
        self,
        chat_history: List[Dict[str, str]],
        max_retries: int = 1,
        timeout_seconds: float = 12.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send conversation history to Groq with tool definitions.
        Returns response in Gemini-compatible shape so downstream consumers don't break.
        Returns None if API fails/quota exceeded.
        """
        if not self.api_key or self.api_key.startswith("mock"):
            logger.info("API key is not configured. Skipping AI tool call.")
            return None

        # Build OpenAI-format messages from chat history
        messages = [{"role": "system", "content": GEMINI_SYSTEM_PROMPT}]
        for msg in chat_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Skip function response/call messages in history (OpenAI handles tool results differently)
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_business_data",
                    "description": (
                        "Retrieve business performance data (revenue, sales, attendance, complaints, remarks, operational issues, top performers, top branches) for branches. "
                        "Use this tool to show today's agenda, alerts, complaints, or operational issues. "
                        "Also use this tool to CREATE, UPDATE, or DELETE meetings when the user explicitly asks to schedule/arrange/create/reschedule/cancel a meeting. "
                        "IMPORTANT: 'add meeting', 'schedule meeting', 'create meeting', 'arrange a meeting' = CREATE_MEETING intent. "
                        "'show agenda', 'what's on my schedule' = SHOW_TODAYS_AGENDA intent. "
                        "Use this tool whenever the user asks for sales, revenue, attendance, reports, alerts, "
                        "meetings, scheduling, agenda, top performers, or branch comparisons. "
                        "ALWAYS call this tool for ANY business-related query, including meeting scheduling. "
                        "Only skip this tool for pure greetings, help requests, or out-of-domain questions like jokes or weather."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "queries": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "intent": {
                                            "type": "string",
                                            "description": (
                                                "The business data intent. Must be one of: "
                                                "GET_BRANCH_REPORT, GET_BRANCH_REVENUE, GET_GOLD_SALES, "
                                                "GET_SILVER_SALES, GET_ATTENDANCE, GET_PENDING_REPORTS, "
                                                "GET_TOP_BRANCH, GET_TOP_EXECUTIVE, COMPARE_BRANCHES, "
                                                "CREATE_MEETING, UPDATE_MEETING, DELETE_MEETING, "
                                                "SHOW_TODAYS_AGENDA, SHOW_ALERTS (for operational issues/alerts), "
                                                "SHOW_COMPLAINTS (for customer complaints), "
                                                "SHOW_OPERATIONAL_ISSUES"
                                            )
                                        },
                                        "branch": {
                                            "type": "string",
                                            "description": "Optional branch name (e.g., Padi, Coimbatore, Chromepet, Poonamallee, Salem, Trichy, Tirunelveli, Trivandrum)."
                                        },
                                        "time": {
                                            "type": "string",
                                            "description": "Optional resolved date or context (e.g., 'today', 'yesterday' or YYYY-MM-DD)."
                                        }
                                    },
                                    "required": ["intent"]
                                },
                                "description": "A list of data queries to retrieve."
                            }
                        },
                        "required": ["queries"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_knowledge_base",
                    "description": (
                        "Search policy documents, SOPs, training manuals, guidelines, and other corporate documents. "
                        "Use this tool to find information not found in daily reports (e.g. policies on refunds, exchanges, training, stock shortages)."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to retrieve relevant paragraphs from the policy documents."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        payload = {
            "model": GROQ_PRIMARY_MODEL,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0.2,
            "max_tokens": 800,
        }

        self.last_model_used = GROQ_PRIMARY_MODEL
        print(f"\n===== CALLING GROQ TOOL CHAT =====")
        print(f"Model: {GROQ_PRIMARY_MODEL}")

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.post(
                        GROQ_API_URL, json=payload, headers=self._get_headers()
                    )
                    self.last_http_status = response.status_code
                    self.last_raw_response = response.text[:1000]

                    print(f"\n===== GROQ TOOL CHAT RESPONSE =====")
                    print(f"Status Code: {response.status_code}")

                    if response.status_code == 200:
                        self.gemini_called_successfully = True
                        self.last_error = None
                        # Convert to Gemini-compatible format so ai.py consumer works unchanged
                        return _openai_to_gemini_format(response.json())

                    elif response.status_code in (401, 403, 429):
                        err_msg = f"Groq API returned status {response.status_code}. Detail: {response.text[:200]}"
                        logger.warning(err_msg)
                        self.gemini_called_successfully = False
                        self.last_error = err_msg
                        return None
                    else:
                        err_msg = f"Groq API attempt {attempt+1} failed with status {response.status_code}: {response.text[:200]}"
                        logger.warning(err_msg)
                        self.last_error = err_msg

                except Exception as e:
                    self.last_error = str(e)
                    logger.warning(f"Unexpected error in Groq tool call: {e}")
                    break

                if attempt < max_retries:
                    await asyncio.sleep(0.5)

        self.gemini_called_successfully = False
        return None


# Singleton instance
gemini_service = GeminiService()
