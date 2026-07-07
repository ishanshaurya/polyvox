"""
Step 3: Generate all 7 Excel QA reports from analysis JSON files.

Reports:
  1. CALL_LOG             — Every call with all 10 KPI scores + direction
  2. KPI_SUMMARY          — Per-agent KPI averages
  3. APPOINTMENT_CONV     — Agent / Hospital / Date conversion breakdown
  4. SURGICAL_PROCEDURES  — All surgical procedure enquiries
  5. ESCALATIONS          — Flagged calls sorted by severity
  6. PATIENT_COMPLAINTS   — All patient complaints extracted
  7. AGENT_EVALUATIONS    — Per-agent ratings and training plan

Usage: python 3_report.py
"""

import os
import glob
import json
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    exit(1)


# ── Colour palette ────────────────────────────────────────────────────────────
C_NAVY       = "1F3864"
C_BLUE       = "2E75B6"
C_LIGHT_BLUE = "D6E4F0"
C_RED_DEEP   = "C00000"
C_RED        = "FF0000"
C_ORANGE     = "FF6600"
C_AMBER      = "FFC000"
C_GREEN_DARK = "375623"
C_GREEN_LIGHT= "E2EFDA"
C_RED_BAD    = "9C0006"
C_RED_LIGHT  = "FFC7CE"
C_WHITE      = "FFFFFF"
C_GREY       = "F2F2F2"
C_GOLD       = "FFD700"
C_BROWN      = "7B3F00"
C_PURPLE     = "7030A0"


def hdr_font(size=10, color=C_WHITE):
    return Font(name="Arial", bold=True, size=size, color=color)

def cell_font(size=9, bold=False, color="000000"):
    return Font(name="Arial", size=size, bold=bold, color=color)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def stars_str(n):
    n = max(1, min(5, int(n or 1)))
    return "★" * n + "☆" * (5 - n)

def score_color(score):
    if score is None:
        return None
    try:
        s = float(score)
    except (ValueError, TypeError):
        return None
    if s >= 80:
        return (C_GREEN_LIGHT, C_GREEN_DARK)
    elif s >= 60:
        return ("FFFF99", "7B6000")
    else:
        return (C_RED_LIGHT, C_RED_BAD)

def severity_color(sev):
    return {"Critical": C_RED_DEEP, "High": C_RED, "Medium": C_ORANGE, "Low": C_AMBER}.get(sev, "888888")

def write_title(ws, title, subtitle, col_count):
    ws.merge_cells(f"A1:{get_column_letter(col_count)}1")
    ws["A1"] = title
    ws["A1"].font = Font(name="Arial", bold=True, size=14, color=C_WHITE)
    ws["A1"].fill = fill(C_NAVY)
    ws["A1"].alignment = center()
    ws.row_dimensions[1].height = 28
    ws.merge_cells(f"A2:{get_column_letter(col_count)}2")
    ws["A2"] = subtitle
    ws["A2"].font = Font(name="Arial", size=9, color="CCCCCC", italic=True)
    ws["A2"].fill = fill(C_NAVY)
    ws["A2"].alignment = center()
    ws.row_dimensions[2].height = 16

def write_header(ws, headers, row, bg=C_NAVY):
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=ci, value=h)
        c.font = hdr_font()
        c.fill = fill(bg)
        c.alignment = center()
        c.border = thin_border()
    ws.row_dimensions[row].height = 36

def style_row(ws, row_num, col_count, alternate=False):
    bg = C_GREY if alternate else C_WHITE
    for col in range(1, col_count + 1):
        c = ws.cell(row=row_num, column=col)
        if not c.font or not c.font.bold:
            c.font = cell_font()
        if not c.fill or c.fill.fgColor.rgb in ("00000000", "FFFFFFFF", "00FFFFFF"):
            c.fill = fill(bg)
        c.border = thin_border()
        if c.alignment.horizontal not in ("center",):
            c.alignment = left()

def set_widths(ws, widths):
    for ci, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w


