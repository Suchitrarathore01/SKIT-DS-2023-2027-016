import subprocess
from collections import defaultdict
import datetime
import io
import os
import sys
import html
import json

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
    KeepTogether
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)


# -------------------------------------------------------------
# CONFIGURATION: Institution & Department Details
# -------------------------------------------------------------

COLLEGE_NAME = (
    "Swami Keshvanand Institute of Technology,"
    "Management & Gramothan, Jaipur"
)

DEPARTMENT_NAME = (
    "Department of Computer Science & Engineering"
)


# -------------------------------------------------------------
# PROJECT WEEK CONFIGURATION
# -------------------------------------------------------------

# IMPORTANT:
# Set this to the actual FRIDAY on which your
# ChainShield project reporting starts.
#
# Example:
# 2026-09-04 = Friday
#
PROJECT_START_DATE = datetime.date(
    2026,
    9,
    4
)


# -------------------------------------------------------------
# AUTHOR NAME NORMALIZATION
# -------------------------------------------------------------
# Different Git identities can belong to the same team member.
# All listed variants are grouped under one canonical name in
# the generated reports. Git history itself is not modified.

AUTHOR_ALIASES = {
    "sourabh sharma": "Sourabh Sharma",
    "sourabhsharma77200": "Sourabh Sharma",

    # Add additional Git name variants here when required.
    # "git-name-or-username": "Canonical Student Name",
}


def normalize_author_name(author):
    """
    Converts different Git author names belonging to the
    same person into one canonical student name.
    """

    if not author:
        return author

    key = " ".join(author.strip().lower().split())

    return AUTHOR_ALIASES.get(
        key,
        author.strip()
    )


# Directory for weekly PDF reports
WEEKLY_REPORTS_DIR = "weekly_reports"


# Directory and file used to maintain historical
# weekly report information
REPORT_HISTORY_DIR = "reports"

REPORT_HISTORY_FILE = os.path.join(
    REPORT_HISTORY_DIR,
    "weekly_history.json"
)


# -------------------------------------------------------------
# REPOSITORY INFORMATION
# -------------------------------------------------------------


def get_repo_info():
    """
    Extract the repository name from the Git remote when available.
    Fall back to the local Git root if the remote cannot be read.
    """
    repo_name = "Project-Repository"
    branch_name = "main"

    try:
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()

        if remote_url:
            repo_name = (
                remote_url.rstrip("/")
                .split("/")[-1]
                .removesuffix(".git")
            )
    except Exception:
        pass

    if repo_name == "Project-Repository":
        try:
            root_path = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
            ).strip()
            repo_name = os.path.basename(root_path)
        except Exception:
            repo_name = os.path.basename(os.getcwd())

    try:
        branch_name = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        pass

    return repo_name, branch_name



# -------------------------------------------------------------
# WEEKLY HISTORY MANAGEMENT
# -------------------------------------------------------------

def initialize_history():

    """
    Creates the report history directory and JSON file
    if they do not already exist.
    """

    os.makedirs(
        REPORT_HISTORY_DIR,
        exist_ok=True
    )

    if not os.path.exists(
        REPORT_HISTORY_FILE
    ):

        history = {
            "project_start": (
                PROJECT_START_DATE.isoformat()
            ),
            "weeks": []
        }

        save_history(
            history
        )


