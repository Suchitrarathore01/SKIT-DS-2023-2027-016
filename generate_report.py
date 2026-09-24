import subprocess
from collections import defaultdict
import datetime
import io
import os
import sys
import html

import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
)

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# =============================================================
# CONFIGURATION
# =============================================================

COLLEGE_NAME = (
    "Swami Keshvanand Institute of Technology, Management & "
    "Gramothan, Jaipur"
)

DEPARTMENT_NAME = "Department of Computer Science & Engineering"

PROJECT_ID = "SKIT/DS/2023-2027/016"

MENTOR_NAME = "Dr. Mithilesh Arya"

LAB_COORDINATOR_NAME = "Dr. Sumit Mathur"

TEAM_MEMBERS = {
    "Suchitra Rathore": "Suchitrarathore01",
    "Shrestha Swami": "shrestha-swami",
    "Sourabh Sharma": "Sourabhsharma77200",
    "Yuvraj Singh": "YuvrajSingh-2003",
}


# =============================================================
# REPOSITORY INFORMATION
# =============================================================

def get_repo_info():
    """Get repository name and current branch."""

    repo_name = "Project-Repository"
    branch_name = "unknown"

    try:
        root_path = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            encoding="utf-8"
        ).strip()

        repo_name = os.path.basename(root_path)

    except Exception:

        try:
            remote_url = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                encoding="utf-8"
            ).strip()

            repo_name = (
                remote_url.rstrip("/")
                .split("/")[-1]
                .replace(".git", "")
            )

        except Exception:
            repo_name = os.path.basename(os.getcwd())

    try:
        branch_name = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            encoding="utf-8"
        ).strip()

    except Exception:
        pass

    return repo_name, branch_name


# =============================================================
# FRIDAY → THURSDAY WEEK CALCULATION
# =============================================================

def get_week_window():
    """
    Project week is strictly:

        Friday → Thursday

    Example:

        Friday 25 Sep 2026
        →
        Thursday 01 Oct 2026

    Only commits inside this exact window are included.
    """

    today = datetime.date.today()

    # Python weekday:
    # Monday = 0
    # Tuesday = 1
    # Wednesday = 2
    # Thursday = 3
    # Friday = 4
    # Saturday = 5
    # Sunday = 6

    days_since_friday = (today.weekday() - 4) % 7

    week_start = today - datetime.timedelta(
        days=days_since_friday
    )

    week_end = week_start + datetime.timedelta(days=6)

    return week_start, week_end


# =============================================================
# GIT METRICS
# =============================================================

