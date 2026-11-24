"""Delete registrations created by automated tests (mobile numbers in the reserved range).

    python scripts/purge_test_data.py            # dry run: list what would be deleted
    python scripts/purge_test_data.py --apply    # delete

Uses BASE_URL / ADMIN_USERNAME / ADMIN_PASSWORD from the environment or .env.
"""

from __future__ import annotations

import argparse
import sys

from playwright.sync_api import sync_playwright

from mpl_qa.api.client import RegistrationApi
from mpl_qa.config import get_settings
from mpl_qa.data.factories import TEST_MOBILE_PREFIX


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    args = parser.parse_args()
    settings = get_settings()

    with sync_playwright() as pw:
        ctx = pw.request.new_context(base_url=settings.base_url)
        api = RegistrationApi(ctx).login(settings.admin_username, settings.admin_password)
        doomed = [r for r in api.all() if r.mobile.startswith(TEST_MOBILE_PREFIX)]
        for reg in doomed:
            print(f"{'deleting' if args.apply else 'would delete'} {reg.id}  {reg.name}")
            if args.apply:
                api.delete(reg.id)
        ctx.dispose()

    print(
        f"{len(doomed)} test registration(s) {'deleted' if args.apply else 'found'} "
        f"on {settings.base_url}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