def load_all_analyses(cfg):
    analysis_dir = os.path.join(cfg["output_folder"], "analysis")
    results = []
    for path in sorted(glob.glob(os.path.join(analysis_dir, "*.json"))):
        if path.endswith("_error.txt"):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                data["_json_path"] = path
                results.append(data)
        except Exception as e:
            print(f"  Could not load {path}: {e}")
    return results


def score_to_stars_raw(score, cfg):
    if score is None:
        return 1
    bands = cfg["rating_bands"]
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 1
    if s >= bands[5]: return 5
    elif s >= bands[4]: return 4
    elif s >= bands[3]: return 3
    elif s >= bands[2]: return 2
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 1: CALL LOG
# ─────────────────────────────────────────────────────────────────────────────
def build_call_log(wb, records, cfg):
    ws = wb.create_sheet("Call Log")
    ws.freeze_panes = "A4"
    kpi_names = [k["name"] for k in cfg["kpis"]]

    headers = (
        ["#", "File", "Agent Name", "Hospital", "Direction", "Call Date",
         "Patient Issue", "Call Outcome", "Overall Score", "Stars"]
        + kpi_names
        + ["Unclear?", "Escalation?", "Severity", "Analyzed At"]
    )
    col_count = len(headers)
    write_title(ws, "CALL CENTER QA — CALL LOG",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Total Calls: {len(records)}",
                col_count)
    write_header(ws, headers, 3)

    for i, rec in enumerate(records, 1):
        row = 3 + i
        kpi_scores = rec.get("kpi_scores", {})
        overall = rec.get("overall_score", "")
        escalated = "YES" if rec.get("escalation_required") else "No"
        sev = rec.get("escalation_severity", "None")
        unclear = "Yes" if rec.get("unclear_recording") else ""

        row_data = (
            [i, rec.get("filename", ""), rec.get("agent_name", ""),
             rec.get("hospital", ""), rec.get("direction", ""),
             rec.get("call_date", ""), rec.get("patient_issue", ""),
             rec.get("call_outcome", ""), overall,
             stars_str(rec.get("star_rating", 1))]
            + [kpi_scores.get(k, "") for k in kpi_names]
            + [unclear, escalated, sev if sev != "None" else "",
               rec.get("analyzed_at", "")[:16] if rec.get("analyzed_at") else ""]
        )

        for ci, val in enumerate(row_data, 1):
            ws.cell(row=row, column=ci, value=val)

        style_row(ws, row, col_count, alternate=(i % 2 == 0))

        # Score colour
        sc = ws.cell(row=row, column=9)
        colors = score_color(overall)
        if colors:
            sc.fill = fill(colors[0])
            sc.font = cell_font(bold=True, color=colors[1])
        sc.alignment = center()

        # Stars
        ws.cell(row=row, column=10).font = Font(name="Arial", size=9, color=C_GOLD, bold=True)
        ws.cell(row=row, column=10).alignment = center()

        # KPI colours
        for ki, kname in enumerate(kpi_names):
            kc = ws.cell(row=row, column=11 + ki)
            kc.alignment = center()
            colors = score_color(kpi_scores.get(kname))
            if colors:
                kc.fill = fill(colors[0])
                kc.font = cell_font(color=colors[1])

        base = 11 + len(kpi_names)
        # Unclear
        ws.cell(row=row, column=base).alignment = center()
        if unclear:
            ws.cell(row=row, column=base).font = cell_font(bold=True, color=C_ORANGE)
        # Escalation
        esc_cell = ws.cell(row=row, column=base + 1)
        if rec.get("escalation_required"):
            esc_cell.font = cell_font(bold=True, color=C_RED_DEEP)
        esc_cell.alignment = center()
        # Severity
        sev_cell = ws.cell(row=row, column=base + 2)
        if sev and sev != "None":
            sev_cell.font = cell_font(bold=True, color=severity_color(sev))
        sev_cell.alignment = center()

    widths = [4, 30, 18, 8, 10, 12, 38, 22, 13, 9]
    widths += [14] * len(kpi_names)
    widths += [8, 10, 10, 16]
    set_widths(ws, widths)
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 2: KPI SUMMARY (per-agent averages)
# ─────────────────────────────────────────────────────────────────────────────
def build_kpi_summary(wb, records, cfg):
    ws = wb.create_sheet("KPI Summary")
    ws.freeze_panes = "A4"
    kpi_names = [k["name"] for k in cfg["kpis"]]

    headers = ["#", "Agent Name", "Hospital", "Total Calls"] + kpi_names + ["Overall Avg", "Stars"]
    col_count = len(headers)

    write_title(ws, "KPI PERFORMANCE SUMMARY — PER AGENT",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Average scores per agent per hospital",
                col_count)
    write_header(ws, headers, 3, bg=C_BLUE)

    # Group by agent + hospital (skip missing KPI scores instead of zero-padding)
    groups = defaultdict(lambda: {"calls": [], "kpi_totals": defaultdict(list)})
    for rec in records:
        key = (rec.get("agent_name", "Unknown"), rec.get("hospital", ""))
        try:
            overall_val = rec.get("overall_score")
            if overall_val not in (None, ""):
                groups[key]["calls"].append(float(overall_val))
        except (TypeError, ValueError):
            pass
        for k in kpi_names:
            val = rec.get("kpi_scores", {}).get(k)
            if val in (None, ""):
                continue
            try:
                groups[key]["kpi_totals"][k].append(float(val))
            except (TypeError, ValueError):
                pass

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    sorted_groups = sorted(groups.items(), key=lambda x: (x[0][0], x[0][1]))

    for i, ((agent, hosp), data) in enumerate(sorted_groups, 1):
        row = 3 + i
        avg_overall = avg(data["calls"])
        kpi_avgs = [avg(data["kpi_totals"].get(k, [])) for k in kpi_names]
        stars = score_to_stars_raw(avg_overall, cfg)

        row_data = [i, agent, hosp, len(data["calls"])] + kpi_avgs + [avg_overall, stars_str(stars)]
        for ci, val in enumerate(row_data, 1):
            ws.cell(row=row, column=ci, value=val)

        style_row(ws, row, col_count, alternate=(i % 2 == 0))

        # KPI colours
        for ki, kval in enumerate(kpi_avgs):
            kc = ws.cell(row=row, column=5 + ki)
            kc.alignment = center()
            colors = score_color(kval)
            if colors:
                kc.fill = fill(colors[0])
                kc.font = cell_font(color=colors[1])

        # Overall
        oc = ws.cell(row=row, column=5 + len(kpi_names))
        oc.alignment = center()
        colors = score_color(avg_overall)
        if colors:
            oc.fill = fill(colors[0])
            oc.font = cell_font(bold=True, color=colors[1])

        # Stars
        ws.cell(row=row, column=6 + len(kpi_names)).font = Font(name="Arial", size=9, color=C_GOLD, bold=True)
        ws.cell(row=row, column=6 + len(kpi_names)).alignment = center()

    widths = [4, 20, 8, 10] + [15] * len(kpi_names) + [13, 9]
    set_widths(ws, widths)
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 3: APPOINTMENT CONVERSION
# ─────────────────────────────────────────────────────────────────────────────
def build_appointment_conversion(wb, records, cfg):
    ws = wb.create_sheet("Appointment Conversion")
    ws.freeze_panes = "A4"

    headers = ["#", "Agent Name", "Hospital", "Call Date", "Direction",
               "Appointments Requested", "Appointments Converted",
               "Conversion %", "Walk-in Offered", "Doctor Recommended",
               "Alternative Offered", "Notes"]
    col_count = len(headers)

    write_title(ws, "APPOINTMENT CONVERSION TRACKER",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Track monthly by summing Requested & Converted columns",
                col_count)
    write_header(ws, headers, 3, bg=C_PURPLE)

    # Only calls where an appointment was actually requested
    appt_records = [r for r in records if r.get("appointment_requested")]

    for i, rec in enumerate(appt_records, 1):
        row = 3 + i
        requested = 1 if rec.get("appointment_requested") else 0
        converted = 1 if rec.get("appointment_converted") else 0
        pct = "100%" if requested and converted else ("0%" if requested else "N/A")

        row_data = [
            i, rec.get("agent_name", ""), rec.get("hospital", ""),
            rec.get("call_date", ""), rec.get("direction", ""),
            requested, converted, pct,
            "Yes" if rec.get("walkin_offered") else "No",
            "Yes" if rec.get("doctor_recommendation_made") else "No",
            "Yes" if rec.get("alternative_offered") else "No",
            rec.get("sales_skill_notes", "")
        ]
        for ci, val in enumerate(row_data, 1):
            ws.cell(row=row, column=ci, value=val)

        style_row(ws, row, col_count, alternate=(i % 2 == 0))

        # Conversion % colour
        pct_cell = ws.cell(row=row, column=8)
        pct_cell.alignment = center()
        if pct == "100%":
            pct_cell.font = cell_font(bold=True, color=C_GREEN_DARK)
        elif pct == "0%":
            pct_cell.font = cell_font(bold=True, color=C_RED_BAD)

        for col in [6, 7, 9, 10, 11]:
            ws.cell(row=row, column=col).alignment = center()

    # ── Summary section ──────────────────────────────────────────────────────
    ws.append([])
    summary_row = ws.max_row + 1
    ws.cell(row=summary_row, column=1, value="CONVERSION SUMMARY BY AGENT + HOSPITAL")
    ws.cell(row=summary_row, column=1).font = cell_font(bold=True, size=10, color=C_NAVY)

    summary_headers = ["Agent", "Hospital", "Total Requested", "Total Converted", "Conversion %"]
    for ci, h in enumerate(summary_headers, 1):
        c = ws.cell(row=summary_row + 1, column=ci, value=h)
        c.font = hdr_font()
        c.fill = fill(C_NAVY)
        c.alignment = center()
        c.border = thin_border()

    groups = defaultdict(lambda: {"requested": 0, "converted": 0})
    for rec in appt_records:
        key = (rec.get("agent_name", "Unknown"), rec.get("hospital", ""))
        if rec.get("appointment_requested"):
            groups[key]["requested"] += 1
            if rec.get("appointment_converted"):
                groups[key]["converted"] += 1

    grand_req = 0
    grand_conv = 0
    for si, ((agent, hosp), data) in enumerate(sorted(groups.items()), 1):
        r = summary_row + 2 + si
        req = data["requested"]
        conv = data["converted"]
        grand_req += req
        grand_conv += conv
        pct = f"{round(conv/req*100)}%" if req else "N/A"
        row_data = [agent, hosp, req, conv, pct]
        for ci, val in enumerate(row_data, 1):
            c = ws.cell(row=r, column=ci, value=val)
            c.border = thin_border()
            c.font = cell_font()
            c.alignment = center() if ci > 2 else left()
        colors = score_color((conv / req * 100) if req else None)
        pct_c = ws.cell(row=r, column=5)
        if colors:
            pct_c.fill = fill(colors[0])
            pct_c.font = cell_font(bold=True, color=colors[1])

    # Grand total row
    grand_row = summary_row + 2 + len(groups) + 1
    grand_pct = f"{round(grand_conv/grand_req*100)}%" if grand_req else "N/A"
    grand_data = ["TOTAL — All Agents Combined", "", grand_req, grand_conv, grand_pct]
    for ci, val in enumerate(grand_data, 1):
        c = ws.cell(row=grand_row, column=ci, value=val)
        c.border = thin_border()
        c.font = cell_font(bold=True, color=C_WHITE)
        c.fill = fill(C_NAVY)
        c.alignment = center() if ci > 2 else left()
    # Colour the grand total % by score
    grand_colors = score_color((grand_conv / grand_req * 100) if grand_req else None)
    grand_pct_c = ws.cell(row=grand_row, column=5)
    if grand_colors:
        grand_pct_c.fill = fill(grand_colors[0])
        grand_pct_c.font = cell_font(bold=True, color=grand_colors[1])

    set_widths(ws, [4, 20, 10, 12, 10, 22, 22, 14, 16, 20, 18, 50])
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 4: SURGICAL PROCEDURES
# ─────────────────────────────────────────────────────────────────────────────
def build_surgical_procedures(wb, records, cfg):
    ws = wb.create_sheet("Surgical Procedures")
    ws.freeze_panes = "A4"

    surgical = [r for r in records if r.get("surgical_procedure_requested")]

    headers = ["#", "File", "Agent Name", "Hospital", "Call Date",
               "Procedure Requested", "Available at Hospital?",
               "Booking Attempted?", "Agent's Actions", "Sales Notes",
               "Escalated?", "Score"]
    col_count = len(headers)

    write_title(ws, "SURGICAL PROCEDURE ENQUIRIES",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Total Enquiries: {len(surgical)}",
                col_count)
    write_header(ws, headers, 3, bg="203864")

    if not surgical:
        ws.merge_cells(f"A4:{get_column_letter(col_count)}4")
        ws["A4"] = "No surgical procedure enquiries found in analyzed calls."
        ws["A4"].font = cell_font(bold=True, color=C_GREEN_DARK)
        ws["A4"].fill = fill(C_GREEN_LIGHT)
        ws["A4"].alignment = center()
    else:
        for i, rec in enumerate(surgical, 1):
            row = 3 + i
            row_data = [
                i, rec.get("filename", ""), rec.get("agent_name", ""),
                rec.get("hospital", ""), rec.get("call_date", ""),
                rec.get("surgical_procedure_name", ""),
                rec.get("procedure_available_at_hospital", ""),
                "Yes" if rec.get("procedure_booking_attempted") else "No",
                rec.get("procedure_sales_notes", ""),
                rec.get("sales_skill_notes", ""),
                "Yes" if rec.get("escalation_required") else "No",
                rec.get("overall_score", "")
            ]
            for ci, val in enumerate(row_data, 1):
                ws.cell(row=row, column=ci, value=val)

            style_row(ws, row, col_count, alternate=(i % 2 == 0))

            avail = rec.get("procedure_available_at_hospital", "")
            avail_cell = ws.cell(row=row, column=7)
            avail_cell.alignment = center()
            if avail == "Yes":
                avail_cell.font = cell_font(bold=True, color=C_GREEN_DARK)
            elif avail == "No":
                avail_cell.font = cell_font(bold=True, color=C_RED_BAD)

            colors = score_color(rec.get("overall_score"))
            sc = ws.cell(row=row, column=12)
            if colors:
                sc.fill = fill(colors[0])
                sc.font = cell_font(bold=True, color=colors[1])
            sc.alignment = center()

    set_widths(ws, [4, 30, 18, 8, 12, 28, 18, 16, 50, 50, 10, 10])
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 5: ESCALATIONS
# ─────────────────────────────────────────────────────────────────────────────
def build_escalations(wb, records, cfg):
    ws = wb.create_sheet("Escalations")
    ws.freeze_panes = "A4"

    escalated = [r for r in records if r.get("escalation_required")]
    sev_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    escalated.sort(key=lambda r: sev_order.get(r.get("escalation_severity", "Low"), 4))

    headers = ["#", "File", "Agent Name", "Hospital", "Call Date", "Severity",
               "Escalation Reason", "Patient Issue", "Overall Score",
               "Unclear Recording?", "Call Outcome", "Action Required"]
    col_count = len(headers)

    write_title(ws, "ESCALATION REGISTER",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Total Escalations: {len(escalated)}",
                col_count)
    write_header(ws, headers, 3, bg=C_RED_DEEP)

    if not escalated:
        ws.merge_cells(f"A4:{get_column_letter(col_count)}4")
        ws["A4"] = "No escalations found — all calls within acceptable standards."
        ws["A4"].font = cell_font(bold=True, color=C_GREEN_DARK)
        ws["A4"].fill = fill(C_GREEN_LIGHT)
        ws["A4"].alignment = center()
    else:
        for i, rec in enumerate(escalated, 1):
            row = 3 + i
            sev = rec.get("escalation_severity", "Low")
            action = {
                "Critical": "Immediate manager review + agent suspended pending investigation",
                "High": "Manager review within 24 hours + corrective action plan",
                "Medium": "Supervisor review within 48 hours + coaching session",
                "Low": "Team lead review + verbal guidance",
            }.get(sev, "Review required")

            row_data = [
                i, rec.get("filename", ""), rec.get("agent_name", ""),
                rec.get("hospital", ""), rec.get("call_date", ""), sev,
                rec.get("escalation_reason", ""), rec.get("patient_issue", ""),
                rec.get("overall_score", ""),
                "Yes" if rec.get("unclear_recording") else "No",
                rec.get("call_outcome", ""), action
            ]
            for ci, val in enumerate(row_data, 1):
                ws.cell(row=row, column=ci, value=val)

            style_row(ws, row, col_count, alternate=(i % 2 == 0))

            sev_cell = ws.cell(row=row, column=6)
            sev_cell.font = cell_font(bold=True, color=severity_color(sev))
            sev_cell.alignment = center()

            colors = score_color(rec.get("overall_score"))
            sc = ws.cell(row=row, column=9)
            if colors:
                sc.fill = fill(colors[0])
                sc.font = cell_font(bold=True, color=colors[1])
            sc.alignment = center()

            ws.cell(row=row, column=12).font = cell_font(bold=True, color="7B0000")
            ws.row_dimensions[row].height = 40

    set_widths(ws, [4, 28, 18, 8, 12, 10, 50, 34, 13, 14, 22, 48])
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 6: PATIENT COMPLAINTS
# ─────────────────────────────────────────────────────────────────────────────
def build_complaints(wb, records, cfg):
    ws = wb.create_sheet("Patient Complaints")
    ws.freeze_panes = "A4"

    all_complaints = []
    for rec in records:
        for c in rec.get("patient_complaints", []):
            if c and str(c).strip():
                all_complaints.append({
                    "agent": rec.get("agent_name", ""),
                    "hospital": rec.get("hospital", ""),
                    "file": rec.get("filename", ""),
                    "date": rec.get("call_date", ""),
                    "complaint": str(c).strip(),
                    "issue": rec.get("patient_issue", ""),
                    "outcome": rec.get("call_outcome", ""),
                    "score": rec.get("overall_score", ""),
                    "escalated": "Yes" if rec.get("escalation_required") else "No",
                })

    headers = ["#", "Agent Name", "Hospital", "File", "Call Date",
               "Patient Complaint", "Call Topic", "Call Outcome", "Score", "Escalated?"]
    col_count = len(headers)

    write_title(ws, "PATIENT COMPLAINTS LOG",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Total Complaints: {len(all_complaints)}",
                col_count)
    write_header(ws, headers, 3, bg=C_BROWN)

    if not all_complaints:
        ws.merge_cells(f"A4:{get_column_letter(col_count)}4")
        ws["A4"] = "No patient complaints detected in analyzed calls."
        ws["A4"].font = cell_font(bold=True, color=C_GREEN_DARK)
        ws["A4"].fill = fill(C_GREEN_LIGHT)
        ws["A4"].alignment = center()
    else:
        for i, comp in enumerate(all_complaints, 1):
            row = 3 + i
            row_data = [i, comp["agent"], comp["hospital"], comp["file"],
                        comp["date"], comp["complaint"], comp["issue"],
                        comp["outcome"], comp["score"], comp["escalated"]]
            for ci, val in enumerate(row_data, 1):
                ws.cell(row=row, column=ci, value=val)
            style_row(ws, row, col_count, alternate=(i % 2 == 0))

            ws.cell(row=row, column=6).font = cell_font(bold=True, color=C_BROWN)
            colors = score_color(comp["score"])
            sc = ws.cell(row=row, column=9)
            if colors:
                sc.fill = fill(colors[0])
                sc.font = cell_font(bold=True, color=colors[1])
            sc.alignment = center()
            esc = ws.cell(row=row, column=10)
            if comp["escalated"] == "Yes":
                esc.font = cell_font(bold=True, color=C_RED_DEEP)
            esc.alignment = center()
            ws.row_dimensions[row].height = 32

    set_widths(ws, [4, 18, 8, 28, 12, 58, 34, 22, 10, 12])
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# REPORT 7: AGENT EVALUATIONS
# ─────────────────────────────────────────────────────────────────────────────
def build_agent_evaluations(wb, records, cfg):
    ws = wb.create_sheet("Agent Evaluations")
    ws.freeze_panes = "A4"
    kpi_names = [k["name"] for k in cfg["kpis"]]

    agents = defaultdict(lambda: {
        "calls": [], "kpi_totals": defaultdict(list),
        "escalations": 0, "complaints": 0,
        "training_votes": defaultdict(int),
        "improvement_areas": [],
    })

    for rec in records:
        agent = rec.get("agent_name", "Unknown Agent")
        ag = agents[agent]
        overall_val = rec.get("overall_score")
        if overall_val not in (None, ""):
            try:
                ag["calls"].append(float(overall_val))
            except (TypeError, ValueError):
                pass
        for k in kpi_names:
            val = rec.get("kpi_scores", {}).get(k)
            if val in (None, ""):
                continue
            try:
                ag["kpi_totals"][k].append(float(val))
            except (TypeError, ValueError):
                pass
        if rec.get("escalation_required"):
            ag["escalations"] += 1
        ag["complaints"] += len([c for c in rec.get("patient_complaints", []) if c])
        for t in rec.get("training_recommended", []):
            if t:
                ag["training_votes"][t] += 1
        ag["improvement_areas"].extend(rec.get("improvement_areas", []))

    headers = (
        ["#", "Agent Name", "Total Calls", "Avg Score", "Star Rating",
         "Escalations", "Complaints"]
        + [f"Avg: {k}" for k in kpi_names]
        + ["Top Training Need 1", "Top Training Need 2", "Top Training Need 3",
           "Key Improvement Area", "Performance Band"]
    )
    col_count = len(headers)

    write_title(ws, "AGENT PERFORMANCE EVALUATION",
                f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}  |  Agents: {len(agents)}",
                col_count)
    write_header(ws, headers, 3)

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    def perf_band(score):
        if score is None: return "Insufficient Data"
        if score >= 85: return "Excellent"
        elif score >= 70: return "Good"
        elif score >= 55: return "Average"
        elif score >= 40: return "Needs Improvement"
        return "Poor — Urgent Action Required"

    for i, (agent_name, ag) in enumerate(
        sorted(agents.items(), key=lambda x: avg(x[1]["calls"]) or 0, reverse=True), 1
    ):
        row = 3 + i
        avg_score = avg(ag["calls"])
        stars = score_to_stars_raw(avg_score, cfg)
        kpi_avgs = [avg(ag["kpi_totals"].get(k, [])) for k in kpi_names]

        top_training = sorted(ag["training_votes"].items(), key=lambda x: x[1], reverse=True)
        t1 = top_training[0][0] if len(top_training) > 0 else ""
        t2 = top_training[1][0] if len(top_training) > 1 else ""
        t3 = top_training[2][0] if len(top_training) > 2 else ""

        area_counts = defaultdict(int)
        for a in ag["improvement_areas"]:
            if a:
                area_counts[a.strip()] += 1
        top_area = max(area_counts, key=area_counts.get) if area_counts else ""

        row_data = (
            [i, agent_name, len(ag["calls"]), avg_score,
             stars_str(stars), ag["escalations"], ag["complaints"]]
            + kpi_avgs
            + [t1, t2, t3, top_area, perf_band(avg_score)]
        )
        for ci, val in enumerate(row_data, 1):
            ws.cell(row=row, column=ci, value=val)

        style_row(ws, row, col_count, alternate=(i % 2 == 0))

        colors = score_color(avg_score)
        sc = ws.cell(row=row, column=4)
        if colors:
            sc.fill = fill(colors[0])
            sc.font = cell_font(bold=True, color=colors[1])
        sc.alignment = center()

        ws.cell(row=row, column=5).font = Font(name="Arial", size=9, color=C_GOLD, bold=True)
        ws.cell(row=row, column=5).alignment = center()

        esc_c = ws.cell(row=row, column=6)
        esc_c.alignment = center()
        if ag["escalations"] > 0:
            esc_c.font = cell_font(bold=True, color=C_RED_DEEP)

        comp_c = ws.cell(row=row, column=7)
        comp_c.alignment = center()
        if ag["complaints"] > 0:
            comp_c.font = cell_font(bold=True, color=C_ORANGE)

        for ki, kval in enumerate(kpi_avgs):
            kc = ws.cell(row=row, column=8 + ki)
            kc.alignment = center()
            colors = score_color(kval)
            if colors:
                kc.fill = fill(colors[0])
                kc.font = cell_font(color=colors[1])

        ws.cell(row=row, column=8 + len(kpi_names) + 3).font = cell_font(bold=True)
        ws.cell(row=row, column=8 + len(kpi_names) + 3).alignment = center()
        ws.row_dimensions[row].height = 36

    widths = [4, 20, 12, 12, 12, 14, 12] + [16] * len(kpi_names) + [40, 40, 40, 50, 28]
    set_widths(ws, widths)
    ws.sheet_view.showGridLines = False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def generate_reports(cfg):
    records = load_all_analyses(cfg)
    if not records:
        print("\n  No analysis results found. Run 2_analyze.py first.\n")
        return

    output_dir = cfg["output_folder"]
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    print(f"\n  Generating Excel reports for {len(records)} calls...\n")

    def make(name):
        return os.path.join(output_dir, f"{name}_{ts}.xlsx")

    files = {
        "CALL_LOG":            make("CALL_LOG"),
        "KPI_SUMMARY":         make("KPI_SUMMARY"),
        "APPOINTMENT_CONV":    make("APPOINTMENT_CONVERSION"),
        "SURGICAL":            make("SURGICAL_PROCEDURES"),
        "ESCALATIONS":         make("ESCALATIONS"),
        "COMPLAINTS":          make("PATIENT_COMPLAINTS"),
        "AGENT_EVAL":          make("AGENT_EVALUATIONS"),
    }

    builders = [
        ("CALL_LOG",         build_call_log,              "Call Log"),
        ("KPI_SUMMARY",      build_kpi_summary,           "KPI Summary"),
        ("APPOINTMENT_CONV", build_appointment_conversion, "Appointment Conversion"),
        ("SURGICAL",         build_surgical_procedures,   "Surgical Procedures"),
        ("ESCALATIONS",      build_escalations,           "Escalations"),
        ("COMPLAINTS",       build_complaints,            "Patient Complaints"),
        ("AGENT_EVAL",       build_agent_evaluations,     "Agent Evaluations"),
    ]

    for key, builder, label in builders:
        wb = Workbook()
        wb.remove(wb.active)
        builder(wb, records, cfg)
        wb.save(files[key])
        fname = os.path.basename(files[key])
        print(f"  ✓ {label:<28} → {fname}")

    esc_count = len([r for r in records if r.get("escalation_required")])
    comp_count = sum(len([c for c in r.get("patient_complaints", []) if c]) for r in records)
    surg_count = len([r for r in records if r.get("surgical_procedure_requested")])
    appt_count = len([r for r in records if r.get("appointment_requested")])
    converted  = len([r for r in records if r.get("appointment_converted")])

    print(f"\n  {'─'*56}")
    print(f"  All reports saved to: {os.path.abspath(output_dir)}/")
    print(f"\n  Summary:")
    print(f"    Calls analyzed:           {len(records)}")
    print(f"    Escalations flagged:      {esc_count}")
    print(f"    Patient complaints:       {comp_count}")
    print(f"    Surgical enquiries:       {surg_count}")
    if appt_count:
        pct = round(converted / appt_count * 100)
        print(f"    Appointment requests:     {appt_count}  |  Converted: {converted}  ({pct}%)")
    else:
        print(f"    Appointment requests:     0")
    print()


if __name__ == "__main__":
    import argparse

    from callqa.config.loader import load_config
    from callqa.reports.templates_v1 import generate

    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=None, help="Batch number for report scope")
    parser.add_argument(
        "--batch-only",
        action="store_true",
        help="Include only this batch (default: cumulative through batch)",
    )
    args = parser.parse_args()
    cfg = load_config()

    template = (cfg.get("report_template") or "templates_v1").lower()
    if template == "templates_v1":
        generate(cfg, batch=args.batch, batch_only=args.batch_only)
    else:
        from callqa.reports.excel_legacy import generate_reports
        generate_reports(cfg)