def load_history():

    """
    Loads the historical weekly report information.
    """

    initialize_history()

    try:

        with open(
            REPORT_HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(
                file
            )

    except Exception:

        history = {
            "project_start": (
                PROJECT_START_DATE.isoformat()
            ),
            "weeks": []
        }

        save_history(
            history
        )

        return history


def save_history(history):

    """
    Saves historical weekly report information.
    """

    os.makedirs(
        REPORT_HISTORY_DIR,
        exist_ok=True
    )

    with open(
        REPORT_HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            history,
            file,
            indent=4
        )


def get_week_history(
    week_number,
    history
):

    """
    Returns the stored history for a specific week.
    """

    for week in history.get(
        "weeks",
        []
    ):

        if (
            week.get("week_number")
            == week_number
        ):

            return week

    return None


def get_previous_week_history(
    week_number,
    history
):

    """
    Returns the previous week's history.
    """

    if week_number <= 1:

        return None

    return get_week_history(
        week_number - 1,
        history
    )


# -------------------------------------------------------------
# PROJECT WEEK CALCULATION
# -------------------------------------------------------------

def get_project_week_window(
    target_date=None
):

    """
    Calculates the project week using:

        Friday -> Thursday

    Week 1 begins at PROJECT_START_DATE.

    Example:

        Week 1:
        Friday 04 Sep 2026
        ->
        Thursday 10 Sep 2026

        Week 2:
        Friday 11 Sep 2026
        ->
        Thursday 17 Sep 2026
    """

    if target_date is None:

        target_date = datetime.date.today()

    if target_date < PROJECT_START_DATE:

        return (
            None,
            None,
            None
        )

    days_since_start = (
        target_date
        -
        PROJECT_START_DATE
    ).days

    week_number = (
        days_since_start // 7
    ) + 1

    week_start = (
        PROJECT_START_DATE
        +
        datetime.timedelta(
            days=(week_number - 1) * 7
        )
    )

    week_end = (
        week_start
        +
        datetime.timedelta(
            days=6
        )
    )

    return (
        week_number,
        week_start,
        week_end
    )


# -------------------------------------------------------------
# GET ALL PROJECT WEEKS
# -------------------------------------------------------------

def get_all_project_weeks():

    """
    Returns every project week from the project start
    until the current date.
    """

    today = datetime.date.today()

    weeks = []

    current_start = PROJECT_START_DATE

    week_number = 1

    while current_start <= today:

        current_end = (
            current_start
            +
            datetime.timedelta(
                days=6
            )
        )

        weeks.append(
            {
                "week_number": week_number,
                "start": current_start,
                "end": current_end
            }
        )

        current_start += (
            datetime.timedelta(
                days=7
            )
        )

        week_number += 1

    return weeks


# -------------------------------------------------------------
# GIT METRICS
# -------------------------------------------------------------

def get_git_metrics(
    interval="weekly",
    target_week=None
):

    """
    Parses Git commit logs.

    Supported intervals:

        weekly
        monthly
        final

    Weekly logic:

        Friday -> Thursday

    Monthly and final logic remain the same
    as the original implementation.
    """

    today = datetime.date.today()

    git_args = [
        "git",
        "log",
        "--no-merges",
        "--pretty=format:COMMIT|||%h|||%an|||%ad|||%s",
        "--date=short",
        "--numstat"
    ]


    # ---------------------------------------------------------
    # WEEKLY
    # ---------------------------------------------------------

    if interval == "weekly":

        if target_week is None:

            (
                week_number,
                week_start,
                week_end
            ) = get_project_week_window()

        else:

            week_number = target_week

            week_start = (
                PROJECT_START_DATE
                +
                datetime.timedelta(
                    days=(week_number - 1) * 7
                )
            )

            week_end = (
                week_start
                +
                datetime.timedelta(
                    days=6
                )
            )

        since_date = (
            week_start.strftime(
                "%Y-%m-%d"
            )
        )

        until_date = (
            week_end
            +
            datetime.timedelta(
                days=1
            )
        ).strftime(
            "%Y-%m-%d"
        )

        git_args.append(
            f"--since={since_date}"
        )

        git_args.append(
            f"--until={until_date}"
        )

        scope_title = (
            f"{week_start.strftime('%d %b %Y')} "
            f"to "
            f"{week_end.strftime('%d %b %Y')} "
            f"(Friday to Thursday)"
        )


    # ---------------------------------------------------------
    # MONTHLY
    # ---------------------------------------------------------

    elif interval == "monthly":

        since_date = (
            today
            -
            datetime.timedelta(
                days=30
            )
        ).strftime(
            "%Y-%m-%d"
        )

        git_args.append(
            f"--since={since_date}"
        )

        scope_title = (
            f"Last 30 Days "
            f"(Since {since_date})"
        )


    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    else:

        scope_title = (
            "Complete Project Lifecycle "
            "(All Commits)"
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
            "Please ensure you are inside "
            "a Git repository."
        )

        return (
            None,
            None,
            None,
            scope_title
        )


    students = defaultdict(
        lambda: {
            "commits": 0,
            "added": 0,
            "deleted": 0,
            "active_days": set()
        }
    )


    timeline_activity = defaultdict(
        lambda: defaultdict(int)
    )


    student_logs = defaultdict(
        list
    )


    current_author = None

    current_date_str = None


    # ---------------------------------------------------------
    # PARSE GIT OUTPUT
    # ---------------------------------------------------------

    for line in raw_output.strip().split(
        "\n"
    ):

        line = line.strip()

        if not line:

            continue


        # -----------------------------------------------------
        # COMMIT
        # -----------------------------------------------------

        if line.startswith(
            "COMMIT|||"
        ):

            parts = line.split(
                "|||"
            )

            if len(parts) >= 5:

                sha = parts[1].strip()

                author = normalize_author_name(parts[2])

                date_str = parts[3].strip()

                msg = parts[4].strip()

            else:

                current_author = None

                continue


            # -------------------------------------------------
            # IGNORE AUTOMATED BOTS
            # -------------------------------------------------

            if (
                "bot"
                in author.lower()
                or
                "github-actions"
                in author.lower()
            ):

                current_author = None

                continue


            current_author = author

            current_date_str = date_str


            students[
                current_author
            ]["commits"] += 1


            students[
                current_author
            ]["active_days"].add(
                current_date_str
            )


            student_logs[
                current_author
            ].append(
                (
                    date_str,
                    sha,
                    msg
                )
            )


            # -------------------------------------------------
            # TIMELINE
            # -------------------------------------------------

            try:

                dt = (
                    datetime.datetime.strptime(
                        current_date_str,
                        "%Y-%m-%d"
                    ).date()
                )


                if interval == "weekly":

                    period_key = (
                        dt.strftime(
                            "%a (%b %d)"
                        )
                    )

                elif interval == "monthly":

                    period_key = (
                        f"{dt.isocalendar()[0]}"
                        f"-W"
                        f"{dt.isocalendar()[1]:02d}"
                    )

                else:

                    period_key = (
                        dt.strftime(
                            "%Y-%m"
                        )
                    )


                timeline_activity[
                    period_key
                ][current_author] += 1


            except Exception:

                pass


        # -----------------------------------------------------
        # NUMSTAT
        # -----------------------------------------------------

        elif (
            current_author
            and
            not line.startswith(
                "COMMIT|||"
            )
        ):

            parts = line.split()


            if (
                len(parts) >= 2
                and
                parts[0].isdigit()
                and
                parts[1].isdigit()
            ):

                students[
                    current_author
                ]["added"] += int(
                    parts[0]
                )

                students[
                    current_author
                ]["deleted"] += int(
                    parts[1]
                )


    return (
        students,
        timeline_activity,
        student_logs,
        scope_title
    )


# -------------------------------------------------------------
# CUMULATIVE PROJECT METRICS
# -------------------------------------------------------------

def get_cumulative_metrics(
    week_end
):

    """
    Calculates Git metrics from the project start
    through the selected week's end.

    This does NOT alter the normal weekly metrics.
    It is only used to show cumulative project progress.
    """

    students = defaultdict(
        lambda: {
            "commits": 0,
            "added": 0,
            "deleted": 0,
            "active_days": set()
        }
    )


    since_date = (
        PROJECT_START_DATE.strftime(
            "%Y-%m-%d"
        )
    )

    until_date = (
        week_end
        +
        datetime.timedelta(
            days=1
        )
    ).strftime(
        "%Y-%m-%d"
    )


    git_args = [
        "git",
        "log",
        "--no-merges",
        f"--since={since_date}",
        f"--until={until_date}",
        "--pretty=format:COMMIT|||%h|||%an|||%ad|||%s",
        "--date=short",
        "--numstat"
    ]


    try:

        raw_output = subprocess.check_output(
            git_args,
            encoding="utf-8",
            errors="replace"
        )

    except subprocess.CalledProcessError:

        return students


    current_author = None


    for line in raw_output.strip().split(
        "\n"
    ):

        line = line.strip()


        if not line:

            continue


        if line.startswith(
            "COMMIT|||"
        ):

            parts = line.split(
                "|||"
            )


            if len(parts) < 5:

                current_author = None

                continue


            author = normalize_author_name(parts[2])

            date_str = parts[3].strip()


            if (
                "bot"
                in author.lower()
                or
                "github-actions"
                in author.lower()
            ):

                current_author = None

                continue


            current_author = author


            students[
                current_author
            ]["commits"] += 1


            students[
                current_author
            ]["active_days"].add(
                date_str
            )


        elif current_author:

            parts = line.split()


            if (
                len(parts) >= 2
                and
                parts[0].isdigit()
                and
                parts[1].isdigit()
            ):

                students[
                    current_author
                ]["added"] += int(
                    parts[0]
                )

                students[
                    current_author
                ]["deleted"] += int(
                    parts[1]
                )


    return students


# -------------------------------------------------------------
# SAVE WEEK HISTORY
# -------------------------------------------------------------

def update_week_history(
    week_number,
    week_start,
    week_end,
    doc_name,
    students
):

    """
    Stores the current week's metrics in
    reports/weekly_history.json.
    """

    history = load_history()


    total_commits = sum(
        data["commits"]
        for data in students.values()
    )


    total_added = sum(
        data["added"]
        for data in students.values()
    )


    total_deleted = sum(
        data["deleted"]
        for data in students.values()
    )


    member_metrics = {}


    for name, data in students.items():

        member_metrics[name] = {
            "commits": data["commits"],
            "added": data["added"],
            "deleted": data["deleted"],
            "net_loc": (
                data["added"]
                -
                data["deleted"]
            ),
            "active_days": len(
                data["active_days"]
            )
        }


    record = {

        "week_number": week_number,

        "start": (
            week_start.isoformat()
        ),

        "end": (
            week_end.isoformat()
        ),

        "report": doc_name,

        "total_commits": total_commits,

        "total_added": total_added,

        "total_deleted": total_deleted,

        "total_net_loc": (
            total_added
            -
            total_deleted
        ),

        "members": member_metrics
    }


    existing = get_week_history(
        week_number,
        history
    )


    if existing:

        history["weeks"] = [

            record
            if week.get(
                "week_number"
            ) == week_number

            else week

            for week in history[
                "weeks"
            ]
        ]

    else:

        history[
            "weeks"
        ].append(
            record
        )


    history[
        "weeks"
    ] = sorted(
        history["weeks"],
        key=lambda x:
            x["week_number"]
    )


    save_history(
        history
    )


# -------------------------------------------------------------
# CHART GENERATION
# -------------------------------------------------------------

def create_charts(
    students,
    timeline_activity,
    interval
):

    """
    Generates visual workload and trend charts.

    Existing chart logic is preserved.
    """

    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(11, 3.8)
    )


    authors = list(
        students.keys()
    )


    periods = sorted(
        timeline_activity.keys()
    )


    # ---------------------------------------------------------
    # 1. Timeline Line Chart
    # ---------------------------------------------------------

    if periods and authors:

        for author in authors:

            counts = [

                timeline_activity[p].get(
                    author,
                    0
                )

                for p in periods
            ]


            ax1.plot(
                periods,
                counts,
                marker="o",
                linewidth=2,
                label=author
            )


        ax1.set_title(
            f"Commit Timeline "
            f"({interval.capitalize()})",
            fontsize=10,
            fontweight="bold"
        )


        ax1.set_ylabel(
            "Commits"
        )


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
            "No commits found "
            "in this interval",
            ha="center",
            va="center"
        )


    # ---------------------------------------------------------
    # 2. Net LOC Bar Chart
    # ---------------------------------------------------------

    if authors:

        net_loc = [

            students[a]["added"]
            -
            students[a]["deleted"]

            for a in authors
        ]


        # Same visual color scheme as original code
        colors_list = [
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F"
        ]


        ax2.bar(
            authors,
            net_loc,
            color=colors_list[
                :len(authors)
            ],
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


        ax2.grid(
            axis="y",
            linestyle="--",
            alpha=0.5
        )


    else:

        ax2.text(
            0.5,
            0.5,
            "No LOC changes recorded",
            ha="center",
            va="center"
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


# -------------------------------------------------------------
# PDF GENERATION
# -------------------------------------------------------------

def generate_pdf(
    interval="weekly",
    target_week=None
):

    repo_name, branch_name = (
        get_repo_info()
    )


    students, timeline_activity, student_logs, scope_title = (
        get_git_metrics(
            interval,
            target_week
        )
    )


    if students is None:

        return


    # ---------------------------------------------------------
    # DATE / WEEK INFORMATION
    # ---------------------------------------------------------

    if interval == "weekly":

        if target_week is None:

            (
                week_number,
                week_start,
                week_end
            ) = get_project_week_window()

        else:

            week_number = target_week

            week_start = (
                PROJECT_START_DATE
                +
                datetime.timedelta(
                    days=(week_number - 1) * 7
                )
            )

            week_end = (
                week_start
                +
                datetime.timedelta(
                    days=6
                )
            )


        date_stamp = (
            week_end.strftime(
                "%Y-%m-%d"
            )
        )


        # -----------------------------------------------------
        # WEEKLY DIRECTORY
        # -----------------------------------------------------

        week_directory = os.path.join(
            WEEKLY_REPORTS_DIR,
            f"week_{week_number:02d}"
        )


        os.makedirs(
            week_directory,
            exist_ok=True
        )


        report_title = (
            "Weekly Progress Report (Form-3)"
        )


        doc_name = os.path.join(

            week_directory,

            f"{repo_name}_"
            f"Week_{week_number:02d}_"
            f"Weekly_Progress_Report_"
            f"Form-3_"
            f"{date_stamp}.pdf"
        )


    elif interval == "monthly":

        date_stamp = (
            datetime.date.today()
            .strftime(
                "%Y-%m-%d"
            )
        )


        report_title = (
            "Monthly Progress Report (Form-3)"
        )


        doc_name = (
            f"{repo_name}_"
            f"Monthly_Progress_Report_"
            f"Form-3_"
            f"{date_stamp}.pdf"
        )


    else:

        date_stamp = (
            datetime.date.today()
            .strftime(
                "%Y-%m-%d"
            )
        )


        report_title = (
            "Final Project Evaluation Report"
        )


        doc_name = (
            f"{repo_name}_"
            f"Final_Report_"
            f"{date_stamp}.pdf"
        )


    # ---------------------------------------------------------
    # PDF DOCUMENT
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

        textColor=colors.HexColor(
            "#0F172A"
        ),

        alignment=1,

        spaceAfter=2
    )


    dept_style = ParagraphStyle(

        "DeptStyle",

        parent=styles["Normal"],

        fontSize=9.5,

        leading=13,

        textColor=colors.HexColor(
            "#475569"
        ),

        alignment=1,

        spaceAfter=6
    )


    title_style = ParagraphStyle(

        "TitleStyle",

        parent=styles["Heading2"],

        fontSize=13,

        leading=17,

        textColor=colors.HexColor(
            "#1A365D"
        ),

        alignment=1,

        spaceAfter=5
    )


    repo_style = ParagraphStyle(

        "RepoStyle",

        parent=styles["Normal"],

        fontSize=9.5,

        leading=14,

        textColor=colors.HexColor(
            "#0F172A"
        ),

        spaceAfter=3
    )


    meta_style = ParagraphStyle(

        "MetaStyle",

        parent=styles["Normal"],

        fontSize=8.5,

        textColor=colors.HexColor(
            "#64748B"
        ),

        spaceAfter=8
    )


    section_style = ParagraphStyle(

        "SectionStyle",

        parent=styles["Heading2"],

        fontSize=10.5,

        leading=14,

        textColor=colors.HexColor(
            "#0F172A"
        ),

        spaceBefore=7,

        spaceAfter=4
    )


    sub_section_style = ParagraphStyle(

        "SubSectionStyle",

        parent=styles["Heading3"],

        fontSize=9,

        leading=12,

        textColor=colors.HexColor(
            "#2563EB"
        ),

        spaceBefore=5,

        spaceAfter=2
    )


    msg_style = ParagraphStyle(

        "MsgStyle",

        parent=styles["Normal"],

        fontSize=8,

        leading=10,

        textColor=colors.HexColor(
            "#1E293B"
        )
    )


    meta_cell_style = ParagraphStyle(

        "MetaCellStyle",

        parent=styles["Normal"],

        fontSize=8,

        leading=10,

        textColor=colors.HexColor(
            "#475569"
        ),

        alignment=1
    )


    marks_style = ParagraphStyle(

        "MarksStyle",

        parent=styles["Normal"],

        fontSize=9,

        leading=12,

        textColor=colors.HexColor(
            "#0F172A"
        ),

        alignment=1
    )


    sig_block_style = ParagraphStyle(

        "SigBlockStyle",

        parent=styles["Normal"],

        fontSize=9,

        leading=15,

        textColor=colors.HexColor(
            "#0F172A"
        ),

        alignment=0
    )


    story = []


    # =========================================================
    # 1. HEADER
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
    # 2. METADATA
    # =========================================================

    story.append(

        Paragraph(

            f"<b>Project Repository:</b> "
            f"<font color='#2563EB'><b>"
            f"{html.escape(repo_name)}"
            f"</b></font> "
            f"&nbsp;|&nbsp; "
            f"<b>Branch:</b> "
            f"<code>{html.escape(branch_name)}</code>",

            repo_style
        )
    )


    if interval == "weekly":

        story.append(

            Paragraph(

                f"<b>Project Week:</b> "
                f"Week {week_number} "
                f"&nbsp;|&nbsp; "
                f"<b>Evaluation Window:</b> "
                f"{scope_title} "
                f"&nbsp;|&nbsp; "
                f"<b>Generated On:</b> "
                f"{datetime.date.today().strftime('%B %d, %Y')}",

                meta_style
            )
        )

    else:

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
    # 2. INDIVIDUAL SUMMARY TABLE
    # =========================================================

    section_number = (
        "1"
        if interval == "weekly"
        else "1"
    )


    story.append(

        Paragraph(

            f"{section_number}. "
            f"Individual Contribution Breakdown",

            section_style
        )
    )


    total_commits = sum(

        data["commits"]

        for data in students.values()
    )


    table_data = [

        [
            "Student Name",
            "Commits (%)",
            "Lines Added",
            "Lines Deleted",
            "Net LOC",
            "Active Days"
        ]
    ]


    if students:

        for name, data in students.items():

            pct = (

                data["commits"]
                /
                total_commits
                *
                100

            ) if total_commits > 0 else 0


            net = (
                data["added"]
                -
                data["deleted"]
            )


            table_data.append(

                [

                    html.escape(name),

                    f"{data['commits']} "
                    f"({pct:.1f}%)",

                    f"+{data['added']:,}",

                    f"-{data['deleted']:,}",

                    f"{net:,}",

                    f"{len(data['active_days'])} days"
                ]
            )

    else:

        table_data.append(

            [
                "No commits found in this period.",
                "-",
                "-",
                "-",
                "-",
                "-"
            ]
        )


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
                colors.HexColor(
                    "#1E293B"
                )
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
                colors.HexColor(
                    "#CBD5E1"
                )
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor(
                        "#F8FAFC"
                    )
                ]
            )

        ])
    )


    story.append(
        table
    )


    story.append(
        Spacer(1, 6)
    )



    # =========================================================
    # VISUAL CHARTS
    # =========================================================

    chart_section_number = (
        "2"
        if interval == "weekly"
        else "2"
    )


    story.append(

        Paragraph(

            f"{chart_section_number}. "
            f"Visual Trends & Volume",

            section_style
        )
    )


    chart_image = create_charts(

        students,

        timeline_activity,

        interval
    )


    story.append(
        chart_image
    )


    story.append(
        Spacer(1, 6)
    )


    # =========================================================
    # DETAILED COMMIT LOGS
    # =========================================================

    commit_section_number = (
        "3"
        if interval == "weekly"
        else "3"
    )


    story.append(

        Paragraph(

            f"{commit_section_number}. "
            f"Detailed Commit Logs & "
            f"Mentor Evaluation "
            f"({interval.capitalize()})",

            section_style
        )
    )


    if not student_logs:

        story.append(

            Paragraph(

                "<i>No commit logs found "
                "for this timeframe.</i>",

                styles["Normal"]
            )
        )

    else:

        for student_name, logs in (
            student_logs.items()
        ):

            student_section = []


            student_section.append(

                Paragraph(

                    f"<b>Student:</b> "
                    f"{html.escape(student_name)} "
                    f"— "
                    f"<i>{len(logs)} commit(s)</i>",

                    sub_section_style
                )
            )


            log_table_data = [

                [
                    "Date",
                    "Hash",
                    "Commit Message",
                    "Mentor Marks (/10)"
                ]
            ]


            # -------------------------------------------------
            # FIRST COMMIT ROW
            # -------------------------------------------------

            first_date, first_sha, first_msg = (
                logs[0]
            )


            safe_msg = (

                html.escape(first_msg)

                if first_msg

                else "(No commit message)"
            )


            log_table_data.append(

                [

                    Paragraph(
                        first_date,
                        meta_cell_style
                    ),

                    Paragraph(
                        f"<code>{first_sha}</code>",
                        meta_cell_style
                    ),

                    Paragraph(
                        safe_msg,
                        msg_style
                    ),

                    Paragraph(
                        "<b>_____ / 10</b>",
                        marks_style
                    )
                ]
            )


            # -------------------------------------------------
            # SUBSEQUENT COMMIT ROWS
            # -------------------------------------------------

            for (
                date_val,
                sha_val,
                msg_val
            ) in logs[1:]:

                safe_msg = (

                    html.escape(msg_val)

                    if msg_val

                    else "(No commit message)"
                )


                log_table_data.append(

                    [

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

                        ""
                    ]
                )


            num_rows = len(
                log_table_data
            )


            log_table = Table(

                log_table_data,

                colWidths=[
                    65,
                    50,
                    335,
                    90
                ]
            )


            t_style = [

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#475569"
                    )
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
                    colors.HexColor(
                        "#CBD5E1"
                    )
                ),

                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (2, -1),
                    [
                        colors.white,
                        colors.HexColor(
                            "#F8FAFC"
                        )
                    ]
                ),

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
                    colors.HexColor(
                        "#FEF3C7"
                    )
                )

            ]


            log_table.setStyle(
                TableStyle(
                    t_style
                )
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
    # SIGNATURES
    # =========================================================

    story.append(
        Spacer(1, 16)
    )


    mentor_cell = [

        Paragraph(
            "<b>Name:</b> "
            "___________________________",
            sig_block_style
        ),

        Paragraph(
            "<b>Designation:</b> "
            "Project Mentor",
            sig_block_style
        ),

        Spacer(1, 6),

        Paragraph(
            "<b>Signature:</b> "
            "________________________",
            sig_block_style
        )

    ]


    coordinator_cell = [

        Paragraph(
            "<b>Name:</b> "
            "___________________________",
            sig_block_style
        ),

        Paragraph(
            "<b>Designation:</b> "
            "Lab Coordinator",
            sig_block_style
        ),

        Spacer(1, 6),

        Paragraph(
            "<b>Signature:</b> "
            "________________________",
            sig_block_style
        )

    ]


    sig_table = Table(

        [
            [
                mentor_cell,
                coordinator_cell
            ]
        ],

        colWidths=[
            270,
            270
        ]
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
            )

        ])
    )


    story.append(

        KeepTogether(
            sig_table
        )
    )


    # =========================================================
    # BUILD PDF
    # =========================================================

    doc.build(
        story
    )


    # =========================================================
    # SAVE WEEKLY HISTORY
    # =========================================================

    if interval == "weekly":

        update_week_history(

            week_number,

            week_start,

            week_end,

            doc_name,

            students
        )


    # =========================================================
    # SUCCESS MESSAGE
    # =========================================================

    print(
        f"\n[SUCCESS] Generated: "
        f"{doc_name}"
    )


    print(
        f" -> Found "
        f"{len(students)} student(s) "
        f"and "
        f"{total_commits} total commits."
    )


    if interval == "weekly":

        print(
            f" -> Project Week: "
            f"{week_number}"
        )

        print(
            f" -> Evaluation Window: "
            f"{scope_title}"
        )

        print(
            f" -> History File: "
            f"{REPORT_HISTORY_FILE}"
        )


