from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import build_runner, APP_NAME
from google.genai import types

# Validate required env vars at startup — fail loud, fail early
for key in ("GOOGLE_API_KEY", "DATABASE_URL"):
    if not os.getenv(key):
        raise RuntimeError(f"Missing required environment variable: {key}")

app = FastAPI()

FRONTEND_URL = os.getenv("FRONTEND_URL", "*")  # Set this in Railway later

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = build_runner(os.environ["DATABASE_URL"])
USER_ID = "default"


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/session")
async def create_session(session_id: str):
    svc = runner.session_service
    try:
        session = await svc.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
    except Exception:
        session = await svc.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
    return {"session_id": session.id}


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    content = types.Content(role="user", parts=[types.Part(text=req.message)])

    async def generate():
        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=req.session_id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    text = event.content.parts[0].text
                    if text and text.strip() not in ("", "None"):
                        yield f"data: {text}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}