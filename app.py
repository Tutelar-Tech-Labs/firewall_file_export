from flask import Flask, render_template, request, send_from_directory
import os
from datetime import datetime
from palo_rule_added_export import (
    fetch_config_log_add_events,
    get_security_rules,
    parse_duration,
    IST
)
from waitress import serve

app = Flask(__name__)

EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        status = []

        host = request.form["host"]
        api_key = request.form["api_key"]
        vsys = request.form.get("vsys", "vsys1")

        duration = request.form["duration"]
        custom_duration = request.form.get("custom_duration")
        output_format = request.form["format"]

        if duration == "custom":
            duration = custom_duration

        delta = parse_duration(duration)
        now = datetime.now(IST)

        # ---- STEP 1 ----
        status.append("Fetching config log add events...")
        added_rules = fetch_config_log_add_events(host, api_key, delta)

        # ---- STEP 2 ----
        status.append("Fetching security rule details...")
        rule_details = get_security_rules(host, api_key, vsys)

        final = []
        for rule_name, added_time in added_rules.items():
            if rule_name not in rule_details:
                continue
            row = rule_details[rule_name].copy()
            row["added_time"] = added_time.strftime("%Y/%m/%d %H:%M:%S")
            final.append(row)

        status.append(f"Final rules exported: {len(final)}")

        ts = now.strftime("%Y%m%d_%H%M%S")
        base = f"rules_{duration}_{ts}"

        files = {}

        # ---- CSV ----
        if output_format in ("csv", "both") and final:
            csv_file = base + ".csv"
            import csv
            with open(os.path.join(EXPORT_DIR, csv_file), "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, final[0].keys())
                writer.writeheader()
                writer.writerows(final)
            files["csv"] = csv_file

        # ---- JSON ----
        if output_format in ("json", "both"):
            json_file = base + ".json"
            import json
            with open(os.path.join(EXPORT_DIR, json_file), "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2)
            files["json"] = json_file

        status.append("Export complete. You can now download the file(s).")

        return render_template(
            "result.html",
            status=status,
            files=files
        )

    return render_template("index.html")


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(EXPORT_DIR, filename, as_attachment=True)




if __name__ == "__main__":
    #app.run(host="0.0.0.0", port=5000, debug=True)
    print("Starting Flask app at port 5010...")
    serve(app, host="0.0.0.0", port=5010)

    