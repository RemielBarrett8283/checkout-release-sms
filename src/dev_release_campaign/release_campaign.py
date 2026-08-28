from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Protocol

try:
    from pydantic import BaseModel, Field
except ModuleNotFoundError:
    BaseModel = None  # type: ignore[assignment,misc]


if BaseModel is not None:
    class BuildEvent(BaseModel):
        build_id: str = Field(min_length=1)
        environment: str = Field(min_length=1)
        version: str = Field(min_length=1)
        summary: str = Field(min_length=1, max_length=120)


    class DeveloperRecipient(BaseModel):
        developer_id: str = Field(min_length=1)
        phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
        environment: str = Field(min_length=1)
        sms_opt_in: bool


    class ReleaseCampaignRequest(BaseModel):
        release_id: str = Field(min_length=1)
        build: BuildEvent
        recipients: list[DeveloperRecipient] = Field(min_length=1, max_length=100)


    class MessageDiagnostic(BaseModel):
        developer_id: str
        message_id: str
        status: str


    class CampaignResult(BaseModel):
        release_id: str
        build_id: str
        selected: int
        excluded: int
        messages: list[MessageDiagnostic]
else:
    class _FallbackModel:
        def model_dump_json(self, *, indent: int | None = None) -> str:
            return json.dumps(asdict(self), indent=indent)


    @dataclass
    class BuildEvent(_FallbackModel):
        build_id: str
        environment: str
        version: str
        summary: str


    @dataclass
    class DeveloperRecipient(_FallbackModel):
        developer_id: str
        phone: str
        environment: str
        sms_opt_in: bool


    @dataclass
    class ReleaseCampaignRequest(_FallbackModel):
        release_id: str
        build: BuildEvent
        recipients: list[DeveloperRecipient]

        @classmethod
        def model_validate(cls, value: Mapping[str, Any]) -> ReleaseCampaignRequest:
            return cls(
                release_id=str(value["release_id"]),
                build=BuildEvent(**value["build"]),
                recipients=[DeveloperRecipient(**item) for item in value["recipients"]],
            )


    @dataclass
    class MessageDiagnostic(_FallbackModel):
        developer_id: str
        message_id: str
        status: str


    @dataclass
    class CampaignResult(_FallbackModel):
        release_id: str
        build_id: str
        selected: int
        excluded: int
        messages: list[MessageDiagnostic]


class SmsGateway(Protocol):
    def send(self, *, to: str, body: str, idempotency_key: str) -> Mapping[str, Any]:
        raise AssertionError("protocol-only method")

    def status(self, message_id: str) -> Mapping[str, Any]:
        raise AssertionError("protocol-only method")


class ReleaseCampaign:
    def __init__(self, sms: SmsGateway) -> None:
        self.sms = sms

    def run(self, request: ReleaseCampaignRequest) -> CampaignResult:
        selected = [
            recipient
            for recipient in request.recipients
            if recipient.sms_opt_in
            and recipient.environment == request.build.environment
        ]
        message = (
            f"Build {request.build.build_id} ({request.build.version}) "
            f"is ready: {request.build.summary}"
        )
        diagnostics: list[MessageDiagnostic] = []
        for recipient in selected:
            sent = self.sms.send(
                to=recipient.phone,
                body=message,
                idempotency_key=(
                    f"release:{request.release_id}:developer:{recipient.developer_id}"
                ),
            )
            message_id = str(sent["message_id"])
            delivery = self.sms.status(message_id)
            diagnostics.append(
                MessageDiagnostic(
                    developer_id=recipient.developer_id,
                    message_id=message_id,
                    status=str(delivery["status"]),
                )
            )

        return CampaignResult(
            release_id=request.release_id,
            build_id=request.build.build_id,
            selected=len(selected),
            excluded=len(request.recipients) - len(selected),
            messages=diagnostics,
        )