# -------------------------------------------------------------
# GENERATE ALL PROJECT WEEKS
# -------------------------------------------------------------

def generate_all_weeks():

    """
    Generates weekly reports for every project week
    from PROJECT_START_DATE through the current week.
    """

    weeks = get_all_project_weeks()


    print()
    print(
        "=============================================="
    )
    print(
        "GENERATING ALL PROJECT WEEKS"
    )
    print(
        "=============================================="
    )


    for week in weeks:

        print(
            f"\nProcessing Week "
            f"{week['week_number']}..."
        )


        generate_pdf(
            "weekly",
            week["week_number"]
        )


# -------------------------------------------------------------
# SHOW WEEKLY HISTORY
# -------------------------------------------------------------

def show_history():

    """
    Displays the stored weekly project history.
    """

    history = load_history()


    print()
    print(
        "=============================================="
    )
    print(
        "PROJECT WEEKLY HISTORY"
    )
    print(
        "=============================================="
    )


    print(
        f"Project Start: "
        f"{history.get('project_start')}"
    )


    print()


    if not history.get(
        "weeks"
    ):

        print(
            "No weekly reports recorded yet."
        )

        return


    for week in history[
        "weeks"
    ]:

        print(

            f"Week "
            f"{week['week_number']}: "

            f"{week['start']} "
            f"-> "
            f"{week['end']} "

            f"| Commits: "
            f"{week['total_commits']} "

            f"| Net LOC: "
            f"{week['total_net_loc']}"
        )


