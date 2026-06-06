import os
import shutil
import smtplib
import subprocess
import time
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import gradio as gr
from faker import Faker
import requests
import pandas as pd
from fpdf import FPDF
from datetime import datetime

fake = Faker()
Faker.seed(42)  # Reproducible for tests

# Load/save config
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "smtp": {"server": "smtp.gmail.com", "port": 587, "user": "", "password": "", "to": "test@yourdomain.com"},
    "web_upload_url": "https://dlptest.com/api/test",  # Or your test endpoint
    "industry": "healthcare",  # healthcare, finance, legal, generic
    "dry_run": True
}

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)

with open(CONFIG_FILE) as f:
    config = json.load(f)

def generate_sensitive_data(industry="healthcare", num_records=5):
    """Generate realistic fake sensitive data and save to files."""
    data = []
    os.makedirs("test_data", exist_ok=True)
    
    for i in range(num_records):
        if industry == "healthcare":
            record = {
                "name": fake.name(),
                "ssn": fake.ssn(),
                "dob": fake.date_of_birth().isoformat(),
                "mrn": fake.uuid4()[:8].upper(),
                "diagnosis": fake.sentence(),
                "notes": fake.paragraph()
            }
        elif industry == "finance":
            record = {
                "name": fake.name(),
                "cc": fake.credit_card_full(),
                "account": fake.iban(),
                "balance": fake.pydecimal(left_digits=5, right_digits=2, positive=True)
            }
        else:
            record = {"name": fake.name(), "email": fake.email(), "info": fake.text(max_nb_chars=200)}
        
        data.append(record)
        
        # Save as CSV, TXT, PDF
        df = pd.DataFrame([record])
        df.to_csv(f"test_data/sensitive_{i}.csv", index=False)
        
        with open(f"test_data/sensitive_{i}.txt", "w") as f:
            f.write(str(record))
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for k, v in record.items():
            pdf.cell(200, 10, txt=f"{k}: {v}", ln=1)
        pdf.output(f"test_data/sensitive_{i}.pdf")
    
    return "Generated test files in ./test_data/"

def send_test_email(attachment_path=None):
    if config["dry_run"]:
        return "DRY RUN: Email prepared (not sent)."
    try:
        msg = MIMEMultipart()
        msg['From'] = config["smtp"]["user"]
        msg['To'] = config["smtp"]["to"]
        msg['Subject'] = "Test Insider Data Transfer - DLP Test"
        
        body = "This is a simulated insider email exfil test. Contains attached sensitive data."
        msg.attach(MIMEText(body, 'plain'))
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(attachment_path)}")
            msg.attach(part)
        
        server = smtplib.SMTP(config["smtp"]["server"], config["smtp"]["port"])
        server.starttls()
        server.login(config["smtp"]["user"], config["smtp"]["password"])
        server.send_message(msg)
        server.quit()
        return f"Email sent with attachment: {attachment_path or 'none'}"
    except Exception as e:
        return f"Email error: {str(e)}"

def web_upload_test(file_path):
    if config["dry_run"]:
        return "DRY RUN: Web upload simulated."
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(config["web_upload_url"], files=files, timeout=10)
        return f"Upload response: {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return f"Upload error: {str(e)}"

def print_test(file_path):
    if config["dry_run"]:
        return "DRY RUN: Print command prepared."
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['print', file_path], check=True)
        else:  # Mac/Linux (uses lp or lpr)
            subprocess.run(['lp', file_path], check=True)
        return f"Print job sent for: {file_path}"
    except Exception as e:
        return f"Print error: {str(e)} (ensure printer configured)"

def usb_transfer(file_path):
    if config["dry_run"]:
        return "DRY RUN: USB transfer simulated. Check removable drives."
    try:
        # Simple cross-platform USB detection (improve with pyudev on Linux or platform specifics)
        drives = []
        if os.name == 'posix':  # Mac/Linux
            base = '/Volumes' if 'darwin' in os.uname().sysname.lower() else '/media'
            for d in os.listdir(base):
                path = os.path.join(base, d)
                if os.path.isdir(path):
                    drives.append(path)
        else:  # Windows
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
        
        if not drives:
            return "No USB/removable drive detected."
        
        target = os.path.join(drives[0], "DLP_Test_Exfil")
        os.makedirs(target, exist_ok=True)
        shutil.copy(file_path, target)
        return f"Copied to USB: {target}/{os.path.basename(file_path)}"
    except Exception as e:
        return f"USB error: {str(e)}"

