Here is a complete `README.md` file for the agent project we built.

-----

# 📊 Daily Report Auditor Agent

This project is an AI agent built with the **OpenAI Assistants API** and **Python**. Its purpose is to automatically audit a team's Google Mail inboxes to verify that all members have submitted their daily task reports by a specific deadline.

It securely connects to the **Google Gmail API** using a **Service Account** with **Domain-Wide Delegation** (impersonation) to read inboxes, then uses the OpenAI Assistant's logic to analyze the findings and generate a summary report.

## 🚀 Features

  * **AI-Powered Logic:** Uses an OpenAI Assistant to understand the task, call tools, and analyze results.
  * **Secure Authentication:** Uses a Google Service Account (JSON key) for secure, non-human "agent-to-agent" login.
  * **User Impersonation:** Leverages Google Workspace Domain-Wide Delegation to read specific user inboxes without needing their passwords.
  * **Timezone-Aware:** Checks email timestamps against a hard-coded deadline (e.g., 5:00 PM EST).
  * **Automated Reporting:** Generates a clean Markdown table of who is on time and who is missing or late.

-----

## 🛠️ Prerequisites

Before you can run this script, you **must** complete the following setup. This is the most complex part of the project.

### 1\. Python

  * You must have **Python 3.7+** installed.
  * **On Windows:** If you get a `Python was not found...` error, you must **fix your App execution aliases** or use the `py` command (e.g., `py your_script.py`).

### 2\. OpenAI Account

  * You need an **OpenAI API Key** with credits on your account.
  * You will set this as an environment variable (see **Usage**).

### 3\. Google Cloud Project & Service Account

You need to create the agent's "identity" in Google Cloud.

1.  **Create a Google Cloud Project:** Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  **Enable the Gmail API:** In your project, go to "APIs & Services" \> "Library" and search for **"Gmail API"**. Click **Enable**.
3.  **Create a Service Account:**
      * Go to "IAM & Admin" \> "Service Accounts".
      * Click **"+ Create Service Account"**.
      * Give it a name (e.g., `daily-report-auditor`).
4.  **Download the JSON Key:**
      * Click on your new service account's email address.
      * Go to the **"Keys"** tab.
      * Click **"Add Key"** \> **"Create new key"**.
      * Select **JSON** and click **"Create"**.
      * A `.json` file will download. **This is your agent's "password."** Guard it carefully.

### 4\. Google Workspace Admin (CRITICAL)

This is the **"login"** step. Your agent's identity must be given permission to access your team's inboxes. **You must be a Google Workspace Super Admin to do this.**

1.  **Find your Service Account's Client ID:**
      * Go back to "IAM & Admin" \> "Service Accounts".
      * Click on your service account.
      * Go to the **"Details"** tab and copy the **"Unique ID"** (it's a long number).
2.  **Authorize Domain-Wide Delegation:**
      * Go to your Google Workspace Admin Console at [admin.google.com](https://admin.google.com).
      * Go to **Security \> Access and data control \> API Controls**.
      * Click **"Manage Domain Wide Delegation"**.
      * Click **"Add new"**.
      * Paste the **"Client ID"** (the long number) you just copied.
      * In the **"OAuth scopes"** field, paste this exact scope:
        `https://www.googleapis.com/auth/gmail.readonly`
      * Click **"Authorize"**.

It may take 5-10 minutes for this permission to become active.

-----

## ⚙️ Installation

1.  Clone or download this project's files.
2.  Place your downloaded `service_account_key.json` file in the same directory as the script.
3.  Install the required Python libraries:
    ```bash
    pip install --upgrade openai google-api-python-client google-auth-httplib2 google-auth-oauthlib pytz
    ```

-----

## 🔑 Configuration

Open the Python script (`emailAgent.py` or `run_audit.py`) and edit the configuration variables at the top:

```python
# --- 1. Configuration (Set your details here) ---

# -- Google Config --
# Change this to the exact name of your downloaded key file
SERVICE_ACCOUNT_FILE = 'service_account_key.json' 

# Change these to the real email addresses you are auditing
USERS_TO_AUDIT = ['alice@yourcompany.com', 'bob@yourcompany.com', 'charlie@yourcompany.com']

# -- OpenAI Config --
# The script will look for your key in an environment variable
client = OpenAI() 
```

-----

## 🏃‍♂️ How to Run

1.  Open your terminal or command prompt.
2.  Navigate to the project directory:
    ```bash
    cd path/to/your-project-folder
    ```
3.  Set your **OpenAI API Key** as an environment variable:
      * **macOS/Linux:**
        ```bash
        export OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
        ```
      * **Windows (CMD):**
        ```bash
        set OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
        ```
      * **Windows (PowerShell):**
        ```powershell
        $env:OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
        ```
4.  Run the script:
    ```bash
    python emailAgent.py
    ```
    *(On Windows, you may need to use `py emailAgent.py`)*

The script will run, log its progress to the console (including the "login" attempts), and finally print the AI-generated audit table.

-----

## architecture-diagram How it Works

1.  The script starts and creates an **OpenAI Assistant** with a custom "system prompt" that defines its role, the team list, and the deadline.
2.  The script creates a **Thread** and asks the Assistant to "run the audit."
3.  The Assistant's AI logic determines it needs to use its `search_all_required_inboxes` tool. The run **pauses** and enters a `requires_action` state.
4.  The Python script executes the local `search_all_required_inboxes()` function.
5.  This function loops through the `USERS_TO_AUDIT` list. For each user, it performs the **"agent login"** (`creds.with_subject(user_email)`) to impersonate them.
6.  It uses the Gmail API to search that user's inbox for matching emails.
7.  The function collects all found emails into a single JSON list and returns it to the Assistant.
8.  The script submits this JSON data back to the Assistant, which **resumes** its run.
9.  The Assistant analyzes the JSON (comparing `timestamp_unix` to the `DEADLINE_UNIX`), formulates its findings, and generates the final Markdown table as its response.
10. The script prints the Assistant's final message and cleans up.

-----

## 🩺 Troubleshooting

  * **ERROR:** `Python was not found...`

      * **Cause:** A common Windows issue where a "stub" blocks the real Python installation.
      * **Fix:** Run the script using `py emailAgent.py` OR go to "App execution aliases" in Windows Settings and turn off the `python.exe` stubs.

  * **ERROR:** `Unable to create process... The system cannot find the file specified.`

      * **Cause:** Your IDE (like VS Code) is pointing to a non-existent Python path (e.g., `C:\Python313`).
      * **Fix:** In VS Code, press `Ctrl+Shift+P` \> **"Python: Select Interpreter"** and choose the correct Python installation from the list.

  * **ERROR:** `unauthorized_client: Client is unauthorized to retrieve access tokens...`

      * **Cause:** This is the most common error. You skipped or incorrectly configured the **Google Workspace Admin** setup (Prerequisite \#4).
      * **Fix:** Double-check that you have authorized the correct **Client ID** (the long number, *not* the email) and the *exact* scope (`https.://.../gmail.readonly`) in the "Manage Domain Wide Delegation" settings of your Admin Console. Wait 10 minutes for the change to take effect.