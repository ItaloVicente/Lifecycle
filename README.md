# README -- Detection and Lifecycle Analysis of Code Clones in AI-Generated Pull Requests

This project performs **mining, detection, classification, and lifecycle
analysis of code clones** found in Pull Requests (PRs) submitted by **AI
agents**.

The pipeline covers the entire process: dataset extraction, clone
detection (via Simian and Siamese), classification, and lifecycle
computation for each clone across the commits of a PR.

------------------------------------------------------------------------

## ⚠️ System Requirements

**This project only works on Ubuntu/Linux systems.** The pipeline relies on Linux-specific tools and shell scripts (e.g., `run_all.sh`) and is not compatible with Windows or macOS.

**Required:**
- Ubuntu (or compatible Linux distribution)
- Python 3.12 or higher
- Git
- Poetry (for dependency management) or pip

------------------------------------------------------------------------

## 📦 1. Setting Up the Environment

### Option A: Using Poetry (Recommended)

This project uses **Poetry** for dependency management. If you don't have Poetry installed, install it first:

```bash
# Install Poetry on Ubuntu/Linux
curl -sSL https://install.python-poetry.org | python3 -
```

After installing Poetry, add it to your PATH (follow the instructions shown after installation).

Then, install the project dependencies:

```bash
# Install all dependencies
poetry install

# Activate the virtual environment created by Poetry
poetry shell
```

### Option B: Using pip and venv

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

------------------------------------------------------------------------

## ⚙️ 2. Configuration

### 🔐 2.1. GitHub Token Configuration

Create a `.env` file in the project root directory:

```bash
cp .env-example .env
```

Edit the `.env` file and add your GitHub personal access token:

```
GITHUB_TOKEN=your_github_token_here
```

**Important:** You need a GitHub personal access token to access the GitHub API. Generate one at: https://github.com/settings/tokens

### 📁 2.2. Settings Configuration

Edit the `settings.ini` file in the project root directory. It follows this structure:

```ini
[DETAILS]

# Minimum number of lines for a clone
min_clone = 6

# Maximum number of project versions your machine can have
max_befores = 1

# Programming language for clone detection
# Supported languages: C (.c), C# (.cs), Java (.java), Python (.py), 
# PHP (.php), Ruby (.rb), WSDL (.wsdl), ATL (.atl)
# Use the full language name (e.g., "Python", "Java", "C", "C#")
language = Python
```

**Important Notes:**

-   **language** must be the *full name* of the programming language (e.g., `Python`, `Java`, `C`, `C#`, `Go`).
-   The language name should match what NiCad expects (see comments in `settings.ini` for supported languages).

------------------------------------------------------------------------

## ▶️ 3. Executing the Pipeline

### Quick Start: Using the Automated Script

The easiest way to run the entire pipeline is using the `run_all.sh` script, which executes all numbered scripts (0-10) in sequence:

```bash
# Make sure the script is executable
chmod +x run_all.sh

# Run the entire pipeline
./run_all.sh
```

The script will:
- Execute all scripts from `0_get_aidev_csv.py` to `10_count_lifecycle.py` in sequence
- Display progress and execution time for each step
- Stop execution if any script fails
- Generate a detailed execution summary report in `execution_summary_YYYYMMDD_HHMMSS.txt`

The summary report includes:
- Overall statistics (successes, failures, total execution time)
- Step-by-step execution details with individual timing for each script

### Manual Execution

If you prefer to run scripts individually:

1.  First, run:
    ```bash
    python3 0_get_aidev_csv.py
    ```

2.  Then execute the remaining scripts in ascending order:
    ```bash
    python3 1_prs_project.py
    python3 2_mining_repos.py
    python3 3_get_commits_prs_correct.py
    python3 4_break_projects.py
    python3 5_take_projects.py
    python3 6_detect_clone.py
    python3 7_parser_clones.py
    python3 8_track_clones.py
    python3 9_made_lifecycle.py
    python3 10_count_lifecycle.py
    ```

------------------------------------------------------------------------

## 📂 4. Generated Directories

During execution, the pipeline creates several directories to store intermediate and final results:

### Core Data Directories

- **`AIDev_Dataset/`**: Contains the downloaded AI Dev dataset CSV files with information about AI-generated pull requests.

- **`metadata/`**: Stores metadata files including project configurations, PR information, and intermediate processing data.

- **`git_repos/`**: Contains cloned Git repositories for each project being analyzed. These are the repositories that will be scanned for code clones.

### Clone Detection Results

- **`search_results/`**: Stores XML files containing clone detection results from NiCad. Each file contains detected code clones for a specific project, PR, and commit.

- **`clones_classified/`**: Contains classified clone data, where clones are categorized by type (e.g., persistent, transient, etc.) and behavior.

### Analysis Results

- **`lifetimes/`**: Stores lifecycle analysis results, tracking how clones evolve across commits in pull requests. Contains data about clone persistence, duration, and evolution patterns.

- **`figures/`**: Contains generated visualizations and plots related to the analysis (if any scripts generate figures).

### Summary Reports

- **`execution_summary_*.txt`**: Detailed execution reports generated by `run_all.sh`, containing timing information and execution status for each script.

**Note:** These directories are created automatically when needed. You can safely delete them to start fresh, but be aware that regenerating data may take significant time depending on the number of projects and PRs being analyzed.

------------------------------------------------------------------------

## 🧪 5. Purpose of This Tool

This pipeline enables:

-   Mining PRs generated by autonomous AI agents.
-   Detecting code clones using NiCad (clone detection tool).
-   Classifying clones by type and behavior.
-   Computing recurrence and lifecycle duration of each clone.
-   Counting affected PRs.
-   Evaluating persistence and evolution of clones across commits.

The framework is designed for research on the **impact of AI agents on
software development**, especially regarding:

-   Code duplication
-   Software quality
-   Maintainability
-   Evolutionary behavior of AI-generated code

------------------------------------------------------------------------

## 📋 6. Pipeline Overview

The pipeline consists of 11 scripts executed in sequence:

1. **`0_get_aidev_csv.py`**: Downloads the AI Dev dataset
2. **`1_prs_project.py`**: Extracts PR information for projects
3. **`2_mining_repos.py`**: Clones Git repositories for analysis
4. **`3_get_commits_prs_correct.py`**: Extracts commit information from PRs
5. **`4_break_projects.py`**: Breaks down projects into analyzable units
6. **`5_take_projects.py`**: Selects projects for clone detection
7. **`6_detect_clone.py`**: Performs clone detection using NiCad
8. **`7_parser_clones.py`**: Parses clone detection results
9. **`8_track_clones.py`**: Tracks clones across commits
10. **`9_made_lifecycle.py`**: Computes clone lifecycles and classifies them
11. **`10_count_lifecycle.py`**: Generates final statistics and counts

------------------------------------------------------------------------

## ✔️ 7. Contact

This project was developed for academic and scientific purposes related
to the study of clone generation and evolution in AI-generated code.

------------------------------------------------------------------------
