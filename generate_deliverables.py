"""Generate FindMe PowerPoint presentation and Word report with screenshots."""

import os, sys, time, subprocess, shutil
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from docx import Document
from docx.shared import Inches as DocInches, Pt as DocPt, RGBColor as DocRGB
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

OUT_DIR = Path("D:/capstone/findme/output")
SCREENSHOT_DIR = OUT_DIR / "screenshots"
FLASK_URL = "http://127.0.0.1:5000"
FLASK_DIR = "D:/capstone/findme"
ADMIN_EMAIL = "admin@cavendish.ac.ug"
ADMIN_PASS = "password123"
STUDENT_EMAIL = "john.musinguzi@cavendish.ac.ug"
STUDENT_PASS = "password123"

# ── Color palette (professional blue-based) ──
NAVY     = RGBColor(0x0A, 0x16, 0x28)
DARK_BLUE = RGBColor(0x1E, 0x3A, 0x5F)
BLUE     = RGBColor(0x29, 0x80, 0xB9)
LIGHT_BLUE = RGBColor(0x5A, 0x9B, 0xD0)
ACCENT   = RGBColor(0x34, 0x98, 0xDB)
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
DARK     = RGBColor(0x2C, 0x3E, 0x50)
GRAY     = RGBColor(0x6B, 0x7C, 0x8E)
LIGHT_GRAY = RGBColor(0xF0, 0xF3, 0xF7)
GREEN    = RGBColor(0x27, 0xAE, 0x60)
RED      = RGBColor(0xE7, 0x4C, 0x3C)
ORANGE   = RGBColor(0xF3, 0x9C, 0x12)
GOLD     = RGBColor(0xD4, 0xAC, 0x0D)


# ══════════════════════════════════════════════
#  SCREENSHOT CAPTURE
# ══════════════════════════════════════════════

def ensure_dir(path):
    path.mkdir(parents=True, exist_ok=True)

def start_flask():
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=FLASK_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)
    return proc

def stop_flask(proc):
    proc.terminate()
    proc.wait()

def get_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-gpu")
    opts.binary_location = "C:/Program Files/Google/Chrome/Application/chrome.exe"
    return webdriver.Chrome(options=opts)

def screenshot(driver, url, filename, wait_for=None, login_first=False):
    driver.get(url)
    time.sleep(1.5)
    if wait_for:
        try:
            WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for)))
        except:
            pass
    time.sleep(0.5)
    path = SCREENSHOT_DIR / filename
    driver.save_screenshot(str(path))
    print(f"  [OK] {filename}")
    return path

def capture_all_screenshots():
    ensure_dir(SCREENSHOT_DIR)
    driver = get_driver()
    results = {}
    try:
        # -- Public pages --
        results["home"] = screenshot(driver, FLASK_URL + "/", "01_home.png", ".hero")
        results["about"] = screenshot(driver, FLASK_URL + "/about", "02_about.png", ".about-content")
        results["register"] = screenshot(driver, FLASK_URL + "/register", "03_register.png", ".form-container")
        results["login"] = screenshot(driver, FLASK_URL + "/login", "04_login.png", ".form-container")

        # -- Login as admin --
        driver.get(FLASK_URL + "/login")
        time.sleep(1)
        driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
        driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        time.sleep(2)

        results["admin_dashboard"] = screenshot(driver, FLASK_URL + "/admin/dashboard",
            "05_admin_dashboard.png", ".stats-grid")
        results["admin_matches"] = screenshot(driver, FLASK_URL + "/admin/matches",
            "06_admin_matches.png", ".match-review-card")
        results["admin_lost"] = screenshot(driver, FLASK_URL + "/admin/lost-items",
            "07_admin_lost_items.png", ".table-responsive")
        results["admin_found"] = screenshot(driver, FLASK_URL + "/admin/found-items",
            "08_admin_found_items.png", ".table-responsive")
        results["admin_users"] = screenshot(driver, FLASK_URL + "/admin/users",
            "09_admin_users.png", ".table-responsive")

        # -- Logout, login as student --
        driver.get(FLASK_URL + "/logout")
        time.sleep(1)
        driver.get(FLASK_URL + "/login")
        time.sleep(1)
        try:
            driver.find_element(By.ID, "email").send_keys(STUDENT_EMAIL)
            driver.find_element(By.ID, "password").send_keys(STUDENT_PASS)
            driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
            time.sleep(2)
        except:
            print("  [WARN] Student login failed, using admin session")
            driver.get(FLASK_URL + "/login")
            time.sleep(1)
            driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
            driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
            driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
            time.sleep(2)

        results["dashboard"] = screenshot(driver, FLASK_URL + "/dashboard",
            "10_dashboard.png", ".stats-grid")
        results["report_lost"] = screenshot(driver, FLASK_URL + "/report-lost",
            "11_report_lost.png", ".form-section")
        results["report_found"] = screenshot(driver, FLASK_URL + "/report-found",
            "12_report_found.png", ".form-section")
        results["my_reports"] = screenshot(driver, FLASK_URL + "/my-reports",
            "13_my_reports.png", ".table-responsive")
        results["search"] = screenshot(driver, FLASK_URL + "/search",
            "14_search.png", ".search-form")
        results["matches"] = screenshot(driver, FLASK_URL + "/matches",
            "15_matches.png", ".match-review-card")
        try:
            results["match_detail"] = screenshot(driver, FLASK_URL + "/match/1",
                "16_match_detail.png", ".match-score-banner")
        except:
            results["match_detail"] = None
        try:
            results["item_detail"] = screenshot(driver, FLASK_URL + "/item/lost/1",
                "17_item_detail.png", ".item-hero-image")
        except:
            results["item_detail"] = None
        results["notifications"] = screenshot(driver, FLASK_URL + "/notifications",
            "18_notifications.png", ".notification-list")
        results["profile"] = screenshot(driver, FLASK_URL + "/profile",
            "19_profile.png", ".detail-grid")

        print(f"\n  Captured {len(results)} screenshots")
    finally:
        driver.quit()
    return {k: v for k, v in results.items() if v is not None}


