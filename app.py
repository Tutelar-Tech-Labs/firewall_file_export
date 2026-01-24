from flask import Flask, render_template, request, send_from_directory
import os
from datetime import datetime
from waitress import serve
import csv, json

from palo_rule_added_export import (
    fetch_config_log_added_rules,
    get_security_rules,
    parse_duration,
    IST
)

app = Flask(__name__)

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

CSV_COLUMNS = [
    "name",
    "from_zone",
    "to_zone",
    "source",
    "destination",
    "application",
    "service",
    "action",
    "added_time",
]


def normalize_duration(duration_ui):
    mapping = {
        "Last 1 hour": "1h",
        "Last 24 hours": "24h",
        "Last 7 days": "7d",
        "Last 1 month": "1m",
        "All Logs": "all",
        "Custom": "custom",
        "custom": "custom",
    }
    if not duration_ui:
        return "all"
    return mapping.get(duration_ui.strip(), duration_ui.strip())


def normalize_row(row: dict):
    return {col: row.get(col, "") for col in CSV_COLUMNS}


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        status, files = [], {}

        host = request.form.get("host", "").strip()
        api_key = request.form.get("api_key", "").strip()
        vsys = request.form.get("vsys", "vsys1").strip()

        duration_ui = request.form.get("duration", "all")
        custom_duration = request.form.get("custom_duration", "").strip()
        output_format = request.form.get("format", "both").strip().lower()

        duration = normalize_duration(duration_ui)
        if duration == "custom":
            duration = custom_duration.strip()

        if not duration:
            duration = "all"

        now = datetime.now(IST)
        ts = now.strftime("%Y%m%d_%H%M%S")

        status.append(f"Duration selected: {duration_ui} → using '{duration}'")

        status.append("Fetching CURRENT firewall rules...")
        rule_details = get_security_rules(host, api_key, vsys)

        final = []

        # -------- ALL MODE --------
        if duration == "all":
            status.append("Mode: ALL existing rules export")
            status.append("Fetching config logs to populate added_time for ALL rules...")
            delta_for_all = parse_duration("365d")
            added_rules_map = fetch_config_log_added_rules(host, api_key, delta_for_all)

            for rule in sorted(rule_details.values(), key=lambda x: x["name"].lower()):
                row = rule.copy()

                # ✅ Fill added_time if present in logs
                t = added_rules_map.get(row["name"])
                if t:
                    row["added_time"] = t.strftime("%Y/%m/%d %H:%M:%S")
                else:
                    row["added_time"] = ""

                final.append(normalize_row(row))

            base = f"rules_ALL_{ts}"

        # -------- STRICT DURATION MODE --------
        else:
            try:
                delta = parse_duration(duration)
            except Exception:
                status.append("❌ Invalid duration format. Example: 1h, 24h, 7d, 1m, 30min")
                return render_template("result.html", status=status, files={})

            status.append(f"Mode: DURATION export ({duration})")
            #status.append("Fetching config log events (time filtered)...")

            added_rules = fetch_config_log_added_rules(host, api_key, delta)
            #status.append(f"Rules found in logs: {len(added_rules)}")

            skipped_deleted = 0

            for name, added_time in sorted(added_rules.items(), key=lambda x: x[1]):
                if name not in rule_details:
                    skipped_deleted += 1
                    continue

                row = rule_details[name].copy()
                row["added_time"] = added_time.strftime("%Y/%m/%d %H:%M:%S")
                final.append(normalize_row(row))

            #status.append(f"Skipped deleted/non-existing rules: {skipped_deleted}")

            base = f"rules_{duration}_{ts}"

        status.append(f"Final rows exported: {len(final)}")

        # -------- EXPORT --------
        exported_files_count = 0

        if output_format in ("csv", "both") and final:
            csv_file = base + ".csv"
            with open(os.path.join(EXPORT_DIR, csv_file), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(final)

            files["csv"] = csv_file
            exported_files_count += 1
            status.append(f"CSV exported: {csv_file}")

        if output_format in ("json", "both"):
            json_file = base + ".json"
            with open(os.path.join(EXPORT_DIR, json_file), "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2)

            files["json"] = json_file
            exported_files_count += 1
            status.append(f"JSON exported: {json_file}")

        status.append(f"Export completed ✅ Files created: {exported_files_count}")

        return render_template("result.html", status=status, files=files)

    return render_template("index.html")


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print("Starting Flask app at port 5010...")
    serve(app, host="0.0.0.0", port=5010)
