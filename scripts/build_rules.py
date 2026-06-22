#!/usr/bin/env python3
"""Build the Shadowrocket configuration from an upstream base and local fragments."""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request
from pathlib import Path


DEFAULT_UPSTREAM = (
    "https://raw.githubusercontent.com/Johnshall/"
    "Shadowrocket-ADBlock-Rules-Forever/release/"
    "sr_top500_whitelist_ad.conf"
)
SECTION_RE = re.compile(r"^\[([^]]+)]\s*$", re.MULTILINE)
MIN_UPSTREAM_RULES = 10_000
MAX_UPSTREAM_BYTES = 40 * 1024 * 1024
CLASH_POLICY_MINIMUMS = {
    "reject": 10_000,
    "direct": 100,
    "proxy": 100,
}


def fetch_upstream(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "hrd201-shadowrocket-rules-builder/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(f"upstream returned HTTP {response.status}")
        payload = response.read(MAX_UPSTREAM_BYTES + 1)
    if len(payload) > MAX_UPSTREAM_BYTES:
        raise RuntimeError("upstream configuration exceeds the size limit")
    return payload.decode("utf-8-sig")


def read_upstream(path: Path | None, url: str) -> str:
    if path is not None:
        return path.read_text(encoding="utf-8-sig")
    return fetch_upstream(url)


def extract_section(config: str, wanted: str) -> list[str]:
    lines: list[str] = []
    current: str | None = None
    found = False
    for raw_line in config.splitlines():
        match = SECTION_RE.match(raw_line.strip())
        if match:
            current = match.group(1)
            found = found or current == wanted
            continue
        if current == wanted:
            lines.append(raw_line.rstrip())
    if not found:
        raise RuntimeError(f"upstream section [{wanted}] is missing")
    return lines


def significant(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def validate_upstream(rule_lines: list[str]) -> None:
    rules = significant(rule_lines)
    if len(rules) < MIN_UPSTREAM_RULES:
        raise RuntimeError(
            f"upstream rule count is unexpectedly small: {len(rules)}"
        )
    finals = [line for line in rules if line.upper().startswith("FINAL,")]
    if len(finals) != 1:
        raise RuntimeError(f"upstream must contain exactly one FINAL rule, got {len(finals)}")
    if rules[-1].upper() != "FINAL,PROXY":
        raise RuntimeError("upstream FINAL rule must be the last rule and use PROXY")
    if not any(line.upper() == "GEOIP,CN,DIRECT" for line in rules):
        raise RuntimeError("upstream GEOIP,CN,DIRECT rule is missing")
    if not any(line.upper() == "DOMAIN-SUFFIX,CN,DIRECT" for line in rules):
        raise RuntimeError("upstream DOMAIN-SUFFIX,cn,DIRECT rule is missing")


def split_clash_rules(rule_lines: list[str]) -> dict[str, list[str]]:
    """Strip Shadowrocket policies and group rules for Clash classical providers."""
    grouped = {policy: [] for policy in CLASH_POLICY_MINIMUMS}
    for raw_line in rule_lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        line = line.split(" #", 1)[0].strip()
        parts = [part.strip() for part in line.split(",")]
        policy_index = next(
            (index for index, part in enumerate(parts) if part.lower() in grouped),
            None,
        )
        if policy_index is None:
            raise RuntimeError(f"cannot determine upstream policy: {raw_line}")

        rule_type = parts[0].upper()
        if rule_type in {"FINAL", "RULE-SET"}:
            continue

        policy = parts[policy_index].lower()
        provider_rule = ",".join(parts[:policy_index] + parts[policy_index + 1 :])
        if not provider_rule:
            raise RuntimeError(f"empty Clash provider rule derived from: {raw_line}")
        grouped[policy].append(provider_rule)

    for policy, minimum in CLASH_POLICY_MINIMUMS.items():
        count = len(grouped[policy])
        if count < minimum:
            raise RuntimeError(
                f"Clash {policy} provider is unexpectedly small: {count} < {minimum}"
            )
    return grouped


def render_clash_provider(policy: str, rules: list[str], upstream_url: str) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    payload = "\n".join(f"  - {quote(rule)}" for rule in rules)
    return f"""# AUTO-GENERATED FILE. DO NOT EDIT.
# Policy: {policy.upper()}
# Upstream: {upstream_url}
# Upstream project: Johnshall/Shadowrocket-ADBlock-Rules-Forever
# License: CC BY-SA 4.0. See ../LICENSE and ../NOTICE.
payload:
{payload}
"""


def fragment(root: Path, name: str) -> str:
    path = root / "custom" / name
    data = path.read_text(encoding="utf-8").strip()
    if not data:
        raise RuntimeError(f"custom fragment is empty: {path}")
    if SECTION_RE.search(data):
        raise RuntimeError(f"custom fragment must not contain section headers: {path}")
    return data


def render(root: Path, upstream_url: str, upstream_rules: list[str]) -> str:
    upstream_body = "\n".join(upstream_rules).strip()
    return f"""# AUTO-GENERATED FILE. Edit custom/* or scripts/build_rules.py instead.
# Upstream: {upstream_url}
# Upstream project: Johnshall/Shadowrocket-ADBlock-Rules-Forever
# License: CC BY-SA 4.0. See LICENSE and NOTICE.

[General]
{fragment(root, 'general.conf')}

[Rule]
# Local rules intentionally precede upstream rules.
{fragment(root, 'rules-priority.conf')}

# Daily-generated upstream rules begin here.
{upstream_body}
# Daily-generated upstream rules end here.

[URL Rewrite]
{fragment(root, 'url-rewrite.conf')}

[Script]
{fragment(root, 'scripts.conf')}

[Map Local]
{fragment(root, 'map-local.conf')}

[MITM]
{fragment(root, 'mitm.conf')}
"""


def validate_generated(config: str) -> None:
    required_sections = ["General", "Rule", "URL Rewrite", "Script", "Map Local", "MITM"]
    found = SECTION_RE.findall(config)
    if found != required_sections:
        raise RuntimeError(f"unexpected section order: {found}")

    rules = extract_section(config, "Rule")
    rule_values = significant(rules)
    if sum(line.upper().startswith("FINAL,") for line in rule_values) != 1:
        raise RuntimeError("generated configuration must contain exactly one FINAL rule")

    final_index = next(i for i, line in enumerate(rule_values) if line.upper().startswith("FINAL,"))
    if final_index != len(rule_values) - 1:
        raise RuntimeError("generated FINAL rule is not last")

    required_markers = [
        "DOMAIN,jpn.201pc.win,DIRECT",
        "IP-CIDR,67.230.172.130/32,DIRECT,no-resolve",
        "DOMAIN,ads3-normal-lq.zijieapi.com,REJECT",
        "DOMAIN,adse.ximalaya.com,REJECT",
        "redfruit.ad.response =",
        "youtube.response =",
        "*.ximalaya.com",
    ]
    for marker in required_markers:
        if marker not in config:
            raise RuntimeError(f"required custom marker is missing: {marker}")

    if len(config.encode("utf-8")) > MAX_UPSTREAM_BYTES:
        raise RuntimeError("generated configuration exceeds the size limit")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-url", default=os.environ.get("UPSTREAM_URL", DEFAULT_UPSTREAM))
    parser.add_argument("--upstream-file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("hrd201-sr.conf"))
    parser.add_argument("--mirror", type=Path, default=Path("hrd201-sr-v2.conf"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    upstream = read_upstream(args.upstream_file, args.upstream_url)
    upstream_rules = extract_section(upstream, "Rule")
    validate_upstream(upstream_rules)
    clash_rules = split_clash_rules(upstream_rules)
    generated = render(root, args.upstream_url, upstream_rules)
    validate_generated(generated)

    for output in (args.output, args.mirror):
        destination = output if output.is_absolute() else root / output
        destination.write_text(generated, encoding="utf-8", newline="\n")

    clash_dir = root / "clash"
    clash_dir.mkdir(exist_ok=True)
    for policy, rules in clash_rules.items():
        provider = render_clash_provider(policy, rules, args.upstream_url)
        (clash_dir / f"johnshall-{policy}.yaml").write_text(
            provider,
            encoding="utf-8",
            newline="\n",
        )

    print(
        f"Generated {len(significant(upstream_rules))} upstream rules; "
        f"Shadowrocket output size {len(generated.encode('utf-8'))} bytes; "
        + ", ".join(
            f"Clash {policy}={len(rules)}" for policy, rules in clash_rules.items()
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
