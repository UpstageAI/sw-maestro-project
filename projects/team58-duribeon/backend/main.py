import logging
import os
import traceback

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("duribeon").setLevel(logging.INFO)

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import (
    detect_language,
    generate_missions,
    regenerate_mission_for_place,
    verify_photo,
)
from schemas import Context, Mission
from seed import load_areas


app = FastAPI(title="두리번 API", version="0.1.0")

origins_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    area: str
    group: str
    time_budget: str = ""
    mood: str = ""
    avoid: str = ""
    language: str = "ko"
    rejected_place_ids: list[str] = Field(default_factory=list)


class RegenerateRequest(BaseModel):
    area: str
    group: str
    time_budget: str = ""
    mood: str = ""
    avoid: str = ""
    language: str = "ko"
    place_id: str
    previous_title: str | None = None


class DetectRequest(BaseModel):
    text: str


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "upstage_key": bool(os.getenv("UPSTAGE_API_KEY")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/api/areas")
def api_areas():
    """Return curated areas from the seed JSON.
    Adding a new area = appending to data/seoul_seed.json — no code change."""
    return {"areas": load_areas()}


@app.post("/api/lang/detect")
def api_detect(req: DetectRequest):
    return {"language": detect_language(req.text)}


@app.post("/api/missions/generate")
def api_generate(req: GenerateRequest):
    try:
        ctx = Context(
            area=req.area,
            group=req.group,
            time_budget=req.time_budget,
            mood=req.mood or "balanced",
            avoid=req.avoid,
            language=req.language,
        )
        missions, candidates = generate_missions(ctx, req.rejected_place_ids)
        return {
            "missions": [m.model_dump() for m in missions],
            "candidate_count": len(candidates),
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/missions/regenerate")
def api_regenerate(req: RegenerateRequest):
    """Regenerate ONE mission for the SAME place. Used by the panel's
    "바꿔" (reroll) button — keeps place_id, swaps mission text only."""
    try:
        ctx = Context(
            area=req.area,
            group=req.group,
            time_budget=req.time_budget,
            mood=req.mood or "balanced",
            avoid=req.avoid,
            language=req.language,
        )
        mission = regenerate_mission_for_place(ctx, req.place_id, req.previous_title)
        return {"mission": mission.model_dump()}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


@app.post("/api/missions/verify")
async def api_verify(
    photo: UploadFile = File(...),
    mission_json: str = Form(...),
    language: str = Form("ko"),
):
    try:
        mission = Mission.model_validate_json(mission_json)
        image_bytes = await photo.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="empty photo upload")
        verdict = verify_photo(image_bytes, mission, language)
        return verdict.model_dump()
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
