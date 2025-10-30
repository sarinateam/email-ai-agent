📊 Daily Report AI Auditor
This project contains two distinct AI agents designed to audit daily email reports using the OpenAI API and Google Gmail.

Admin Agent (admin_agent.py):

Use Case: For Google Workspace Admins.

Action: Logs in as a "robot" (Service Account) to "impersonate" users. It checks their "Sent" folders to verify they sent their reports.

Login Method: Server-to-Server (Service Account JSON).

Individual Agent (individual_agent.py):

Use Case: For any individual user.

Action: Logs in as you (using a one-time browser login) and checks your "Inbox" for reports you received from your team.

Login Method: OAuth 2.0 (Desktop App JSON).

🚀 Core Features
AI-Powered Logic: Uses an OpenAI Assistant to intelligently parse email subjects for keywords (e.g., "Daily Status Update" OR "Daily Task Report") and flexible date formats (e.g., 30-10-2025 vs. 10/30/2025).

Two Login Modes: Choose the script that matches your specific goal and account type.

Dynamic Team List: Both scripts dynamically build the AI's instructions from a single Python list, so you only need to update your team in one place.

Timezone-Aware: Deadlines are calculated in a specific timezone (e.g., IST) and compared against the email's precise arrival timestamp.

🛠️ Common Setup (For Both Agents)
Install Python 3.7+ on your system.

Create a Google Cloud Project: Go to the Google Cloud Console and create a new project.

Enable the Gmail API:

In your project, go to APIs & Services > Library.

Search for "Gmail API" and click on it.

Click the "Enable" button. (This is required for both methods).

Install Libraries: Open your terminal and install all the required packages:

Bash

pip install --upgrade openai google-api-python-client google-auth-httplib2 google-auth-oauthlib pytz python-dateutil
Get OpenAI API Key: Get your key from your OpenAI API Keys page.

🔒 Mode 1: Admin Agent (admin_agent.py) Setup
Use this if you are a Google Workspace Admin and want to check what your users have sent.

1. Google Setup (Service Account)
Create Service Account:

In your Google Cloud project, go to IAM & Admin > Service Accounts.

Click "+ Create Service Account". Give it a name (e.g., daily-report-auditor).

Download JSON Key:

Click on your new service account's email address.

Go to the "Keys" tab. Click "Add Key" > "Create new key".

Select JSON and click "Create". A file (e.g., service_account_1.json) will download. Save this in your project folder.

Authorize Domain-Wide Delegation (Critical Admin Task):

First, find your Service Account's Client ID. Go to its "Details" tab and copy the "Unique ID" (it's a long number).

Go to your Google Workspace Admin Console (admin.google.com).

Go to Security > Access and data control > API Controls.

Click "Manage Domain Wide Delegation".

Click "Add new".

Paste the "Client ID" (the long number).

In the "OAuth scopes" field, paste: https://www.googleapis.com/auth/gmail.readonly

Click "Authorize". (This can take 10-15 minutes to activate).

2. Script Configuration (admin_agent.py)
Open admin_agent.py and edit the configuration variables at the top:

Python

# The name of your downloaded service account file
SERVICE_ACCOUNT_FILE = 'service_account_1.json' 

# The list of user inboxes you want to check
USERS_TO_AUDIT = [
    'user1@yourcompany.com', 
    'user2@yourcompany.com'
]
3. How to Run (Admin Agent)
Set your OpenAI API Key as an environment variable (see below).

Run the script: python admin_agent.py

The agent will run automatically. It will not open a browser.

🔑 Mode 2: Individual Agent (individual_agent.py) Setup
Use this if you have a personal (@gmail.com) account and want to check your inbox for emails from your team.

1. Google Setup (OAuth 2.0)
Configure OAuth Consent Screen:

In your Google Cloud project, go to APIs & Services > OAuth consent screen.

Choose "External" and click "Create".

Fill in the required fields (App name, User support email, Developer contact email).

Click "Save and Continue" on all other steps.

On the "Test users" step, click "+ Add Users" and add your own Gmail address. This is critical.

Create Credentials:

Go to APIs & Services > Credentials.

Click "+ Create Credentials" > "OAuth client ID".

For "Application type," select "Desktop app".

Give it a name and click "Create".

Click "DOWNLOAD JSON".

Rename this file to credentials.json and save it in your project folder.

2. Script Configuration (individual_agent.py)
Open individual_agent.py and edit the configuration variables at the top:

Python

# This should match your downloaded file name
CREDENTIALS_FILE = 'credentials.json'

# The list of people you are expecting reports FROM
USERS_TO_AUDIT = [
    'nevin.m@ateamsoftsolutions.com', 
    'vijay.shankar@ateamsoftsolutions.com'
]
3. How to Run (Individual Agent)
Set your OpenAI API Key as an environment variable (see below).

Delete token.json if it exists from a previous run.

Run the script: python individual_agent.py

First Run Only: Your browser will open. You must log in to your Google account (the one you set as a "Test user") and click "Allow". The script then creates a token.json file to save your login.

All future runs will be automatic.

🚀 Running the Project
Open your terminal in the project folder.

Set your OpenAI API Key as an environment variable.

macOS/Linux:

Bash

export OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
Windows (CMD):

Bash

set OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
Windows (PowerShell):

PowerShell

$env:OPENAI_API_KEY='sk-YourSecretKeyGoesHere'
Run your chosen script:

Bash

# For admin mode
python admin_agent.py

# OR

# For individual mode
python individual_agent.py
Troubleshooting
Error (Admin): unauthorized_client

Cause: Your Domain-Wide Delegation is wrong or hasn't activated.

Fix: Wait 15 minutes. If it persists, double-check that you authorized the Client ID (the long number), not the email, and that the scope https.../gmail.readonly is exact.

Error (Individual): Error 403: access_denied

Cause: You didn't add your email as a "Test user" on the OAuth Consent Screen.

Fix: Go back to the OAuth consent screen setup in Google Cloud, click "Edit App", go to the "Test users" step, and add your email.

Error (Individual): Error 401: invalid_client

Cause: Your credentials.json is wrong.

Fix: Ensure you are using the "Desktop app" JSON file, not a "Service Account" one.

Error (Both): HttpError 403... Gmail API has not been used...

Cause: You didn't enable the Gmail API.

Fix: Go to the link in the error message and click the "Enable" button