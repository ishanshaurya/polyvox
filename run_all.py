"""
RUN_ALL.py — Run the full Call Center QA pipeline in one command.

Usage:
    python run_all.py
    python run_all.py --step report   # re-run only one step

Prerequisites:
    pip install anthropic openai-whisper openpyxl pyyaml
    Set anthropic_api_key and email settings in config.yaml
"""

import sys
import os
import glob
import json
import argparse
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from collections import defaultdict
import yaml


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_dependencies():
    missing = []
    for pkg in ["anthropic", "whisper", "openpyxl", "yaml"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("   Run: pip install anthropic openai-whisper openpyxl pyyaml\n")
        sys.exit(1)


def validate_config(cfg):
    """Sanity-check config.yaml before running the pipeline."""
    kpis = cfg.get("kpis", [])
    if not kpis:
        print("\n❌ No KPIs defined in config.yaml\n")
        sys.exit(1)
    total_weight = sum(k.get("weight", 0) for k in kpis)
    if total_weight != 100:
        print(f"\n⚠️  WARNING: KPI weights sum to {total_weight}, not 100. "
              f"Scoring will still work but overall_score may be skewed.\n")
    for req in ("recordings_folder", "output_folder", "whisper_model", "claude_model"):
        if not cfg.get(req):
            print(f"\n❌ Missing required config: {req}\n")
            sys.exit(1)
    print(f"  ✓ Config valid  ({len(kpis)} KPIs, weights sum to {total_weight})")


def check_api_key(cfg):
    # First try config.yaml, then fall back to environment variable
    key = cfg.get("anthropic_api_key", "").strip()
    if key and not key.startswith("paste-your"):
        os.environ["ANTHROPIC_API_KEY"] = key
        print("  ✓ API key loaded from config.yaml")
    elif os.environ.get("ANTHROPIC_API_KEY"):
        print("  ✓ API key loaded from environment variable")
    else:
        print("\n❌ Anthropic API key not found.")
        print("   Open config.yaml and paste your key next to: anthropic_api_key:\n")
        sys.exit(1)


def build_email_summary(cfg):
    """Read analysis JSONs and build a plain-text + HTML summary for the email body."""
    analysis_dir = os.path.join(cfg["output_folder"], "analysis")
    records = []
    for path in sorted(glob.glob(os.path.join(analysis_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception:
            pass

    if not records:
        return "No analysis data found.", "<p>No analysis data found.</p>"

    total = len(records)
    escalations = [r for r in records if r.get("escalation_required")]
    converted = [r for r in records if r.get("appointment_converted")]
    requested = [r for r in records if r.get("appointment_requested")]
    surgical = [r for r in records if r.get("surgical_procedure_requested")]
    complaints_count = sum(len([c for c in r.get("patient_complaints", []) if c]) for r in records)

    scores = []
    for r in records:
        try:
            scores.append(float(r.get("overall_score", 0)))
        except (TypeError, ValueError):
            pass
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    conv_pct = f"{round(len(converted)/len(requested)*100)}%" if requested else "N/A"

    # Per-agent summary
    agents = defaultdict(lambda: {"scores": [], "escalations": 0})
    for r in records:
        a = r.get("agent_name", "Unknown")
        try:
            agents[a]["scores"].append(float(r.get("overall_score", 0)))
        except (TypeError, ValueError):
            pass
        if r.get("escalation_required"):
            agents[a]["escalations"] += 1

    agent_rows_txt = ""
    agent_rows_html = ""
    for agent, data in sorted(agents.items(), key=lambda x: -(sum(x[1]["scores"])/len(x[1]["scores"]) if x[1]["scores"] else 0)):
        avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
        calls = len(data["scores"])
        esc = data["escalations"]
        agent_rows_txt += f"  {agent:<25} {calls:>5} calls   Avg: {avg:>5}/100   Escalations: {esc}\n"
        color = "#c6efce" if avg >= 70 else ("#ffeb9c" if avg >= 55 else "#ffc7ce")
        esc_cell = f'<b style="color:#c00000">{esc}</b>' if esc else str(esc)
        agent_rows_html += (
            f"<tr style='background:{color}'>"
            f"<td style='padding:6px 12px'>{agent}</td>"
            f"<td style='padding:6px 12px;text-align:center'>{calls}</td>"
            f"<td style='padding:6px 12px;text-align:center'><b>{avg}/100</b></td>"
            f"<td style='padding:6px 12px;text-align:center'>{esc_cell}</td>"
            f"</tr>"
        )

    generated = datetime.now().strftime("%d %b %Y %H:%M")
    divider = "─" * 55

    plain = (
        f"KIMSHEALTH CALL CENTER QA — REPORT SUMMARY\n"
        f"Generated: {generated}\n"
        f"{divider}\n\n"
        f"  Total calls analyzed:      {total}\n"
        f"  Average overall score:     {avg_score}/100\n"
        f"  Escalations flagged:       {len(escalations)}\n"
        f"  Patient complaints:        {complaints_count}\n"
        f"  Appointment requests:      {len(requested)}  |  Converted: {len(converted)}  ({conv_pct})\n"
        f"  Surgical enquiries:        {len(surgical)}\n\n"
        f"AGENT BREAKDOWN:\n"
        f"{divider}\n"
        f"{agent_rows_txt}\n"
        f"{divider}\n"
        f"All 7 Excel reports are attached.\n"
    )

    html = f"""
<html><body style="font-family:Arial,sans-serif;color:#1f3864;max-width:700px">
<div style="background:#1f3864;padding:18px 24px;border-radius:6px 6px 0 0">
  <h2 style="color:#fff;margin:0">KIMSHEALTH Call Center QA Report</h2>
  <p style="color:#ccc;margin:4px 0 0">Generated: {generated}</p>
</div>
<div style="background:#f2f2f2;padding:16px 24px;border-bottom:3px solid #2e75b6">
  <table width="100%" cellspacing="0">
    <tr>
      <td style="padding:8px 16px;background:#fff;border-radius:4px;margin:4px">
        <div style="font-size:22px;font-weight:bold;color:#1f3864">{total}</div>
        <div style="font-size:11px;color:#888">Calls Analyzed</div>
      </td>
      <td width="12"></td>
      <td style="padding:8px 16px;background:#fff;border-radius:4px">
        <div style="font-size:22px;font-weight:bold;color:{'#375623' if avg_score>=70 else '#c00000'}">{avg_score}/100</div>
        <div style="font-size:11px;color:#888">Avg Score</div>
      </td>
      <td width="12"></td>
      <td style="padding:8px 16px;background:#fff;border-radius:4px">
        <div style="font-size:22px;font-weight:bold;color:#c00000">{len(escalations)}</div>
        <div style="font-size:11px;color:#888">Escalations</div>
      </td>
      <td width="12"></td>
      <td style="padding:8px 16px;background:#fff;border-radius:4px">
        <div style="font-size:22px;font-weight:bold;color:#7030a0">{conv_pct}</div>
        <div style="font-size:11px;color:#888">Appt Conversion</div>
      </td>
      <td width="12"></td>
      <td style="padding:8px 16px;background:#fff;border-radius:4px">
        <div style="font-size:22px;font-weight:bold;color:#ff6600">{complaints_count}</div>
        <div style="font-size:11px;color:#888">Complaints</div>
      </td>
    </tr>
  </table>
</div>
<div style="padding:16px 24px">
  <h3 style="color:#1f3864;border-bottom:2px solid #2e75b6;padding-bottom:4px">Agent Performance</h3>
  <table width="100%" cellspacing="0" style="border-collapse:collapse;font-size:13px">
    <tr style="background:#1f3864;color:#fff">
      <th style="padding:8px 12px;text-align:left">Agent</th>
      <th style="padding:8px 12px">Total Calls</th>
      <th style="padding:8px 12px">Avg Score</th>
      <th style="padding:8px 12px">Escalations</th>
    </tr>
    {agent_rows_html}
  </table>
</div>
<div style="padding:8px 24px 16px;font-size:12px;color:#888">
  All 7 Excel reports are attached to this email.
</div>
</body></html>
"""
    return plain, html


def send_email(cfg, subject_suffix=""):
    """Send generated Excel reports by email using settings from config.yaml."""
    email_cfg = cfg.get("email", {})
    if not email_cfg.get("enabled", False):
        return

    sender = email_cfg.get("sender_email", "").strip()
    password = email_cfg.get("sender_password", "").strip()
    recipients = email_cfg.get("recipients", [])
    smtp_server = email_cfg.get("smtp_server", "smtp.office365.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))

    if not sender or sender.startswith("paste-your"):
        print("\n  [Email] Skipped — sender_email not configured in config.yaml")
        return
    if not password or password.startswith("paste-your"):
        print("\n  [Email] Skipped — sender_password not configured in config.yaml")
        return
    if not recipients:
        print("\n  [Email] Skipped — no recipients configured")
        return

    # Find the most recently generated xlsx files (same timestamp batch)
    output_dir = cfg["output_folder"]
    all_xlsx = sorted(
        glob.glob(os.path.join(output_dir, "*.xlsx")),
        key=os.path.getmtime,
        reverse=True,
    )
    # Group by timestamp suffix (last 13 chars before .xlsx: YYYYMMDD_HHMM)
    if all_xlsx:
        latest_ts = os.path.basename(all_xlsx[0]).rsplit("_", 2)
        # Take all files modified within the last 10 minutes as this batch
        cutoff = os.path.getmtime(all_xlsx[0]) - 600
        batch = [f for f in all_xlsx if os.path.getmtime(f) >= cutoff]
    else:
        batch = []

    plain_body, html_body = build_email_summary(cfg)
    generated = datetime.now().strftime("%d %b %Y")
    subject = f"Call Center QA Report — {generated}{(' ' + subject_suffix) if subject_suffix else ''}"

    print(f"\n{'═' * 60}")
    print(f"  SENDING EMAIL REPORT")
    print(f"{'═' * 60}")
    print(f"  To: {', '.join(recipients)}")
    print(f"  Attaching {len(batch)} Excel file(s)...")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Attach Excel files
        outer = MIMEMultipart("mixed")
        outer["Subject"] = subject
        outer["From"] = sender
        outer["To"] = ", ".join(recipients)
        outer.attach(MIMEText(plain_body, "plain"))
        outer.attach(MIMEText(html_body, "html"))

        for filepath in batch:
            fname = os.path.basename(filepath)
            with open(filepath, "rb") as f:
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
            outer.attach(part)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, outer.as_string())

        print(f"  ✓ Email sent successfully to {len(recipients)} recipient(s)\n")

    except smtplib.SMTPAuthenticationError:
        print("  ✗ Email failed — incorrect email or password in config.yaml")
        print("    For Gmail: use an App Password (not your regular password)")
        print("    For Office 365: use your normal email password\n")
    except Exception as e:
        print(f"  ✗ Email failed — {e}\n")


def run_step(script, label):
    print(f"\n{'═' * 60}")
    print(f"  STEP: {label}")
    print(f"{'═' * 60}")
    result = subprocess.run([sys.executable, script], check=False)
    if result.returncode != 0:
        print(f"\n❌ {label} failed. Fix errors above and re-run.\n")
        sys.exit(result.returncode)


if __name__ == "__main__":
    # Always run from the folder where this script lives
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description="Call Center QA Pipeline")
    parser.add_argument(
        "--step",
        choices=["transcribe", "analyze", "report", "all"],
        default="all",
        help="Run only a specific pipeline step (default: all)",
    )
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  KIMSHEALTH CALL CENTER QA PIPELINE")
    print("  Powered by OpenAI Whisper + Claude AI")
    print("═" * 60)

    check_dependencies()
    cfg = load_config()
    validate_config(cfg)
    check_api_key(cfg)

    steps = {
        "transcribe": ("1_transcribe.py", "Transcribe MP3 Recordings (Whisper)"),
        "analyze":    ("2_analyze.py",    "Analyze Transcripts (Claude AI)"),
        "report":     ("3_report.py",     "Generate Excel Reports"),
    }

    to_run = list(steps.keys()) if args.step == "all" else [args.step]
    for s in to_run:
        script, label = steps[s]
        run_step(script, label)

    # Send email if reports were generated this run
    if "report" in to_run:
        send_email(cfg)

    print("═" * 60)
    print("  ✅ PIPELINE COMPLETE — Check the outputs/ folder")
    print("═" * 60 + "\n")