# Helper functions for expanded use cases
def send_test_email_with_to(attachment_path=None, to_email="personal@gmail.com"):
    """Simulate sending to personal email."""
    if config["dry_run"]:
        return f"DRY RUN: Email to {to_email} prepared."
    # Similar to send_test_email but override to
    try:
        # Reuse logic or duplicate minimally
        return f"Email sent to {to_email} (simulated)"
    except Exception as e:
        return f"Personal email error: {str(e)}"

import zipfile
def zip_and_exfil(file_path):
    """Create ZIP and attempt exfil (email or copy)."""
    if config["dry_run"]:
        return "DRY RUN: ZIP created and prepared for exfil."
    try:
        zip_path = file_path + ".zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(file_path)
        # Could email the zip or copy
        return f"ZIP created: {zip_path} - ready for exfil"
    except Exception as e:
        return f"ZIP error: {str(e)}"

def simulate_cloud_sync(file_path):
    """Simulate sync to Dropbox/OneDrive/etc."""
    if config["dry_run"]:
        return "DRY RUN: Cloud sync to personal folder simulated."
    return "Cloud sync attempted (mock)."

def simulate_clipboard_exfil(file_path):
    """Simulate copy-paste via clipboard."""
    if config["dry_run"]:
        return "DRY RUN: Clipboard exfil simulated (copy sensitive text)."
    return "Clipboard data copied (mock)."

def rename_and_transfer(file_path):
    """Obfuscate by renaming and transfer."""
    if config["dry_run"]:
        return "DRY RUN: File renamed and transferred."
    try:
        new_name = file_path.replace("sensitive", "invoice_report")
        shutil.copy(file_path, new_name)
        return f"Renamed to {new_name} and transferred."
    except Exception as e:
        return f"Rename error: {str(e)}"

def simulate_sftp(file_path):
    """Mock SFTP transfer."""
    if config["dry_run"]:
        return "DRY RUN: SFTP transfer to external server simulated."
    return "SFTP transfer mock success."

def simulate_onedrive(file_path):
    """Simulate OneDrive sync."""
    if config["dry_run"]:
        return "DRY RUN: OneDrive personal sync simulated."
    return "OneDrive sync mock."

def run_test(scenario="all", num_files=3, adaptive=False):
    """Enhanced run_test with multiple use cases and basic adaptive AI logic."""
    log = []
    generate_sensitive_data(config["industry"], num_files)
    files = [f for f in os.listdir("test_data") if os.path.isfile(os.path.join("test_data", f))]
    
    use_cases = {
        "email": send_test_email,
        "web": web_upload_test,
        "print": print_test,
        "usb": usb_transfer,
        # New expanded use cases
        "email_personal": lambda p: send_test_email_with_to(p, "personal@gmail.com"),  # Simulate personal email
        "zip_exfil": lambda p: zip_and_exfil(p),
        "cloud_sync": simulate_cloud_sync,
        "clipboard": simulate_clipboard_exfil,
        "rename_obfuscate": rename_and_transfer,
        "browser_upload": web_upload_test,  # Variant
        "sftp_transfer": simulate_sftp,
        "one_drive": simulate_onedrive,
    }
    
    active_scenarios = ["all"] if scenario == "all" else [scenario]
    
    for f in files[:num_files]:
        path = os.path.join("test_data", f)
        log.append(f"Testing: {f}")
        
        for sc in active_scenarios:
            if sc in use_cases:
                result = use_cases[sc](path)
                log.append(f"{sc.upper()}: {result}")
            elif sc == "all":
                for uc in ["email", "web", "print", "usb"]:
                    if uc in use_cases:
                        result = use_cases[uc](path)
                        log.append(f"{uc.upper()}: {result}")
        
        time.sleep(1)
    
    # Basic Adaptive AI Logic
    if adaptive:
        log.append("\n🤖 Adaptive AI Analysis:")
        blocked = any("blocked" in res.lower() or "error" in res.lower() for res in log)
        if blocked and "email" in str(log):
            log.append("AI Pivot: Email blocked → Trying ZIP + personal Gmail variant")
            zip_path = zip_and_exfil(files[0])
            log.append(f"ZIP PIVOT: {zip_path}")
        # More adaptive rules can be added here or via LLM integration
    
    # Generate report
    report_df = pd.DataFrame({"Timestamp": [datetime.now()], "Scenario": [scenario], "Log": ["\n".join(log)], "Adaptive": [adaptive]})
    report_path = f"dlp_test_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    report_df.to_csv(report_path, index=False)
    
    return "\n".join(log) + f"\n\nReport saved: {report_path}"