def get_git_metrics(interval="weekly"):

    today = datetime.date.today()

    # ---------------------------------------------------------
    # WEEKLY
    # ---------------------------------------------------------

    if interval == "weekly":

        week_start, week_end = get_week_window()

        since_date = week_start.strftime("%Y-%m-%d")

        # Git --until can be exclusive/inclusive sensitive,
        # therefore use the next day.
        until_date = (
            week_end + datetime.timedelta(days=1)
        ).strftime("%Y-%m-%d")

        scope_title = (
            f"{week_start.strftime('%d %b %Y')} "
            f"to {week_end.strftime('%d %b %Y')} "
            f"(Friday to Thursday)"
        )

        git_args = [
            "git",
            "log",
            "--no-merges",
            f"--since={since_date}",
            f"--until={until_date}",
            "--pretty=format:COMMIT|||%h|||%an|||%ad|||%s",
            "--date=short",
            "--numstat",
        ]

    # ---------------------------------------------------------
    # MONTHLY
    # ---------------------------------------------------------

    elif interval == "monthly":

        since_date = (
            today - datetime.timedelta(days=30)
        ).strftime("%Y-%m-%d")

        git_args = [
            "git",
            "log",
            "--no-merges",
            f"--since={since_date}",
            "--pretty=format:COMMIT|||%h|||%an|||%ad|||%s",
            "--date=short",
            "--numstat",
        ]

        scope_title = (
            f"Last 30 Days (Since {since_date})"
        )

    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    else:

        git_args = [
            "git",
            "log",
            "--no-merges",
            "--pretty=format:COMMIT|||%h|||%an|||%ad|||%s",
            "--date=short",
            "--numstat",
        ]

        scope_title = (
            "Complete Project Lifecycle (All Commits)"
        )

    # ---------------------------------------------------------
    # RUN GIT COMMAND
    # ---------------------------------------------------------

    try:

        raw_output = subprocess.check_output(
            git_args,
            encoding="utf-8",
            errors="replace"
        )

    except subprocess.CalledProcessError:

        print(
            "[ERROR] Git command failed. "
            "Please ensure you are inside a Git repository."
        )

        return None, None, None, scope_title

    # ---------------------------------------------------------
    # Initialize ALL team members
    # ---------------------------------------------------------

    students = defaultdict(
        lambda: {
            "commits": 0,
            "added": 0,
            "deleted": 0,
            "active_days": set(),
        }
    )

    for member_name in TEAM_MEMBERS:
        students[member_name]

    timeline_activity = defaultdict(
        lambda: defaultdict(int)
    )

    student_logs = defaultdict(list)

    current_author = None
    current_date_str = None

    # ---------------------------------------------------------
    # Parse git output
    # ---------------------------------------------------------

    for line in raw_output.splitlines():

        line = line.strip()

        if not line:
            continue

        # -----------------------------------------------------
        # New commit
        # -----------------------------------------------------

        if line.startswith("COMMIT|||"):

            parts = line.split("|||")

            if len(parts) < 5:
                current_author = None
                continue

            sha = parts[1].strip()
            author = parts[2].strip()
            date_str = parts[3].strip()
            msg = parts[4].strip()

            # -------------------------------------------------
            # STRICT AUTHOR DATE FILTER
            # -------------------------------------------------
            #
            # This is the important fix.
            #
            # Git initially filters using commit date.
            # We additionally verify the displayed AUTHOR DATE
            # against the exact Friday → Thursday window.
            #

            if interval == "weekly":

                try:

                    commit_date = datetime.datetime.strptime(
                        date_str,
                        "%Y-%m-%d"
                    ).date()

                except ValueError:

                    current_author = None
                    continue

                if not (
                    week_start <= commit_date <= week_end
                ):

                    current_author = None
                    continue

            # -------------------------------------------------
            # Ignore GitHub automation bots
            # -------------------------------------------------

            if (
                "bot" in author.lower()
                or "github-actions" in author.lower()
            ):

                current_author = None
                continue

            # -------------------------------------------------
            # Match author to team member
            # -------------------------------------------------

            matched_author = None

            for member_name, username in TEAM_MEMBERS.items():

                if (
                    author.lower() == member_name.lower()
                    or author.lower() == username.lower()
                ):

                    matched_author = member_name
                    break

            # If author is not a registered team member,
            # do not invent a team contribution.

            if matched_author is None:

                current_author = None
                continue

            current_author = matched_author

            current_date_str = date_str

            students[current_author]["commits"] += 1

            students[current_author]["active_days"].add(
                current_date_str
            )

            student_logs[current_author].append(
                (
                    date_str,
                    sha,
                    msg
                )
            )

            # -------------------------------------------------
            # Timeline
            # -------------------------------------------------

            try:

                dt = datetime.datetime.strptime(
                    current_date_str,
                    "%Y-%m-%d"
                ).date()

                if interval == "weekly":

                    period_key = dt.strftime(
                        "%a (%b %d)"
                    )

                elif interval == "monthly":

                    period_key = (
                        f"{dt.isocalendar()[0]}-"
                        f"W{dt.isocalendar()[1]:02d}"
                    )

                else:

                    period_key = dt.strftime(
                        "%Y-%m"
                    )

                timeline_activity[
                    period_key
                ][current_author] += 1

            except Exception:
                pass

        # -----------------------------------------------------
        # Numstat line
        # -----------------------------------------------------

        elif current_author:

            parts = line.split()

            if len(parts) >= 2:

                try:

                    added = int(parts[0])
                    deleted = int(parts[1])

                    students[
                        current_author
                    ]["added"] += added

                    students[
                        current_author
                    ]["deleted"] += deleted

                except ValueError:

                    pass

    return (
        students,
        timeline_activity,
        student_logs,
        scope_title,
    )


# =============================================================
# CHART GENERATION
# =============================================================