# ══════════════════════════════════════════════
#  POWERPOINT GENERATION
# ══════════════════════════════════════════════

def add_bg(slide, color=NAVY):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color

def add_text_box(slide, left, top, width, height, text, font_size=18,
                 color=WHITE, bold=False, alignment=PP_ALIGN.LEFT, font_name="Calibri"):
    txBox = slide.shapes.add_textbox(Emu(left), Emu(top), Emu(width), Emu(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.color.rgb = color
    p.font.bold = bold
    p.font.name = font_name
    p.alignment = alignment
    return txBox

def add_shape_box(slide, left, top, width, height, fill_color=None, line_color=None):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Emu(left), Emu(top), Emu(width), Emu(height)
    )
    shape.line.fill.background()
    if fill_color:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
    if line_color:
        shape.line.color.rgb = line_color
        shape.line.width = Pt(1)
    return shape

def add_image_safe(slide, img_path, left, top, width, height=None):
    if img_path and os.path.exists(img_path):
        if height:
            slide.shapes.add_picture(str(img_path), Emu(left), Emu(top), Emu(width), Emu(height))
        else:
            slide.shapes.add_picture(str(img_path), Emu(left), Emu(top), Emu(width))
        return True
    return False

def create_title_slide(prs, title, subtitle=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    add_bg(slide, NAVY)
    # accent bar
    add_shape_box(slide, 0, 2800000, 9144000, 60000, ACCENT)
    add_text_box(slide, 800000, 1600000, 7500000, 1200000, title,
                 font_size=40, color=WHITE, bold=True)
    if subtitle:
        add_text_box(slide, 800000, 2900000, 7500000, 800000, subtitle,
                     font_size=20, color=LIGHT_BLUE, bold=False)
    add_text_box(slide, 800000, 5200000, 7500000, 400000,
                 "Cavendish University Uganda | Lost & Found Management System",
                 font_size=13, color=GRAY)
    return slide

def create_section_slide(prs, title, subtitle=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, DARK_BLUE)
    add_shape_box(slide, 0, 2000000, 9144000, 40000, ACCENT)
    add_text_box(slide, 800000, 800000, 7500000, 800000, title,
                 font_size=32, color=WHITE, bold=True)
    if subtitle:
        add_text_box(slide, 800000, 2400000, 7500000, 600000, subtitle,
                     font_size=16, color=LIGHT_BLUE)
    return slide

def create_content_slide(prs, title, bullets, img_path=None, img_caption=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    # top accent
    add_shape_box(slide, 0, 0, 9144000, 70000, ACCENT)
    # title
    add_shape_box(slide, 0, 70000, 9144000, 600000, LIGHT_GRAY)
    add_text_box(slide, 400000, 120000, 8300000, 500000, title,
                 font_size=24, color=DARK_BLUE, bold=True)

    left_col = 400000
    right_col = 4800000
    content_top = 900000

    if img_path and os.path.exists(img_path):
        # Image on right
        add_image_safe(slide, img_path, right_col, content_top, 4000000, 2400000)
        if img_caption:
            add_text_box(slide, right_col, 3350000, 4000000, 300000, img_caption,
                         font_size=10, color=GRAY, alignment=PP_ALIGN.CENTER)
        # Bullets on left
        text = "\n".join(f"\u2022  {b}" for b in bullets)
        add_text_box(slide, left_col, content_top, 4000000, 3000000, text,
                     font_size=15, color=DARK, font_name="Calibri")
    else:
        text = "\n".join(f"\u2022  {b}" for b in bullets)
        add_text_box(slide, left_col, content_top, 8300000, 3500000, text,
                     font_size=15, color=DARK, font_name="Calibri")
    return slide

def create_two_img_slide(prs, title, bullets, img1_path, img2_path, cap1="", cap2=""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(slide, WHITE)
    add_shape_box(slide, 0, 0, 9144000, 70000, ACCENT)
    add_shape_box(slide, 0, 70000, 9144000, 600000, LIGHT_GRAY)
    add_text_box(slide, 400000, 120000, 8300000, 500000, title,
                 font_size=22, color=DARK_BLUE, bold=True)

    content_top = 900000
    # Two images side by side
    if img1_path and os.path.exists(img1_path):
        add_image_safe(slide, img1_path, 300000, content_top, 4100000, 2400000)
        if cap1:
            add_text_box(slide, 300000, 3350000, 4100000, 250000, cap1,
                         font_size=9, color=GRAY, alignment=PP_ALIGN.CENTER)
    if img2_path and os.path.exists(img2_path):
        add_image_safe(slide, img2_path, 4700000, content_top, 4100000, 2400000)
        if cap2:
            add_text_box(slide, 4700000, 3350000, 4100000, 250000, cap2,
                         font_size=9, color=GRAY, alignment=PP_ALIGN.CENTER)

    text = "\n".join(f"\u2022  {b}" for b in bullets)
    add_text_box(slide, 400000, 3650000, 8300000, 1500000, text,
                 font_size=14, color=DARK, font_name="Calibri")
    return slide


def generate_pptx(screenshots):
    prs = Presentation()
    prs.slide_width = Emu(9144000)   # 10" 
    prs.slide_height = Emu(5715000)  # 7.5"

    # ═══ TITLE ═══
    create_title_slide(prs,
        "FindMe\nCavendish University Lost & Found System",
        "An AI-Powered Lost and Found Item Management System")

    # ═══ AGENDA ═══
    create_content_slide(prs, "Agenda", [
        "Problem Statement & Objectives",
        "System Overview & Architecture",
        "Key Features & Screenshots",
        "AI-Powered Matching Engine",
        "User Roles: Student & Admin Workflows",
        "Technology Stack",
        "Demo Walkthrough",
        "Conclusion & Q&A"
    ])

    # ═══ PROBLEM ═══
    create_content_slide(prs, "Problem Statement", [
        "Students and staff frequently lose personal items on campus",
        "No centralized system for reporting and recovering lost items",
        "Manual processes are inefficient and unreliable",
        "Unable to leverage AI for automated item matching",
        "Need for a secure, role-based platform with real-time notifications"
    ])

    # ═══ SYSTEM OVERVIEW ═══
    create_content_slide(prs, "System Overview", [
        "Web-based platform built with Flask (Python 3.13)",
        "Three-tier architecture: Presentation, Business Logic, Data",
        "MySQL database for persistent storage",
        "AI-powered matching engine using content-based analysis",
        "Role-based access: Admin, Student, Lecturer",
        "Responsive design for desktop and mobile access"
    ])

    # ═══ STUDENT FEATURES ═══
    create_section_slide(prs, "User Features", "Student & Staff Functionality")

    # Dashboard
    create_content_slide(prs, "Dashboard",
        ["Quick overview of platform activity and personal stats",
         "Action cards for rapid reporting and search",
         "Recent matches and notifications at a glance",
         "Linked statistics for lost/found items and matches"],
        screenshots.get("dashboard"), "User Dashboard")

    # Report Lost
    create_content_slide(prs, "Report Lost Item",
        ["Step-by-step form with reporter and item details",
         "Fields for category, brand, model, color, serial number",
         "Date/time and location of loss",
         "Optional image upload with preview",
         "Auto-populates user info from session"],
        screenshots.get("report_lost"), "Report Lost Item Form")

    # Report Found
    create_content_slide(prs, "Report Found Item",
        ["Intuitive form for recording found items",
         "Current location tracking for custody chain",
         "Image upload for visual identification",
         "Categorized with locations and descriptions"],
        screenshots.get("report_found"), "Report Found Item Form")

    # My Reports
    create_content_slide(prs, "My Reports",
        ["Centralized view of all submitted reports",
         "Real-time status tracking for each item",
         "Direct links to item details and AI matches",
         "Filter by type (lost/found) and status"],
        screenshots.get("my_reports"), "My Reports Page")

    # Search
    create_content_slide(prs, "Search Items",
        ["Powerful multi-criteria search engine",
         "Filter by keywords, category, location, type, status",
         "Instant results from the entire database",
         "Direct navigation to item details"],
        screenshots.get("search"), "Search Page")

    # AI Matches
    create_content_slide(prs, "AI Matching Results",
        ["Automated matching of lost vs found items",
         "Confidence scores with Very High / High / Possible / Low levels",
         "Side-by-side comparison of matched items",
         "Detailed AI explanation for each match"],
        screenshots.get("matches"), "AI Matches for User")

    # Match Detail
    if screenshots.get("match_detail"):
        create_content_slide(prs, "Match Detail View",
            ["Comprehensive comparison of matched items",
             "Visual score circle with confidence percentage",
             "Side-by-side images and attribute tables",
             "AI-generated explanation of matching logic"],
            screenshots.get("match_detail"), "Match Detail Page")

    # Notifications
    create_content_slide(prs, "Notifications",
        ["Real-time alerts for new matches and status changes",
         "Unread indicators with count badge in navigation",
         "Categorized notifications for easy triage",
         "One-click navigation to relevant items"],
        screenshots.get("notifications"), "Notifications Center")

    # ═══ ADMIN FEATURES ═══
    create_section_slide(prs, "Admin Features", "Administrative Functionality")

    # Admin Dashboard
    create_content_slide(prs, "Admin Dashboard",
        ["Platform-wide statistics and KPIs",
         "Pending verifications and match approvals",
         "Recent activity log and user management",
         "Data-driven insights for system monitoring"],
        screenshots.get("admin_dashboard"), "Admin Dashboard")

    # Admin AI Matches
    create_content_slide(prs, "Admin: AI Match Management",
        ["Review AI-generated matches with full detail",
         "Approve or reject matches with one click",
         "View comparison images and AI explanations",
         "Manage match lifecycle from pending to resolved"],
        screenshots.get("admin_matches"), "Admin AI Matches")

    # Admin Lost Items
    create_content_slide(prs, "Admin: Lost & Found Items",
        ["Complete inventory of all reported items",
         "Status management and updates",
         "Advanced filtering and search",
         "Bulk operations and reporting"],
        screenshots.get("admin_lost"), "Admin Lost Items")

    # Admin Users
    create_content_slide(prs, "Admin: User Management",
        ["Role-based user administration",
         "Account activation/deactivation",
         "Student, lecturer, and admin role assignment",
         "User activity monitoring"],
        screenshots.get("admin_users"), "Admin Users Management")

    # ═══ AI MATCHING ═══
    create_section_slide(prs, "AI Matching Engine", "How It Works")

    create_content_slide(prs, "AI Matching Algorithm",
        ["Content-based analysis using item attributes",
         "Compares: item name, brand, model, color, category, location",
         "Fuzzy string matching for partial text similarity",
         "Location proximity scoring",
         "Weighted scoring system with configurable thresholds",
         "Explanation generation for transparency and trust"],
        None)

    # ═══ TECH STACK ═══
    create_section_slide(prs, "Technology Stack", "Tools & Technologies")

    create_content_slide(prs, "Technology Stack", [
        "Backend: Python 3.13, Flask, Flask-MySQLdb",
        "Frontend: Jinja2 Templates, HTML5, CSS3, JavaScript",
        "Database: MySQL 8.0 with relational schema",
        "AI/ML: Custom matching engine (content-based)",
        "Security: bcrypt password hashing, session management",
        "File Storage: Local filesystem with image optimization",
        "Email: Flask-Mail console backend for development",
        "Design: Font Awesome icons, responsive CSS grid"
    ])

    # ═══ DEMO ═══
    create_section_slide(prs, "Demonstration", "Live Walkthrough")

    create_content_slide(prs, "User Registration & Login",
        ["New users can register with student/staff details",
         "Faculty and course selection for institutional context",
         "Secure password hashing with bcrypt",
         "Role-based redirection after login"],
        screenshots.get("register"), "Registration Page")

    create_content_slide(prs, "Complete User Workflow",
        ["1. Register/Login to the platform",
         "2. Report a lost or found item with details",
         "3. AI automatically finds potential matches",
         "4. Review matches with confidence scores",
         "5. Coordinate recovery through the platform",
         "6. Close the loop with verified recoveries"],
        screenshots.get("dashboard"), "User Dashboard - Starting Point")

    # ═══ CONCLUSION ═══
    slide = create_title_slide(prs,
        "Thank You",
        "FindMe - Recovering What Matters Most")
    add_text_box(slide, 800000, 4200000, 7500000, 500000,
                 "Questions & Discussion\nCavendish University Uganda",
                 font_size=16, color=LIGHT_BLUE, alignment=PP_ALIGN.CENTER)

    # Save
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    pptx_path = OUT_DIR / f"FindMe_Presentation_{ts}.pptx"
    prs.save(str(pptx_path))
    print(f"\n  [OK] PowerPoint saved: {pptx_path}")
    return pptx_path


# ══════════════════════════════════════════════
#  WORD REPORT GENERATION
# ══════════════════════════════════════════════

def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = DocRGB(0x1E, 0x3A, 0x5F)
    return h

def add_para(doc, text, bold=False, italic=False, size=11, color=None, align=None, space_after=6):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = DocPt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = color
    if align:
        p.alignment = align
    p.paragraph_format.space_after = DocPt(space_after)
    return p

def add_bullet(doc, text, level=0, size=11):
    p = doc.add_paragraph(text, style='List Bullet')
    p.paragraph_format.left_indent = DocPt(36 + level * 18)
    for run in p.runs:
        run.font.size = DocPt(size)
    return p

def add_image_doc(doc, img_path, caption="", width=5.5):
    if img_path and os.path.exists(img_path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(img_path), width=DocInches(width))
        if caption:
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(caption)
            r.font.size = DocPt(9)
            r.font.italic = True
            r.font.color.rgb = DocRGB(0x6B, 0x7C, 0x8E)


def generate_docx(screenshots):
    doc = Document()

    # ── Styles ──
    style = doc.styles['Normal']
    style.font.name = 'Calibri'
    style.font.size = DocPt(11)
    style.paragraph_format.space_after = DocPt(6)

    # ═══ COVER PAGE ═══
    for _ in range(6):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("FindMe")
    r.font.size = DocPt(42)
    r.font.bold = True
    r.font.color.rgb = DocRGB(0x0A, 0x16, 0x28)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Cavendish University Lost & Found Management System")
    r.font.size = DocPt(18)
    r.font.color.rgb = DocRGB(0x1E, 0x3A, 0x5F)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("An AI-Powered Item Recovery Platform")
    r.font.size = DocPt(14)
    r.font.color.rgb = DocRGB(0x6B, 0x7C, 0x8E)

    doc.add_paragraph()
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Technical Report & User Guide")
    r.font.size = DocPt(16)
    r.font.bold = True

    doc.add_page_break()

    # ═══ TABLE OF CONTENTS ═══
    add_heading(doc, "Table of Contents", 1)
    toc_items = [
        "1. Executive Summary",
        "2. Introduction",
        "3. System Architecture",
        "4. Technology Stack",
        "5. Features Overview",
        "6. User Guide",
        "   6.1 Registration & Login",
        "   6.2 Dashboard",
        "   6.3 Reporting Items",
        "   6.4 AI Matching",
        "   6.5 Search & Notifications",
        "   6.6 Profile Management",
        "7. Administration Guide",
        "   7.1 Admin Dashboard",
        "   7.2 Match Management",
        "   7.3 Item Management",
        "   7.4 User Management",
        "8. AI Matching Engine",
        "9. Security & Data Protection",
        "10. Conclusion"
    ]
    for item in toc_items:
        add_para(doc, item, size=11, color=DocRGB(0x2C, 0x3E, 0x50))
    doc.add_page_break()

    # ═══ 1. EXECUTIVE SUMMARY ═══
    add_heading(doc, "1. Executive Summary", 1)
    add_para(doc, (
        "FindMe is a comprehensive web-based Lost and Found management system developed "
        "for Cavendish University Uganda. The platform leverages modern web technologies "
        "and artificial intelligence to streamline the process of reporting, matching, and "
        "recovering lost items on campus."
    ))
    add_para(doc, (
        "The system replaces manual, paper-based processes with an intuitive digital platform "
        "that enables students, staff, and administrators to efficiently manage lost and found "
        "items. Key innovations include an AI-powered matching engine that automatically "
        "identifies potential matches between lost and found reports based on item attributes, "
        "significantly reducing the time and effort required for item recovery."
    ))
    add_para(doc, (
        "Built with Python Flask and MySQL, the system features role-based access control, "
        "real-time notifications, image upload capabilities, and a responsive design accessible "
        "from any device. The platform serves over 10,000+ students and staff members at "
        "Cavendish University Uganda."
    ))

    # ═══ 2. INTRODUCTION ═══
    add_heading(doc, "2. Introduction", 1)
    add_heading(doc, "2.1 Background", 2)
    add_para(doc, (
        "Cavendish University Uganda, like many educational institutions, faces the challenge "
        "of managing lost and found items across its campus. Students and staff frequently "
        "misplace personal belongings including phones, laptops, textbooks, identification "
        "cards, and other valuables. Traditional methods of managing these items through "
        "physical notice boards, manual logbooks, and word-of-mouth communication are "
        "inefficient and often result in lost items remaining unclaimed."
    ))

    add_heading(doc, "2.2 Problem Statement", 2)
    add_para(doc, "The existing lost and found process at Cavendish University faces several challenges:")
    add_bullet(doc, "No centralized system for reporting lost or found items")
    add_bullet(doc, "Manual matching of lost items with found items is time-consuming and unreliable")
    add_bullet(doc, "Limited visibility into the status of reported items")
    add_bullet(doc, "No automated notifications when potential matches are identified")
    add_bullet(doc, "Difficult for administrators to track and manage the entire recovery process")
    add_bullet(doc, "Security concerns with unauthorized claims of lost items")

    add_heading(doc, "2.3 Objectives", 2)
    add_bullet(doc, "Develop a centralized web platform for reporting lost and found items")
    add_bullet(doc, "Implement AI-powered matching to automatically identify potential item matches")
    add_bullet(doc, "Provide role-based access for students, staff, and administrators")
    add_bullet(doc, "Enable real-time notifications for match updates and status changes")
    add_bullet(doc, "Create a secure verification process for item claim management")
    add_bullet(doc, "Deliver a responsive, user-friendly interface optimized for all devices")

    # ═══ 3. SYSTEM ARCHITECTURE ═══
    add_heading(doc, "3. System Architecture", 1)
    add_para(doc, (
        "The system follows a three-tier architecture pattern, separating concerns into "
        "presentation, business logic, and data access layers..."
    ))

    add_heading(doc, "3.1 Presentation Layer", 2)
    add_bullet(doc, "HTML templates rendered server-side using Flask's Jinja2 templating engine")
    add_bullet(doc, "Responsive CSS design system with custom design tokens and variables")
    add_bullet(doc, "JavaScript for interactive features: navigation toggles, image previews, form validation")
    add_bullet(doc, "Font Awesome 6 for professional iconography throughout the interface")

    add_heading(doc, "3.2 Business Logic Layer", 2)
    add_bullet(doc, "Flask routes handle HTTP requests with session-based authentication")
    add_bullet(doc, "AI matching engine processes item attributes for similarity scoring")
    add_bullet(doc, "Notification system triggers alerts for matches and status changes")
    add_bullet(doc, "File upload service with validation and naming conventions")

    add_heading(doc, "3.3 Data Layer", 2)
    add_bullet(doc, "MySQL relational database with normalized schema")
    add_bullet(doc, "Tables: users, lost_items, found_items, matches, notifications, categories, locations, etc.")
    add_bullet(doc, "Foreign key relationships maintain data integrity")
    add_bullet(doc, "Stored procedures for complex matching queries")

    doc.add_page_break()

    # ═══ 4. TECHNOLOGY STACK ═══
    add_heading(doc, "4. Technology Stack", 1)
    headers = ["Component", "Technology", "Version"]
    data = [
        ["Backend Framework", "Python Flask", "3.0+"],
        ["Programming Language", "Python", "3.13"],
        ["Database", "MySQL", "8.0+"],
        ["Database Connector", "Flask-MySQLdb (MySQLdb)", "2.x"],
        ["Template Engine", "Jinja2", "3.x"],
        ["AI/ML", "Custom Content-Based Matcher", "—"],
        ["Password Security", "bcrypt", "4.x"],
        ["Image Processing", "Pillow (PIL)", "12.x"],
        ["Frontend Icons", "Font Awesome 6", "6.5+"],
    ]
    tech_table = doc.add_table(rows=1 + len(data), cols=3)
    tech_table.style = 'Light Grid Accent 1'
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        tech_table.cell(0, i).text = h
    for ri, row_data in enumerate(data, 1):
        for ci, val in enumerate(row_data):
            tech_table.cell(ri, ci).text = val

    doc.add_paragraph()

    # ═══ 5. FEATURES OVERVIEW ═══
    add_heading(doc, "5. Features Overview", 1)
    add_para(doc, (
        "The FindMe platform provides a comprehensive set of features designed to address "
        "all aspects of the lost and found management lifecycle:"
    ))

    features = [
        ("User Registration & Authentication", "Secure account creation with role-based access control (Student, Lecturer, Admin). Password hashing with bcrypt and session management."),
        ("Report Lost Items", "Detailed form capturing item information, including category, brand, model, color, serial number, location, date/time lost, and optional image upload."),
        ("Report Found Items", "Similar form for found items with additional tracking of current item location for custody management."),
        ("AI-Powered Matching", "Automated comparison of lost and found items using content-based analysis with confidence scoring and detailed explanations."),
        ("Search & Filter", "Multi-criteria search across all items with filters for type, category, location, date, and status."),
        ("Real-time Notifications", "Instant alerts when matches are found or item status changes, with unread count indicators."),
        ("Admin Dashboard", "Comprehensive platform overview with statistics, pending approvals, and activity monitoring."),
        ("Verification Workflow", "Multi-step verification process for claiming items, ensuring secure and authorized recovery."),
    ]
    for title, desc in features:
        add_heading(doc, title, 2)
        add_para(doc, desc)

    doc.add_page_break()

    # ═══ 6. USER GUIDE ═══
    add_heading(doc, "6. User Guide", 1)
    add_para(doc, "This section provides a step-by-step guide to using the FindMe platform from a student or staff perspective.")

    # 6.1
    add_heading(doc, "6.1 Registration & Login", 2)
    add_para(doc, (
        "New users can create an account by navigating to the Registration page. "
        "The form requires full name, email address, phone number, student/staff ID, "
        "account type (Student or Lecturer), faculty, course/program, and a secure password. "
        "After successful registration, users can log in with their email and password."
    ))
    for key in ["register", "login"]:
        if screenshots.get(key):
            add_image_doc(doc, screenshots[key], f"{key.capitalize()} Page", width=5.0)

    # 6.2
    add_heading(doc, "6.2 Dashboard", 2)
    add_para(doc, (
        "The dashboard provides a centralized overview of the user's platform activity. "
        "It displays summary statistics for lost items, found items, and matches. "
        "Action cards provide quick access to common tasks: Report Lost, Report Found, "
        "Search Items, and View Matches. Recent matches and items are listed for quick navigation."
    ))
    if screenshots.get("dashboard"):
        add_image_doc(doc, screenshots["dashboard"], "User Dashboard", width=5.5)

    # 6.3
    add_heading(doc, "6.3 Reporting Items", 2)
    add_para(doc, (
        "To report a lost or found item, click the corresponding action card on the dashboard "
        "or navigate directly to the Report Lost or Report Found pages. The forms are organized "
        "into sections for user information, item details, event information, and optional image upload."
    ))
    for key in ["report_lost", "report_found"]:
        if screenshots.get(key):
            add_image_doc(doc, screenshots[key], f"Report {'Lost' if 'lost' in key else 'Found'} Item Form", width=5.0)

    # 6.4
    add_heading(doc, "6.4 AI Matching", 2)
    add_para(doc, (
        "The AI Matching engine automatically compares lost items against found items (and vice versa) "
        "to identify potential matches. Results are displayed with confidence scores "
        "(Very High, High, Possible, Low), side-by-side image comparisons, and detailed "
        "AI-generated explanations describing why items were matched."
    ))
    if screenshots.get("matches"):
        add_image_doc(doc, screenshots["matches"], "AI Match Results for Users", width=5.5)
    if screenshots.get("match_detail"):
        add_image_doc(doc, screenshots["match_detail"], "Match Detail View with Score and Comparison", width=5.5)

    # 6.5
    add_heading(doc, "6.5 Search & Notifications", 2)
    add_para(doc, (
        "The search page allows users to find items using multiple filters including keywords, "
        "category, location, type (lost/found), and status. Notifications keep users informed "
        "of new matches, status changes, and other platform updates with unread count badges."
    ))
    for key in ["search", "notifications"]:
        if screenshots.get(key):
            add_image_doc(doc, screenshots[key], f"{'Search Page' if key == 'search' else 'Notifications Center'}", width=5.0)

    # 6.6
    add_heading(doc, "6.6 Profile Management", 2)
    add_para(doc, (
        "Users can view and edit their profile information including name, phone number, "
        "and student/staff ID. The profile page also displays account details such as role, "
        "faculty, course, account status, and join date. Password changes are handled through "
        "a separate secure page."
    ))
    if screenshots.get("profile"):
        add_image_doc(doc, screenshots["profile"], "Profile Page", width=5.0)

    doc.add_page_break()

    # ═══ 7. ADMIN GUIDE ═══
    add_heading(doc, "7. Administration Guide", 1)
    add_para(doc, (
        "Administrators have access to comprehensive management tools for overseeing the "
        "entire lost and found system. The admin interface is accessible to users with "
        "the Admin role and provides full control over platform operations."
    ))

    # 7.1
    add_heading(doc, "7.1 Admin Dashboard", 2)
    add_para(doc, (
        "The admin dashboard provides a high-level overview of the entire platform with "
        "key performance indicators including total lost and found items, match statistics, "
        "pending verifications, and recent activity logs."
    ))
    if screenshots.get("admin_dashboard"):
        add_image_doc(doc, screenshots["admin_dashboard"], "Admin Dashboard with KPIs", width=5.5)

    # 7.2
    add_heading(doc, "7.2 Match Management", 2)
    add_para(doc, (
        "Administrators can review, approve, or reject AI-generated matches. The match review "
        "interface displays side-by-side comparisons of lost and found items with the AI's "
        "confidence score and explanation. Administrators can verify the match and mark it as "
        "approved, rejected, or pending further verification."
    ))
    if screenshots.get("admin_matches"):
        add_image_doc(doc, screenshots["admin_matches"], "Admin AI Match Review Page", width=5.5)

    # 7.3
    add_heading(doc, "7.3 Item Management", 2)
    add_para(doc, (
        "The Lost Items and Found Items management pages provide a complete listing of all "
        "reported items in the system. Administrators can filter, search, update statuses, "
        "and manage the lifecycle of each item until it is recovered or closed."
    ))
    for key in ["admin_lost", "admin_found"]:
        if screenshots.get(key):
            add_image_doc(doc, screenshots[key], f"Admin {'Lost' if 'lost' in key else 'Found'} Items Management", width=5.0)

    # 7.4
    add_heading(doc, "7.4 User Management", 2)
    add_para(doc, (
        "The Users management page allows administrators to view, search, and manage all "
        "registered users. Administrators can activate or deactivate accounts, change user "
        "roles, and monitor user activity to ensure platform security."
    ))
    if screenshots.get("admin_users"):
        add_image_doc(doc, screenshots["admin_users"], "Admin User Management Page", width=5.5)

    doc.add_page_break()

    # ═══ 8. AI MATCHING ENGINE ═══
    add_heading(doc, "8. AI Matching Engine", 1)
    add_para(doc, (
        "The AI matching engine is the core innovation of the FindMe platform. It uses "
        "content-based analysis to automatically identify potential matches between lost "
        "and found items, eliminating the need for manual searching and comparison."
    ))

    add_heading(doc, "8.1 Matching Algorithm", 2)
    add_para(doc, "The engine evaluates multiple dimensions of similarity:")
    dims = [
        ("Item Name", "Exact and partial text matching with normalization"),
        ("Brand & Model", "Brand-model combination analysis"),
        ("Category", "Same-category priority scoring"),
        ("Color", "Color matching with normalization"),
        ("Description Keywords", "TF-IDF inspired keyword overlap analysis"),
        ("Location", "Proximity-based scoring for locations"),
        ("Date Range", "Temporal proximity scoring"),
    ]
    for name, desc in dims:
        p = doc.add_paragraph()
        run = p.add_run(f"{name}: ")
        run.font.bold = True
        p.add_run(desc)

    add_heading(doc, "8.2 Confidence Levels", 2)
    levels = [
        ("Very High (80-100%)", "Multiple strong attribute matches across dimensions"),
        ("High (60-79%)", "Good matches on key attributes with some partial matches"),
        ("Possible (40-59%)", "Some similarity but lacking strong confirming evidence"),
        ("Low (0-39%)", "Minimal match potential, requires manual review"),
    ]
    for level, desc in levels:
        add_bullet(doc, f"{level} — {desc}")

    add_heading(doc, "8.3 Explanation Generation", 2)
    add_para(doc, (
        "A key feature of the system is the generation of human-readable explanations for "
        "each match. These explanations detail which attributes matched, the confidence "
        "contribution of each factor, and any notable discrepancies, providing transparency "
        "and building user trust in the AI system."
    ))

    # ═══ 9. SECURITY ═══
    add_heading(doc, "9. Security & Data Protection", 1)
    add_bullet(doc, "Password hashing using bcrypt with salt rounds for secure credential storage")
    add_bullet(doc, "Session-based authentication with server-side session management")
    add_bullet(doc, "Role-based access control (RBAC) limiting features by user role")
    add_bullet(doc, "SQL injection prevention through parameterized queries (MySQLdb)")
    add_bullet(doc, "File upload validation for type and size (max 16MB)")
    add_bullet(doc, "XSS prevention through Jinja2 auto-escaping")
    add_bullet(doc, "CSRF protection via session-based origin validation")
    add_bullet(doc, "Secure session cookies with HTTP-only flags")

    # ═══ 10. CONCLUSION ═══
    add_heading(doc, "10. Conclusion", 1)
    add_para(doc, (
        "FindMe successfully addresses the lost and found management challenges at "
        "Cavendish University Uganda by providing a comprehensive digital platform with "
        "AI-powered matching capabilities. The system streamlines the entire process from "
        "item reporting through recovery, reducing the time and effort required for all "
        "stakeholders involved."
    ))
    add_para(doc, (
        "The AI matching engine demonstrates the practical application of artificial "
        "intelligence in solving everyday campus challenges, while the responsive, accessible "
        "design ensures the platform can be used by the entire university community."
    ))
    add_para(doc, (
        "Future enhancements could include mobile application development, integration with "
        "university security systems, barcode/RFID tagging for high-value items, and expansion "
        "of the AI matching capabilities to include image-based visual similarity analysis."
    ))

    # Save
    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    docx_path = OUT_DIR / f"FindMe_Technical_Report_{ts}.docx"
    doc.save(str(docx_path))
    print(f"\n  [OK] Word report saved: {docx_path}")
    return docx_path


# ══════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════

def main():
    ensure_dir(OUT_DIR)
    ensure_dir(SCREENSHOT_DIR)

    print("=" * 60)
    print("  FindMe - Deliverables Generator")
    print("  PowerPoint Presentation + Word Report")
    print("=" * 60)

    # Step 1: Start Flask
    print("\n[1/4] Starting Flask server...")
    flask_proc = start_flask()
    print("  Flask server started on", FLASK_URL)

    # Step 2: Capture screenshots
    print("\n[2/4] Capturing screenshots...")
    try:
        screenshots = capture_all_screenshots()
    except Exception as e:
        print(f"  [ERROR] Screenshot capture failed: {e}")
        print("  Continuing with partial screenshots...")
        screenshots = {}

    # Step 3: Generate PowerPoint
    print("\n[3/4] Generating PowerPoint presentation...")
    try:
        pptx_path = generate_pptx(screenshots)
    except Exception as e:
        print(f"  [ERROR] PowerPoint generation failed: {e}")
        import traceback
        traceback.print_exc()
        pptx_path = None

    # Step 4: Generate Word report
    print("\n[4/4] Generating Word report...")
    try:
        docx_path = generate_docx(screenshots)
    except Exception as e:
        print(f"  [ERROR] Word report generation failed: {e}")
        import traceback
        traceback.print_exc()
        docx_path = None

    # Cleanup
    stop_flask(flask_proc)
    print("\n" + "=" * 60)
    print("  Generation Complete!")
    if pptx_path:
        print(f"  PowerPoint: {pptx_path}")
    if docx_path:
        print(f"  Word Report: {docx_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