# Gradio UI - Professional Production Look
with gr.Blocks(title="IRIS DLP Test Engine", theme=gr.themes.Dark(), css="""
    .gradio-container {max-width: 1200px; margin: auto;}
    .header {text-align: center; padding: 20px; background: linear-gradient(135deg, #1e3a8a, #3b82f6); border-radius: 10px; color: white;}
    .tab-content {padding: 20px;}
""") as demo:
    with gr.Row():
        gr.Image(value="https://picsum.photos/id/1015/800/150", label=None, show_label=False, container=False, height=120)  # Placeholder logo banner
    
    gr.Markdown("""
    <div class="header">
        <h1>🛡️ IRIS DLP Insider Risk Test Engine</h1>
        <p style="font-size: 1.1em;">Professional Simulation Platform for Testing Data Loss Prevention Controls</p>
        <p><strong>Enterprise-Grade • Insider-Focused • Production Ready</strong></p>
    </div>
    """)
    
    with gr.Tabs():
        with gr.TabItem("🚀 Quick Test"):
            with gr.Row():
                with gr.Column(scale=1):
                    industry = gr.Dropdown(
                        ["healthcare", "finance", "legal", "generic"], 
                        value=config["industry"], 
                        label="📊 Industry Sector",
                        info="Select data profile for realistic test files"
                    )
                    dry_run = gr.Checkbox(
                        value=config["dry_run"], 
                        label="🛡️ Dry Run Mode (Recommended for Safety)",
                        info="Simulates actions without actual transmission"
                    )
                    num_files = gr.Slider(1, 10, value=3, step=1, label="📁 Number of Test Files")
                    
                with gr.Column(scale=1):
                    scenario = gr.Dropdown(
                        ["all", "email", "web", "print", "usb", "email_personal", "zip_exfil", "cloud_sync", "clipboard", "rename_obfuscate", "sftp_transfer", "one_drive", "adaptive_chain"],
                        value="all", 
                        label="🔄 Exfiltration Use Cases",
                        info="Expanded insider behaviors - select multiple via 'all' or specific",
                        multiselect=False
                    )
                    adaptive = gr.Checkbox(value=False, label="🤖 Enable Adaptive AI (Pivots on blocks)")
                    smtp_to = gr.Textbox(
                        value=config["smtp"]["to"], 
                        label="📧 Test Email Recipient",
                        placeholder="test@yourcompany.com"
                    )
                    web_url = gr.Textbox(
                        value=config["web_upload_url"], 
                        label="🌐 Web Upload Test Endpoint",
                        placeholder="https://dlptest.com/api/test"
                    )
            
            btn = gr.Button("🚀 EXECUTE INSIDER SIMULATION", variant="primary", size="large")
            output = gr.Textbox(label="📋 Real-Time Execution Log", lines=18, show_copy_button=True)
        
        with gr.TabItem("⚙️ Configuration & SMTP"):
            gr.Markdown("### SMTP Settings (for real email tests)")
            with gr.Row():
                smtp_server = gr.Textbox(value=config["smtp"]["server"], label="SMTP Server")
                smtp_port = gr.Textbox(value=config["smtp"]["port"], label="Port")
                smtp_user = gr.Textbox(value=config["smtp"]["user"], label="Username")
                smtp_pass = gr.Textbox(value=config["smtp"]["password"], label="Password", type="password")
            
            save_btn = gr.Button("💾 Save All Settings")
        
        with gr.TabItem("📊 Test History & Reports"):
            gr.Markdown("### Previous Test Reports")
            report_files = gr.FileExplorer(label="Download Reports", file_count="multiple", root_dir=".")
            refresh_btn = gr.Button("🔄 Refresh Reports")
    
    # Footer
    gr.Markdown("---\n**IRIS by WestHamStory** • For red teaming & defensive validation • Always use in authorized test environments only.")

    def update_config(ind, dr, to_email, wurl, srv, prt, usr, pwd):
        config["industry"] = ind
        config["dry_run"] = dr
        config["smtp"]["to"] = to_email
        config["web_upload_url"] = wurl
        config["smtp"]["server"] = srv
        config["smtp"]["port"] = int(prt)
        config["smtp"]["user"] = usr
        config["smtp"]["password"] = pwd
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        return "✅ Configuration saved successfully."
    
    def refresh_reports():
        reports = [f for f in os.listdir(".") if f.startswith("dlp_test_report")]
        return reports if reports else ["No reports yet. Run a test!"]

    save_btn.click(update_config, [industry, dry_run, smtp_to, web_url, smtp_server, smtp_port, smtp_user, smtp_pass], output)
    btn.click(run_test, [scenario, num_files, adaptive], output)
    refresh_btn.click(refresh_reports, outputs=report_files)

if __name__ == "__main__":
    demo.launch(share=False, server_name="127.0.0.1", server_port=7860)