def create_charts(
    students,
    timeline_activity,
    interval
):

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11, 3.8)
    )

    authors = list(students.keys())

    periods = sorted(
        timeline_activity.keys()
    )

    # ---------------------------------------------------------
    # Commit Timeline
    # ---------------------------------------------------------

    if periods:

        plotted_any = False

        for author in authors:

            counts = [
                timeline_activity[p].get(
                    author,
                    0
                )
                for p in periods
            ]

            if sum(counts) > 0:

                plotted_any = True

                ax1.plot(
                    periods,
                    counts,
                    marker="o",
                    linewidth=2,
                    label=author
                )

        if plotted_any:

            ax1.set_title(
                f"Commit Timeline "
                f"({interval.capitalize()})",
                fontsize=10,
                fontweight="bold"
            )

            ax1.set_ylabel("Commits")

            ax1.tick_params(
                axis="x",
                rotation=30
            )

            ax1.grid(
                True,
                linestyle="--",
                alpha=0.5
            )

            ax1.legend(
                fontsize=8
            )

        else:

            ax1.text(
                0.5,
                0.5,
                "No commits found in this interval",
                ha="center",
                va="center"
            )

    else:

        ax1.text(
            0.5,
            0.5,
            "No commits found in this interval",
            ha="center",
            va="center"
        )

    # ---------------------------------------------------------
    # Net LOC
    # ---------------------------------------------------------

    net_loc = [
        students[a]["added"]
        - students[a]["deleted"]
        for a in authors
    ]

    ax2.bar(
        authors,
        net_loc,
        width=0.45
    )

    ax2.set_title(
        "Net Lines of Code Written",
        fontsize=10,
        fontweight="bold"
    )

    ax2.set_ylabel(
        "LOC (Added - Deleted)"
    )

    ax2.tick_params(
        axis="x",
        rotation=25
    )

    ax2.grid(
        axis="y",
        linestyle="--",
        alpha=0.5
    )

    plt.tight_layout()

    img_buffer = io.BytesIO()

    plt.savefig(
        img_buffer,
        format="png",
        dpi=200
    )

    plt.close()

    img_buffer.seek(0)

    return Image(
        img_buffer,
        width=500,
        height=170
    )


# =============================================================
# PDF GENERATION
# =============================================================

