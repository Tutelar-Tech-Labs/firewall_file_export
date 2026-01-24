import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IST = timezone(timedelta(hours=5, minutes=30))


def api_call(host, api_key, params):
    params["key"] = api_key
    r = requests.get(
        f"https://{host}/api/",
        params=params,
        verify=False,
        timeout=60
    )
    r.raise_for_status()
    return r.text


def parse_duration(duration):
    if duration == "all":
        return None

    duration = duration.strip().lower()
    m = re.match(r"(\d+(?:\.\d+)?)(h|d|w|m|min)$", duration)
    if not m:
        raise ValueError("Invalid duration format. Use 1h, 24h, 7d, 1w, 1m, 30min, all")

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


def extract_rule_name_from_path(path):
    if not path:
        return None

    path = " ".join(path.split())
    m = re.search(
        r"(?:pre-rulebase|post-rulebase|rulebase)\s+security\s+rules\s+(.+)$",
        path
    )
    return m.group(1).strip() if m else None


def fetch_config_log_events(host, api_key, delta=None, max_poll=120):
    params = {"type": "log", "log-type": "config"}

    if delta:
        now = datetime.now(IST)
        start = now - delta
        start_str = start.strftime("%Y/%m/%d %H:%M:%S")
        params["query"] = f"(receive_time geq '{start_str}')"
        params["nlogs"] = "5000"

    xml = api_call(host, api_key, params)
    root = ET.fromstring(xml)

    job_id = root.findtext(".//job")
    if not job_id:
        raise RuntimeError("No job ID returned from config log API")

    for _ in range(max_poll):
        time.sleep(2)
        xml = api_call(host, api_key, {
            "type": "log",
            "action": "get",
            "job-id": job_id
        })
        root = ET.fromstring(xml)

        if root.findtext(".//status") == "FIN":
            return root.findall(".//entry")

    raise RuntimeError("Timeout while waiting for config log job")


def fetch_config_log_added_rules(host, api_key, delta):
    entries = fetch_config_log_events(host, api_key, delta=delta)
    now = datetime.now(IST)

    rules = {}

    for e in entries:
        rule = extract_rule_name_from_path(e.findtext("path"))
        if not rule:
            continue

        t_raw = e.findtext("time_generated")
        if not t_raw:
            continue

        try:
            t = datetime.strptime(t_raw, "%Y/%m/%d %H:%M:%S").replace(tzinfo=IST)
        except Exception:
            continue

        if delta and (now - t > delta):
            continue

        if rule not in rules or t < rules[rule]:
            rules[rule] = t

    return rules


def members(e, tag):
    vals = [m.text for m in e.findall(f"./{tag}/member") if m.text]
    return ", ".join(vals) if vals else "any"


def text(e, tag, default=""):
    x = e.find(tag)
    return x.text.strip() if x is not None and x.text else default


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
        if not name:
            continue

        rules[name] = {
            "name": name,
            "from_zone": members(e, "from"),
            "to_zone": members(e, "to"),
            "source": members(e, "source"),
            "destination": members(e, "destination"),
            "application": members(e, "application"),
            "service": members(e, "service"),
            "action": text(e, "action", "N/A"),
        }

    return rules
