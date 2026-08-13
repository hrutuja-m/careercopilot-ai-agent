from fastapi import APIRouter, File, HTTPException, UploadFile
from services.profile_store import get_profile, update_profile_from_resume

router = APIRouter()


@router.get("/")
def get_resume_profile():
    return {
        "message": "Resume profile loaded successfully",
        "resume_profile": get_profile(),
    }


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF resume.")

    contents = await file.read()
    if len(contents) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF must be smaller than 8 MB.")

    try:
        profile = update_profile_from_resume(contents, file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}") from exc

    return {
        "message": "Resume parsed and profile updated",
        "resume_profile": profile,
    }
