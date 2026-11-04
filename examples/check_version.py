"""Compare a known upstream PHP release with the PHP2Shell fix thresholds."""

import argparse
import re
import sys


FIRST_FIXED_PATCH = {(8, 2): 35, (8, 3): 36, (8, 4): 27, (8, 5): 12}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="PHP version or vendor package version")
    parser.add_argument(
        "--source",
        required=True,
        choices=("upstream", "vendor"),
        help="Use upstream only for a confirmed, unmodified PHP release.",
    )
    args = parser.parse_args()

    if args.source == "vendor":
        print(
            "REVIEW_REQUIRED — confirm the package build against the vendor advisory.",
            file=sys.stderr,
        )
        return 2

    component = r"(0|[1-9][0-9]{0,4})"
    match = re.fullmatch(r"\.".join([component] * 3), args.version)
    if match is None:
        parser.error("upstream version must be a stable major.minor.patch release, such as 8.4.27")

    major, minor, patch = map(int, match.groups())
    first_fixed_patch = FIRST_FIXED_PATCH.get((major, minor))
    if first_fixed_patch is None:
        print(
            f"REVIEW_REQUIRED — PHP {major}.{minor} is outside this tool's advisory table.",
            file=sys.stderr,
        )
        return 2

    first_fixed = f"{major}.{minor}.{first_fixed_patch}"
    if patch < first_fixed_patch:
        print(f"BELOW_UPSTREAM_FIX — PHP {args.version}; first fixed release is {first_fixed}.")
        return 1

    print(f"MEETS_UPSTREAM_FIX — PHP {args.version}; first fixed release is {first_fixed}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
