import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import csv
import json
import argparse
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IST = timezone(timedelta(hours=5, minutes=30))


# ---------------- API HELPERS ----------------

def api_call(host, api_key, params):
    params["key"] = api_key
    r = requests.get(
        f"https://{host}/api/",
        params=params,
        verify=False,
        timeout=30
    )
    r.raise_for_status()
    return r.text


# ---------------- DURATION ----------------

def parse_duration(duration):
    if duration == "all":
        return None

    m = re.match(r"(\d+(?:\.\d+)?)(h|d|w|m|min)", duration)
    if not m:
        raise ValueError("Invalid duration format")

    value, unit = float(m.group(1)), m.group(2)

    if unit == "h":
        return timedelta(hours=value)
    if unit == "d":
        return timedelta(days=value)
    if unit == "w":
        return timedelta(weeks=value)
    if unit == "m":
        return timedelta(days=value * 30)
    if unit == "min":
        return timedelta(minutes=value)


# ---------------- CONFIG LOGS ----------------

def extract_rule_name_from_path(path):
    """
    Correct extraction:
    Everything AFTER 'rulebase security rules'
    """
    marker = "rulebase security rules"
    if not path or marker not in path:
        return None

    rule = path.split(marker, 1)[1].strip()
    if not rule:
        return None

    return rule


def fetch_config_log_add_events(host, api_key, delta):
    # Start async job
    xml = api_call(host, api_key, {
        "type": "log",
        "log-type": "config"
    })

    root = ET.fromstring(xml)
    job_id = root.findtext(".//job")
    if not job_id:
        raise RuntimeError("No job ID returned")

    # Poll
    while True:
        time.sleep(2)
        xml = api_call(host, api_key, {
            "type": "log",
            "action": "get",
            "job-id": job_id
        })
        root = ET.fromstring(xml)
        if root.findtext(".//status") == "FIN":
            break

    now = datetime.now(IST)
    added_rules = {}

    for e in root.findall(".//entry"):
        path = e.findtext("path")
        time_raw = e.findtext("time_generated")

        rule_name = extract_rule_name_from_path(path)
        if not rule_name:
            continue

        try:
            t = datetime.strptime(
                time_raw, "%Y/%m/%d %H:%M:%S"
            ).replace(tzinfo=IST)
        except Exception:
            continue

        if delta and now - t > delta:
            continue

        if rule_name not in added_rules or t < added_rules[rule_name]:
            added_rules[rule_name] = t

    return added_rules


# ---------------- RULE DETAILS ----------------

def get_security_rules(host, api_key, vsys):
    xml = api_call(host, api_key, {
        "type": "config",
        "action": "get",
        "xpath": (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']"
            "/rulebase/security/rules"
        )
    })

    root = ET.fromstring(xml)
    rules = {}

    for e in root.findall(".//entry"):
        name = e.get("name")

        rules[name] = {
            "name": name,
            "from_zone": members(e, "from"),
            "to_zone": members(e, "to"),
            "source": members(e, "source"),
            "destination": members(e, "destination"),
            "application": members(e, "application"),
            "service": members(e, "service"),
            "action": text(e, "action"),
            "log_start": text(e, "log-start", "no"),
            "log_end": text(e, "log-end", "yes"),
        }

    return rules


def members(e, tag):
    vals = [m.text for m in e.findall(f".//{tag}/member") if m.text]
    return ", ".join(vals) if vals else "any"


def text(e, tag, default=""):
    x = e.find(tag)
    return x.text if x is not None and x.text else default


# ---------------- MAIN ----------------

def main():
    parser = argparse.ArgumentParser(
        description="Export firewall rules added within a duration (with full details)"
    )
    parser.add_argument("--host", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--vsys", default="vsys1")
    parser.add_argument("--duration", default="all",
                        help="1h, 24h, 7d, 1w, 1m, 30min, all")
    parser.add_argument("--output", default="added_rules")
    parser.add_argument("--format", choices=["csv", "json", "both"], default="both")
    args = parser.parse_args()

    delta = parse_duration(args.duration)

    print("Fetching config log add events...")
    added_rules = fetch_config_log_add_events(
        args.host, args.api_key, delta
    )

    print("Fetching security rule details...")
    rule_details = get_security_rules(
        args.host, args.api_key, args.vsys
    )

    final = []

    for rule_name, modified_time in added_rules.items():
        if rule_name not in rule_details:
            continue

        row = rule_details[rule_name].copy()
        row["modified_time"] = modified_time.strftime("%Y/%m/%d %H:%M:%S")
        final.append(row)

    print("Final rules exported:", len(final))

    ts = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    base = f"{args.output}_{args.duration}_{ts}"

    if args.format in ("csv", "both") and final:
        with open(base + ".csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, final[0].keys())
            writer.writeheader()
            writer.writerows(final)

    if args.format in ("json", "both"):
        with open(base + ".json", "w", encoding="utf-8") as f:
            json.dump(final, f, indent=2)

    print("Export complete.")


if __name__ == "__main__":
    main()