# -------------------------------------------------------------
# MAIN
# -------------------------------------------------------------

if __name__ == "__main__":

    chosen_interval = (

        sys.argv[1].lower()

        if len(sys.argv) > 1

        else "weekly"
    )


    # ---------------------------------------------------------
    # CURRENT WEEK
    # ---------------------------------------------------------

    if chosen_interval == "weekly":

        generate_pdf(
            "weekly"
        )


    elif chosen_interval == "current":

        generate_pdf(
            "weekly"
        )


    # ---------------------------------------------------------
    # SPECIFIC WEEK
    # ---------------------------------------------------------

    elif chosen_interval == "week":

        if len(sys.argv) < 3:

            print(
                "Usage: "
                "python generate_report.py "
                "week <number>"
            )

            sys.exit(1)


        try:

            week_number = int(
                sys.argv[2]
            )

        except ValueError:

            print(
                "Week number must be an integer."
            )

            sys.exit(1)


        generate_pdf(
            "weekly",
            week_number
        )


    # ---------------------------------------------------------
    # ALL WEEKS
    # ---------------------------------------------------------

    elif chosen_interval == "all":

        generate_all_weeks()


    # ---------------------------------------------------------
    # HISTORY
    # ---------------------------------------------------------

    elif chosen_interval == "history":

        show_history()


    # ---------------------------------------------------------
    # MONTHLY
    # ---------------------------------------------------------

    elif chosen_interval == "monthly":

        generate_pdf(
            "monthly"
        )


    # ---------------------------------------------------------
    # FINAL
    # ---------------------------------------------------------

    elif chosen_interval == "final":

        generate_pdf(
            "final"
        )


    # ---------------------------------------------------------
    # INVALID COMMAND
    # ---------------------------------------------------------

    else:

        print()

        print(
            "Usage:"
        )

        print()

        print(
            "  python generate_report.py weekly"
        )

        print(
            "  python generate_report.py current"
        )

        print(
            "  python generate_report.py week <number>"
        )

        print(
            "  python generate_report.py all"
        )

        print(
            "  python generate_report.py history"
        )

        print(
            "  python generate_report.py monthly"
        )

        print(
            "  python generate_report.py final"
        )

        print()