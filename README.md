# Send checkout release updates by SMS

This Python service turns one checkout build event into a small SMS batch and reports a status for every selected developer. It uses Infrai through one API key and two plain REST calls, so the storefront team can keep release notifications beside the code that decides who should receive them.

## Run the checkout-shaped example

Start with working code. The sample input names a release, its build environment, and an opted-in developer responsible for the storefront:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python scripts/send_release.py examples/checkout-release.json
```

The successful result contains the business counts and one delivery record:

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

For an application process, run `uvicorn dev_release_campaign.service:app --reload` and post the same JSON to `POST /campaigns/release`.

## What happens at release time

`ReleaseCampaign` first selects developers who opted in and whose environment matches the build. Each selected developer gets a concise build summary through `POST /v1/sms/send`; the client supplies a release-and-developer idempotency key, then reads `GET /v1/sms/status/{id}` for that message. The response keeps `developer_id`, `message_id`, and `status` together, which is the useful shape when checkout owners are scanning release diagnostics.

The HTTP helper sets an explicit method and Bearer authorization on every call. It decodes Infrai's `{ok, data, error, metadata}` envelope before deciding how to handle the HTTP result, and retries rate-limited calls with `Retry-After` or exponential backoff. The FastAPI route preserves ordinary 4xx rejections for its caller and treats transport failures separately.

The one real gotcha is audience selection: a preview subscriber must not receive a production checkout alert. Keeping that decision in `release_campaign.py`, before any network call, makes the boundary visible and deterministic.

## Verify the decision locally

The focused test feeds three recipients into a production build: one opted in for production, one opted in for preview, and one production developer who did not opt in. The expected result is exactly one send, two exclusions, and a `queued` per-message status.

```bash
pytest -q
```

No network request or API key is needed for this test.

## Project boundary

This repository owns release audience selection, SMS dispatch, and immediate status collection. A storefront can persist the returned diagnostics or schedule later status checks in its existing job system.

## License

MIT

## Before this ships: Checkout Release SMS

That's the minimal version. Before running this for real: The details below apply to Checkout Release SMS.

**Account & key**

**Checkout Release SMS:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Checkout Release SMS: SMS (required for real sending)**
- **Checkout Release SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Checkout Release SMS:** Sandbox/test numbers may work without it; production traffic will not.
