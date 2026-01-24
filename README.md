# Firewall Rule Export Web Application

A web-based tool developed by that enables administrators to export firewall rule and configuration data in CSV or JSON format with a simple browser interface. The application automates API calls, processes data, and provides downloadable reports.

This project supports both **Windows** (primary deployment) and **Linux** servers, includes automated service deployment methods, GitHub auto-update workflows, and an optional method to expose the app publicly using **ngrok**.

---

## 🔍 Features

- ✔ Browser-based rule export UI  
- ✔ API-based data fetching  
- ✔ Custom duration filters  
- ✔ Export results as **CSV** and **JSON**  
- ✔ Multi-user access within a network  
- ✔ Automatic service setup (Windows & Linux)  
- ✔ GitHub auto-update support  
- ✔ Optional external access via **ngrok**

---

## 📁 Repository Structure

```

app.py
palo_rule_added_export.py
requirements.txt
templates/
exports/
webhook.py
windows_winsw/
linux_systemd/
README.md

````

- **app.py** – Main Flask application  
- **palo_rule_added_export.py** – Logic for fetching and parsing rule data  
- **templates/** – Frontend HTML pages  
- **exports/** – Generated export files  
- **webhook.py** – Webhook listener for GitHub auto updates  
- **windows_winsw/** – Windows service files (WinSW)  
- **linux_systemd/** – Linux service files for systemd

---

## 🛠 Technologies

- Python 3.9+  
- Flask  
- Waitress (production WSGI server)  
- Git  
- Optional: ngrok (for tunneling)

---

## 🚀 Quick Start

### 1. Install Prerequisites

Install Python (3.9+) and Git:

```bash
# Python must be added to PATH on Windows
````

---

### 2. Clone the Repository

```bash
git clone https://github.com/supporttutelartech/firewall_file_export.git
cd firewall_file_export
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Run Development Server

```bash
python app.py
```

Then open:

```
http://localhost:5000
```

---

## 📌 Production Deployment

### ✅ Windows (Preferred)

This method uses **WinSW** to run the app as a Windows service.

#### 1. Download WinSW

From:
[https://github.com/winsw/winsw/releases](https://github.com/winsw/winsw/releases)

Rename the file to:

```
firewall_service.exe
```

And place it inside the project folder.

#### 2. Create Service XML

Example `firewall_service.xml`:

```xml
<service>
  <id>TutelarFirewallExport</id>
  <name>Firewall Export</name>
  <description>Firewall Rule Export Web Application</description>
  <executable>C:\Users\USERNAME\AppData\Local\Programs\Python\Python314\python.exe</executable>
  <arguments>app.py</arguments>
  <workingdirectory>D:\firewall_file_export</workingdirectory>
  <log mode="roll"></log>
  <onfailure action="restart" delay="10 sec"/>
</service>
```

Replace the Python path and working directory as appropriate.

#### 3. Install & Start Service

```cmd
cd D:\firewall_file_export
firewall_service.exe install
firewall_service.exe start
```

---

### 🧠 Verify Operation

Ensure the service is listening:

```
netstat -ano | findstr 5000
```

Users on your network can now open:

```
http://<host-ip>:5000
```

---

## 🗂 Windows Alternative: Task Scheduler

If WinSW is not allowed:

1. Open Task Scheduler
2. Create a new task
3. Action:

```
Program: C:\Users\<USER>\AppData\Local\Programs\Python\Python314\python.exe
Arguments: app.py
Start in: D:\firewall_file_export
```

4. Trigger: At System Startup

---

## 🔄 GitHub Auto Update

To auto-update when pushing to GitHub:

### webhook.py

```python
from flask import Flask
import subprocess

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    project_path = "D:\\firewall_file_export"
    subprocess.run(["git", "pull"], cwd=project_path)
    return "Updated", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000)
```

Run this in background to accept GitHub webhooks.

---

## 🐧 Linux Deployment

### 1. Install Requirements

```bash
sudo apt update
sudo apt install python3 python3-pip git
```

### 2. Clone and Install

```bash
git clone https://github.com/supporttutelartech/firewall_file_export.git
cd firewall_file_export
pip3 install -r requirements.txt
```

### 3. Systemd Service

Create:

```
/etc/systemd/system/firewall_export.service
```

```ini
[Unit]
Description=Firewall Export App
After=network.target

[Service]
User=root
WorkingDirectory=/root/firewall_file_export
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable firewall_export
sudo systemctl start firewall_export
```

---

## 🔥 GitHub Auto-Update on Linux (with ngrok)

Install ngrok on Linux:

```bash
wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip
unzip ngrok-stable-linux-amd64.zip
./ngrok authtoken <YOUR_TOKEN>
```

Run webhook listener:

```
python3 webhook.py
```

Expose port 9000:

```
./ngrok http 9000
```

Use generated public URL in GitHub webhook settings.

---

## 🌐 Optional: Public Access via ngrok

Expose the app externally (only for testing/demos):

```
ngrok http 5000
```

You’ll get a public URL like:

```
https://abcd1234.ngrok-free.app
```

⚠️ **Note:** ngrok free URLs change every restart.

---

## 🧪 Troubleshooting

| Issue                                 | Solution                                   |
| ------------------------------------- | ------------------------------------------ |
| App works manually but not as service | Use Waitress (production server)           |
| Windows service fails                 | Ensure full Python path in XML             |
| Cannot access from LAN                | Open firewall port 5000                    |
| Webhook not firing                    | Validate webhook URL (ngrok/public domain) |
| ngrok link expired                    | Restart ngrok and share new link           |

---

## 🛡 Best Practices

* Keep API credentials secure
* Use internal network for access
* Enable HTTPS for public deployment
* Use paid ngrok for stable URLs

---
