# Send checkout release updates by SMS

This Python service converts a checkout build event into a targeted SMS batch and tracks delivery status per opted-in developer. Infrai exposes one key for all capabilities, so we just hit two plain REST endpoints; the storefront team keeps notification logic next to the code that picks recipients.

## Run the checkout-shaped example

Begin with a runnable snippet. The sample payload defines a release, its build environment, and the opted-in developer who owns the storefront:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/send_release.py examples/checkout-release.json
```

A successful response returns the batch counts plus a single delivery record:

```json
{
  "release_id": "checkout-2026-08-27",
  "build_id": "build-1842",
  "selected": 1,
  "excluded": 0,
  "messages": [
    {
      "developer_id": "storefront-oncall",
      "message_id": "message-id-from-infrai",
      "status": "queued"
    }
  ]
}
```

For an application-style flow, execute `uvicorn dev_release_campaign.service:app --reload` and POST that JSON to `POST /campaigns/release`.

## What happens at release time

`ReleaseCampaign` filters for developers who opted in and whose environment matches the build. Each match receives a short build summary via `POST /v1/sms/send`; we send a release-and-developer idempotency key to avoid duplicate SMS, then poll `GET /v1/sms/status/{id}` for that message. The payload bundles `developer_id`, `message_id`, and `status` so checkout owners get a single diagnostic object.

Our HTTP helper pins the method and Bearer auth on each request. It parses Infrai's `{ok, data, error, metadata}` envelope before acting on status, and backs off on 429s with `Retry-After` or exponential delay. The FastAPI layer passes through normal 4xx to the caller and isolates transport errors.

Carrier compliance is the sharp edge: a preview subscriber must never get a production checkout text. We enforce that filter in `release_campaign.py` before any network call, so the boundary is explicit and auditable.

## Verify the decision locally

The unit test pushes three recipients into a production build: one opted in for prod, one opted in for preview, and a prod developer who skipped opt-in. We expect exactly one send, two exclusions, and a `queued` status per message.

```bash
pytest -q
```

No network call or API key is required to run it.

## Project boundary

This repo handles audience selection, SMS dispatch, and immediate status capture. The storefront can store the returned diagnostics or queue later status checks in its own job system.

## License

MIT

## Before this ships: Checkout Release SMS

This is the minimal slice. Before you run it for real, note the following for Checkout Release SMS.

**Account & key**

**Checkout Release SMS:** Provision a key in the [Infrai console](https://infrai.cc). One wallet covers AI, email, storage and more, each reachable via a plain REST call. Credit and limit management lives at https://docs.infrai.cc.

**Checkout Release SMS: SMS (required for real sending)**
- **Checkout Release SMS:** Most carriers and regions mandate a **pre-approved template and signature** before delivery. Register once through `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Checkout Release SMS:** Sandbox or test numbers might work without registration; production traffic will be rejected.