def generate_pdf(interval="weekly"):

    repo_name, branch_name = get_repo_info()

    (
        students,
        timeline_activity,
        student_logs,
        scope_title
    ) = get_git_metrics(interval)

    if students is None:
        return

    # ---------------------------------------------------------
    # Weekly report date
    # ---------------------------------------------------------

    if interval == "weekly":

        week_start, week_end = get_week_window()

        date_stamp = week_end.strftime(
            "%Y-%m-%d"
        )

        os.makedirs(
            "weekly_reports",
            exist_ok=True
        )

    else:

        date_stamp = datetime.date.today().strftime(
            "%Y-%m-%d"
        )

    # ---------------------------------------------------------
    # Report name
    # ---------------------------------------------------------

    if interval == "weekly":

        report_title = (
            "Weekly Progress Report (Form-3)"
        )

        doc_name = os.path.join(
            "weekly_reports",
            f"{repo_name}_Weekly_Progress_Report_Form-3_"
            f"{date_stamp}.pdf"
        )

    elif interval == "monthly":

        report_title = (
            "Monthly Progress Report (Form-3)"
        )

        doc_name = (
            f"{repo_name}_Monthly_Progress_Report_Form-3_"
            f"{date_stamp}.pdf"
        )

    else:

        report_title = (
            "Final Project Evaluation Report"
        )

        doc_name = (
            f"{repo_name}_Final_Report_"
            f"{date_stamp}.pdf"
        )

    # ---------------------------------------------------------
    # PDF Document
    # ---------------------------------------------------------

    doc = SimpleDocTemplate(
        doc_name,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    college_style = ParagraphStyle(
        "CollegeStyle",
        parent=styles["Heading1"],
        fontSize=13.5,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
        spaceAfter=2
    )

    dept_style = ParagraphStyle(
        "DeptStyle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1,
        spaceAfter=6
    )

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1A365D"),
        alignment=1,
        spaceAfter=5
    )

    repo_style = ParagraphStyle(
        "RepoStyle",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3
    )

    meta_style = ParagraphStyle(
        "MetaStyle",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=8
    )

    section_style = ParagraphStyle(
        "SectionStyle",
        parent=styles["Heading2"],
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=7,
        spaceAfter=4
    )

    sub_section_style = ParagraphStyle(
        "SubSectionStyle",
        parent=styles["Heading3"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=5,
        spaceAfter=2
    )

    msg_style = ParagraphStyle(
        "MsgStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    meta_cell_style = ParagraphStyle(
        "MetaCellStyle",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    marks_style = ParagraphStyle(
        "MarksStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A"),
        alignment=1
    )

    sig_block_style = ParagraphStyle(
        "SigBlockStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=15,
        textColor=colors.HexColor("#0F172A"),
        alignment=0
    )

    story = []

    # =========================================================
    # HEADER
    # =========================================================

    story.append(
        Paragraph(
            f"<b>{html.escape(COLLEGE_NAME)}</b>",
            college_style
        )
    )

    story.append(
        Paragraph(
            f"<b>{html.escape(DEPARTMENT_NAME)}</b>",
            dept_style
        )
    )

    story.append(
        Paragraph(
            f"<u><b>{report_title}</b></u>",
            title_style
        )
    )

    story.append(
        Spacer(1, 3)
    )

    # =========================================================
    # PROJECT METADATA
    # =========================================================

    story.append(
        Paragraph(
            f"<b>Project ID:</b> "
            f"{html.escape(PROJECT_ID)}",
            repo_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Project Repository:</b> "
            f"<font color='#2563EB'><b>"
            f"{html.escape(repo_name)}</b></font> "
            f"&nbsp;|&nbsp; "
            f"<b>Branch:</b> "
            f"<code>{html.escape(branch_name)}</code>",
            repo_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Evaluation Window:</b> "
            f"{scope_title} "
            f"&nbsp;|&nbsp; "
            f"<b>Generated On:</b> "
            f"{datetime.date.today().strftime('%B %d, %Y')}",
            meta_style
        )
    )

    # =========================================================
    # TEAM MEMBERS
    # =========================================================

    story.append(
        Paragraph(
            "Team Members",
            section_style
        )
    )

    member_data = [
        ["Student Name", "GitHub Username"]
    ]

    for name, username in TEAM_MEMBERS.items():

        member_data.append([
            name,
            username
        ])

    member_table = Table(
        member_data,
        colWidths=[250, 250]
    )

    member_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1E293B")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.whitesmoke
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#CBD5E1")
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8FAFC")
                ]
            ),
        ])
    )

    story.append(member_table)

    story.append(
        Spacer(1, 6)
    )

    # =========================================================
    # CONTRIBUTION TABLE
    # =========================================================

    story.append(
        Paragraph(
            "1. Individual Contribution Breakdown",
            section_style
        )
    )

    total_commits = sum(
        data["commits"]
        for data in students.values()
    )

    table_data = [[
        "Student Name",
        "Commits (%)",
        "Lines Added",
        "Lines Deleted",
        "Net LOC",
        "Active Days"
    ]]

    for name in TEAM_MEMBERS:

        data = students[name]

        pct = (
            data["commits"]
            / total_commits
            * 100
        ) if total_commits > 0 else 0

        net = (
            data["added"]
            - data["deleted"]
        )

        table_data.append([
            html.escape(name),
            f"{data['commits']} ({pct:.1f}%)",
            f"+{data['added']:,}",
            f"-{data['deleted']:,}",
            f"{net:,}",
            f"{len(data['active_days'])} days"
        ])

    table = Table(
        table_data,
        colWidths=[
            120,
            80,
            80,
            80,
            80,
            100
        ]
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#1E293B")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.whitesmoke
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "ALIGN",
                (0, 1),
                (0, -1),
                "LEFT"
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                3.5
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                3.5
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#CBD5E1")
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#F8FAFC")
                ]
            ),
        ])
    )

    story.append(table)

    story.append(
        Spacer(1, 6)
    )

    # =========================================================
    # CHARTS
    # =========================================================

    story.append(
        Paragraph(
            "2. Visual Trends & Volume",
            section_style
        )
    )

    chart_image = create_charts(
        students,
        timeline_activity,
        interval
    )

    story.append(chart_image)

    story.append(
        Spacer(1, 6)
    )

    # =========================================================
    # COMMIT LOGS
    # =========================================================

    story.append(
        Paragraph(
            f"3. Detailed Commit Logs & Mentor Evaluation "
            f"({interval.capitalize()})",
            section_style
        )
    )

    if not student_logs:

        story.append(
            Paragraph(
                "<i>No commit logs found for this timeframe.</i>",
                styles["Normal"]
            )
        )

    else:

        for student_name, logs in student_logs.items():

            student_section = []

            student_section.append(
                Paragraph(
                    f"<b>Student:</b> "
                    f"{html.escape(student_name)} "
                    f"— <i>{len(logs)} commit(s)</i>",
                    sub_section_style
                )
            )

            log_table_data = [[
                "Date",
                "Hash",
                "Commit Message",
                "Mentor Marks (/10)"
            ]]

            for index, (
                date_val,
                sha_val,
                msg_val
            ) in enumerate(logs):

                safe_msg = (
                    html.escape(msg_val)
                    if msg_val
                    else "(No commit message)"
                )

                mark_cell = ""

                if index == 0:

                    mark_cell = Paragraph(
                        "<b>_____ / 10</b>",
                        marks_style
                    )

                log_table_data.append([
                    Paragraph(
                        date_val,
                        meta_cell_style
                    ),
                    Paragraph(
                        f"<code>{sha_val}</code>",
                        meta_cell_style
                    ),
                    Paragraph(
                        safe_msg,
                        msg_style
                    ),
                    mark_cell
                ])

            num_rows = len(log_table_data)

            log_table = Table(
                log_table_data,
                colWidths=[
                    65,
                    50,
                    335,
                    90
                ]
            )

            log_table.setStyle(
                TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#475569")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.whitesmoke
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "LEFT"
                    ),
                    (
                        "ALIGN",
                        (3, 0),
                        (3, -1),
                        "CENTER"
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7.5
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2.5
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2.5
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#CBD5E1")
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (2, -1),
                        [
                            colors.white,
                            colors.HexColor("#F8FAFC")
                        ]
                    ),
                ])
            )

            # Mentor marks column spans all commit rows

            if num_rows > 1:

                log_table.setStyle(
                    TableStyle([
                        (
                            "SPAN",
                            (3, 1),
                            (3, num_rows - 1)
                        ),
                        (
                            "VALIGN",
                            (3, 1),
                            (3, num_rows - 1),
                            "MIDDLE"
                        ),
                        (
                            "BACKGROUND",
                            (3, 1),
                            (3, num_rows - 1),
                            colors.HexColor("#FEF3C7")
                        ),
                    ])
                )

            student_section.append(
                log_table
            )

            student_section.append(
                Spacer(1, 5)
            )

            story.append(
                KeepTogether(
                    student_section
                )
            )

    # =========================================================
    # SIGNATURE SECTION
    # =========================================================

    story.append(
        Spacer(1, 16)
    )

    mentor_cell = [

        Paragraph(
            f"<b>Name:</b> "
            f"{html.escape(MENTOR_NAME)}",
            sig_block_style
        ),

        Paragraph(
            "<b>Designation:</b> Project Mentor",
            sig_block_style
        ),

        Spacer(1, 6),

        Paragraph(
            "<b>Signature:</b> "
            "____________________________________________",
            sig_block_style
        ),
    ]

    coordinator_cell = [

        Paragraph(
            f"<b>Name:</b> "
            f"{html.escape(LAB_COORDINATOR_NAME)}",
            sig_block_style
        ),

        Paragraph(
            "<b>Designation:</b> Lab Coordinator",
            sig_block_style
        ),

        Spacer(1, 6),

        Paragraph(
            "<b>Signature:</b> "
            "____________________________________________",
            sig_block_style
        ),
    ]

    sig_table = Table(
        [[mentor_cell, coordinator_cell]],
        colWidths=[270, 270]
    )

    sig_table.setStyle(
        TableStyle([
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (0, -1),
                0
            ),
            (
                "LEFTPADDING",
                (1, 0),
                (1, -1),
                40
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0
            ),
        ])
    )

    story.append(
        KeepTogether(sig_table)
    )

    # =========================================================
    # BUILD PDF
    # =========================================================

    doc.build(story)

    print()

    print(
        "[SUCCESS] Generated:",
        doc_name
    )

    print(
        f" -> Evaluation Window: {scope_title}"
    )

    print(
        f" -> Found {total_commits} total "
        f"team commit(s)."
    )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    chosen_interval = (
        sys.argv[1].lower()
        if len(sys.argv) > 1
        else "weekly"
    )

    if chosen_interval not in [
        "weekly",
        "monthly",
        "final"
    ]:

        print(
            "Usage: python generate_report.py "
            "[weekly|monthly|final]"
        )

        sys.exit(1)

    generate_pdf(chosen_interval)