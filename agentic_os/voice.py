from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from .logging import get_logger
from voice_agent import get_voice_agent


logger = get_logger(__name__)
router = APIRouter()


@router.post("/api/voice/process")
async def process_voice(request: Request):
    try:
        data = await request.json()
        audio_base64 = data.get("audio")
        audio_format = data.get("format", "webm")

        if not audio_base64:
            raise HTTPException(status_code=400, detail="No audio data provided")

        audio_bytes = base64.b64decode(audio_base64)

        agent = get_voice_agent()
        result = await agent.process_voice_input(audio_bytes, audio_format)

        return result
    except Exception as exc:
        logger.error("Voice processing error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing voice: {str(exc)}")


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Voice WebSocket connection established")

    try:
        agent = get_voice_agent()

        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "audio":
                audio_base64 = message.get("audio")
                audio_format = message.get("format", "webm")

                if not audio_base64:
                    await websocket.send_json({"type": "error", "error": "No audio data provided"})
                    continue

                await websocket.send_json({"type": "processing", "status": "transcribing"})

                audio_bytes = base64.b64decode(audio_base64)

                transcription = await agent.transcribe_audio(audio_bytes, audio_format)

                if not transcription:
                    await websocket.send_json({"type": "error", "error": "Could not transcribe audio"})
                    continue

                await websocket.send_json({"type": "transcription", "text": transcription})
                await websocket.send_json({"type": "processing", "status": "thinking"})

                response_text = ""
                async for chunk in agent.stream_llm_response(transcription):
                    response_text += chunk
                    await websocket.send_json({"type": "response_chunk", "chunk": chunk})

                await websocket.send_json({"type": "processing", "status": "speaking"})

                response_audio = await agent.synthesize_speech(response_text)

                if response_audio:
                    audio_base64 = base64.b64encode(response_audio).decode("utf-8")
                    await websocket.send_json(
                        {
                            "type": "audio_response",
                            "audio": audio_base64,
                            "format": "mp3",
                            "text": response_text,
                        }
                    )
                else:
                    await websocket.send_json({"type": "error", "error": "Failed to synthesize speech"})

                await websocket.send_json({
                    "type": "complete",
                    "transcription": transcription,
                    "response": response_text,
                })

            elif message_type == "clear_history":
                agent.clear_history(keep_system_prompt=True)
                await websocket.send_json({"type": "history_cleared", "message": "Conversation history cleared"})

            elif message_type == "get_history":
                history = agent.get_conversation_summary()
                await websocket.send_json({"type": "history", "data": history})

            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json({"type": "error", "error": f"Unknown message type: {message_type}"})

    except WebSocketDisconnect:
        logger.info("Voice WebSocket connection closed")
    except Exception as exc:
        logger.error("Voice WebSocket error: %s", exc, exc_info=True)
        try:
            await websocket.send_json({"type": "error", "error": str(exc)})
        except Exception:
            pass


@router.post("/api/voice/synthesize")
async def synthesize_speech(request: Request):
    try:
        data = await request.json()
        text = data.get("text")

        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        agent = get_voice_agent()
        audio_bytes = await agent.synthesize_speech(text)

        if not audio_bytes:
            raise HTTPException(status_code=500, detail="Failed to synthesize speech")

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {"audio": audio_base64, "format": "mp3", "text": text}

    except Exception as exc:
        logger.error("TTS error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error synthesizing speech: {str(exc)}")


@router.post("/api/voice/transcribe")
async def transcribe_audio_endpoint(request: Request):
    try:
        data = await request.json()
        audio_base64 = data.get("audio")
        audio_format = data.get("format", "webm")

        if not audio_base64:
            raise HTTPException(status_code=400, detail="No audio data provided")

        audio_bytes = base64.b64decode(audio_base64)

        agent = get_voice_agent()
        transcription = await agent.transcribe_audio(audio_bytes, audio_format)

        if not transcription:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")

        return {"transcription": transcription}

    except Exception as exc:
        logger.error("STT error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(exc)}")


@router.get("/api/voice/conversation")
async def get_conversation():
    try:
        agent = get_voice_agent()
        history = agent.get_conversation_summary()

        return {"history": history, "count": len(history)}
    except Exception as exc:
        logger.error("Error getting conversation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/api/voice/conversation")
async def clear_conversation():
    try:
        agent = get_voice_agent()
        agent.clear_history(keep_system_prompt=True)

        return {"message": "Conversation history cleared", "success": True}
    except Exception as exc:
        logger.error("Error clearing conversation: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
