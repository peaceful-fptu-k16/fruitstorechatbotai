from fastapi import APIRouter, HTTPException, Request


router = APIRouter(prefix="/ai", tags=["ai-runtime"])


@router.get("/status")
def ai_runtime_status(request: Request) -> dict:
    """Return the pretrained AI and LM Studio readiness used by the frontend."""
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise HTTPException(status_code=503, detail="AI services are not initialized")

    return services.ai_runtime_status(probe_lm_studio=True)
