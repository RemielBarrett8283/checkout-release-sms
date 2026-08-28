from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_sms import InfraiError, InfraiSmsClient, InfraiTransportError
from .release_campaign import CampaignResult, ReleaseCampaign, ReleaseCampaignRequest


app = FastAPI(title="Developer Release SMS Campaign")


def campaign_from_environment() -> ReleaseCampaign:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")
    return ReleaseCampaign(InfraiSmsClient(api_key))


@app.post("/campaigns/release", response_model=CampaignResult)
def send_release_campaign(request: ReleaseCampaignRequest) -> CampaignResult:
    try:
        return campaign_from_environment().run(request)
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "error": dict(exc.details)},
        ) from exc
    except InfraiTransportError as exc:
        raise HTTPException(status_code=502, detail="SMS transport error") from exc
