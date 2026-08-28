from __future__ import annotations

from typing import Any, Mapping

from dev_release_campaign.release_campaign import ReleaseCampaign, ReleaseCampaignRequest


class RecordingSmsGateway:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, *, to: str, body: str, idempotency_key: str) -> Mapping[str, Any]:
        self.sent.append(
            {"to": to, "body": body, "idempotency_key": idempotency_key}
        )
        return {"message_id": f"msg-{len(self.sent)}"}

    def status(self, message_id: str) -> Mapping[str, Any]:
        return {"message_id": message_id, "status": "queued"}


def test_campaign_targets_opted_in_developers_for_the_build_environment() -> None:
    gateway = RecordingSmsGateway()
    request = ReleaseCampaignRequest.model_validate(
        {
            "release_id": "checkout-2026-08-27",
            "build": {
                "build_id": "build-1842",
                "environment": "production",
                "version": "checkout-api@4.8.0",
                "summary": "payment diagnostics include gateway request IDs",
            },
            "recipients": [
                {
                    "developer_id": "storefront-oncall",
                    "phone": "+14155550120",
                    "environment": "production",
                    "sms_opt_in": True,
                },
                {
                    "developer_id": "preview-builder",
                    "phone": "+14155550121",
                    "environment": "preview",
                    "sms_opt_in": True,
                },
                {
                    "developer_id": "checkout-observer",
                    "phone": "+14155550122",
                    "environment": "production",
                    "sms_opt_in": False,
                },
            ],
        }
    )

    result = ReleaseCampaign(gateway).run(request)

    assert result.selected == 1
    assert result.excluded == 2
    assert result.messages[0].status == "queued"
    assert gateway.sent == [
        {
            "to": "+14155550120",
            "body": (
                "Build build-1842 (checkout-api@4.8.0) is ready: "
                "payment diagnostics include gateway request IDs"
            ),
            "idempotency_key": (
                "release:checkout-2026-08-27:developer:storefront-oncall"
            ),
        }
    ]
