import requests
import pandas as pd
import os
from datetime import datetime
from jinja2 import Template
import pdfkit
import matplotlib.pyplot as plt
from io import BytesIO
import base64

# List of repositories to track
REPOS = [
    "octocat/Hello-World",
    "torvalds/linux",
    "django/django",
    "pallets/flask",
    "ansible/ansible",
    "psf/requests",
    "numpy/numpy",
    "scikit-learn/scikit-learn",
    "pandas-dev/pandas",
    "keras-team/keras",
    "tensorflow/tensorflow",
    "scrapy/scrapy",
    "matplotlib/matplotlib",
    "pytest-dev/pytest",
    "fastapi/fastapi",
]


OUTPUT_DIR = "output"
CSV_FILE = os.path.join(OUTPUT_DIR, "github_stats.csv")
PDF_FILE = os.path.join(
    OUTPUT_DIR, f"github_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
)

# Optional GitHub token for higher API rate limits
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# Ensure the output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_repo_stats(repo_full_name: str) -> dict:
    """
    Fetch repository statistics from GitHub API.

    Parameters:
        repo_full_name (str): Full repo name in "owner/repo" format.

    Returns:
        dict: Dictionary containing repository stats.
    """
    url = f"https://api.github.com/repos/{repo_full_name}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    return {
        "repo_name": repo_full_name,
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "issues": data.get("open_issues_count", 0),
        "watchers": data.get("watchers_count", 0),
        "last_push": data.get("pushed_at", ""),
        "date": datetime.now().strftime("%Y-%m-%d"),
    }


def update_csv(stats_list: list[dict]):
    """
    Update the historical CSV file with the latest stats.
    Appends new data to existing CSV or creates a new file if it doesn't exist.

    Parameters:
        stats_list (list[dict]): List of repository stats dictionaries.
    """
    df_new = pd.DataFrame(stats_list)
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df_updated = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_updated = df_new

    df_updated.to_csv(CSV_FILE, index=False)
    print(f"CSV updated → {CSV_FILE}")


def generate_bar_chart(stats_list, key, title, color="#4CAF50") -> str:
    """
    Generate a horizontal bar chart from repo statistics and return it as a Base64 string.

    Parameters:
        stats_list (list[dict]): List of repository stats dictionaries.
        key (str): The statistic to visualize ('stars', 'forks', etc.).
        title (str): Chart title.
        color (str): Bar color in HEX format.

    Returns:
        str: Base64-encoded PNG image string for embedding in HTML.
    """
    repos = [repo["repo_name"] for repo in stats_list]
    values = [repo[key] for repo in stats_list]

    plt.figure(figsize=(8, 4))
    plt.barh(repos, values, color=color)
    plt.xlabel(key.capitalize())
    plt.title(title)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_pie_chart(stats_list, key, title) -> str:
    """
    Generate a pie chart showing the proportion of a specific stat across repos.

    Parameters:
        stats_list (list[dict]): List of repository stats dictionaries.
        key (str): The statistic to visualize ('stars', etc.).
        title (str): Chart title.

    Returns:
        str: Base64-encoded PNG image string for embedding in HTML.
    """
    labels = [repo["repo_name"] for repo in stats_list]
    sizes = [repo[key] for repo in stats_list]

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%")
    plt.title(title)

    buf = BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def generate_pdf_report(stats_list: list[dict]):
    """
    Generate a PDF report from repository stats using an HTML template.

    Parameters:
        stats_list (list[dict]): List of repository stats dictionaries.
    """
    template_path = os.path.join("resources", "report_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_html = f.read()

    # Calculate summary statistics
    total_stars = sum(repo["stars"] for repo in stats_list)
    total_forks = sum(repo["forks"] for repo in stats_list)
    total_issues = sum(repo["issues"] for repo in stats_list)
    total_watchers = sum(repo["watchers"] for repo in stats_list)

    html_filled = Template(template_html).render(
        stats=stats_list,
        date=datetime.now().strftime("%Y-%m-%d"),
        total_stars=total_stars,
        total_forks=total_forks,
        total_issues=total_issues,
        total_watchers=total_watchers,
        stars_chart=f"data:image/png;base64,{generate_bar_chart(stats_list, 'stars', 'Top Repositories by Stars')}",
        forks_chart=f"data:image/png;base64,{generate_bar_chart(stats_list, 'forks', 'Top Repositories by Forks', '#2196F3')}",
        stars_pie_chart=f"data:image/png;base64,{generate_pie_chart(stats_list, 'stars', 'Stars Proportion')}",
    )

    pdfkit.from_string(html_filled, PDF_FILE)
    print(f"PDF report generated → {PDF_FILE}")


if __name__ == "__main__":
    stats = []
    for repo in REPOS:
        try:
            stats.append(fetch_repo_stats(repo))
            print(f"Fetched stats for {repo}")
        except Exception as e:
            print(f"Error fetching {repo}: {e}")

    update_csv(stats)
    generate_pdf_report(stats)
