from __future__ import annotations

import argparse
import json
import os

from dev_release_campaign.infrai_sms import InfraiSmsClient
from dev_release_campaign.release_campaign import ReleaseCampaign, ReleaseCampaignRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a developer release SMS campaign")
    parser.add_argument("campaign", help="path to a campaign JSON file")
    args = parser.parse_args()

    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("INFRAI_API_KEY is required")
    with open(args.campaign, encoding="utf-8") as handle:
        request = ReleaseCampaignRequest.model_validate(json.load(handle))
    result = ReleaseCampaign(InfraiSmsClient(api_key)).run(request)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
