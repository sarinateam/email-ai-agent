import json
import time
import datetime
import pytz
import os.path
from openai import OpenAI
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil.parser import parse as parse_date


CREDENTIALS_FILE = 'credentials.json'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_FILE = 'token.json' 
USERS_TO_AUDIT = [
    'vijay.shankar@ateamsoftsolutions.com', 
    'sarath.krishnan@ateamsoftsolutions.com', 
    'nanda.krishnan@ateamsoftsolutions.com', 
    'vineeth@ateamsoftsolutions.com',
    'saran.raj@ateamsoftsolutions.com',
    'nevin.m@ateamsoftsolutions.com',
    'aneesh@ateamsoftsolutions.com'
]

# --- OpenAI Config ---
client = OpenAI() 


def get_gmail_service():

    """
    This is the new "login" flow for a personal account.
    It will open a browser window for you to click "Allow" the first time.
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Please authorize in the browser...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Credentials saved to {TOKEN_FILE}")

    try:
        service = build('gmail', 'v1', credentials=creds)
        print("Gmail service built successfully.")
        return service
    except HttpError as error:
        print(f"An error occurred building the service: {error}")
        return None


def search_my_inbox_for_reports():
    """
    Searches YOUR inbox for emails FROM Alice, Bob, and Charlie
    with keywords "Daily Task Report" OR "Daily status update".
    It does NOT check the date; it leaves that for the AI.
    """
    print("--- [Tool Called: search_my_inbox_for_reports] ---")
    
    service = get_gmail_service()
    if not service:
        return json.dumps([{"error": "Failed to authenticate with Gmail."}])

    all_found_emails = []
    
    try:
        tz = pytz.timezone("IST") 
        today_str = datetime.datetime.now(tz).strftime('%Y-%m-%d')
    except Exception as e:
        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
    print(f"Searching for keywords: (Daily status update OR Daily Task Report)")

    for user_email in USERS_TO_AUDIT:
        try:
            print(f"Searching for reports from: {user_email}...")
    
            search_query = f'subject:("Daily status update" OR "Daily Task Report" OR "Work Process" OR "Project Report" OR "Daily Task Report" OR "Task Progress" OR "Task Status") from:{user_email} in:inbox'

            results = service.users().messages().list(
                userId='me', 
                q=search_query,
                maxResults=1
            ).execute()
            
            messages = results.get('messages', [])

            if not messages:
                print(f"No potential reports found from {user_email}.")
                continue

            for msg_stub in messages: 
                msg = service.users().messages().get(
                    userId='me', id=msg_stub['id'], format='metadata',
                    metadataHeaders=['Subject', 'Date']
                ).execute()
                
                subject = next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject')
                date_str = next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Date')

                timestamp_unix = int(msg['internalDate']) // 1000 
                
                all_found_emails.append({
                    "sender": user_email,
                    "subject": subject, 
                    "timestamp_unix": timestamp_unix,
                    "timestamp_human": date_str
                })
                print(f"Found potential report from {user_email}: '{subject}'")

        except HttpError as e:
            print(f"ERROR searching for {user_email}'s emails: {e}")
            all_found_emails.append({
                "sender": user_email,
                "error": f"Failed to search for emails: {str(e)}"
            })
        except Exception as e:
             print(f"An unexpected error occurred for {user_email}: {e}")

    return json.dumps({
        "today_is": today_str,
        "found_emails": all_found_emails
    })

# --- 3. The Assistant's Definition (The "Instructions") ---

try:
    tz = pytz.timezone("IST")
    today = datetime.datetime.now(tz).date()
    deadline_dt = tz.localize(datetime.datetime.combine(today, datetime.time(20, 0, 0)))
    DEADLINE_UNIX = int(deadline_dt.timestamp())
    print(f"Today's 8:00 PM IST deadline is UNIX timestamp: {DEADLINE_UNIX}")
except Exception as e:
    print(f"Warning: Could not set EST timezone. Using simple timestamp. {e}")
    DEADLINE_UNIX = int(datetime.datetime.now().replace(hour=20, minute=0, second=0, microsecond=0).timestamp())

try:
    tz = pytz.timezone("IST")
    TODAY_STR = datetime.datetime.now(tz).strftime('%Y-%m-%d')
except Exception:
    TODAY_STR = datetime.datetime.now().strftime('%Y-%m-%d')

# 1. Generate the team list string *dynamically* from your single source
team_list_for_prompt = "\n".join([f"- {user}" for user in USERS_TO_AUDIT])


AUDITOR_INSTRUCTIONS = f"""
Role: You are the Daily Report Auditor.
Today's Date: {TODAY_STR}
Deadline: The deadline for all reports was 8:00 PM IST today.
Today's Deadline Timestamp (UNIX): {DEADLINE_UNIX}

Team to Check (for emails sent FROM them):
{team_list_for_prompt}

Action & Output:
1.  Call the `search_my_inbox_for_reports` tool. It will return a JSON object containing all emails that *might* be reports.
2.  Analyze the `found_emails` list from the tool.
3.  For each email, you must perform two checks:
    a. **Date Check:** Look at the `subject` string. Does it contain a date that matches today's date ({TODAY_STR})? The format might be different (e.g., '30-10-2025' or '10/30/2025' or 'Oct 30 2025'). You must be smart and parse it.
    b. **Time Check:** Look at the `timestamp_unix`.
4.  For each team member in the 'Team to Check' list, determine their status:
    - **On Time:** A report was found AND the date in the subject matches today AND its `timestamp_unix` is less than or equal to {DEADLINE_UNIX}.
    - **Late:** A report was found AND the date in the subject matches today BUT its `timestamp_unix` is greater than {DEADLINE_UNIX}.
    - **Missing:** No email was found, OR no email was found with a subject line containing today's date.
5.  Generate the final report table, including *all* members from the 'Team to Check' list.
6.  Present *only* the final table as your response.
"""

email_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_my_inbox_for_reports",
        "description": "Searches the user's personal inbox for emails sent FROM the required team members with potential report keywords.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

def main():
    print("Creating Daily Report Auditor agent...")
    assistant = client.beta.assistants.create(
        name="Daily Report Auditor",
        instructions=AUDITOR_INSTRUCTIONS,
        model="gpt-4-turbo", # or gpt-4o
        tools=[email_tool_schema]
    )

    print(f"Starting new audit run with Assistant ID: {assistant.id}")
    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Please run the daily report audit and provide the final status table."
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while run.status in ["queued", "in_progress"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    if run.status == "requires_action":
        print("Run requires action. Assistant is calling the Gmail tool...")
        tool_outputs = []
        
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.function.name == "search_my_inbox_for_reports":
                
                response = search_my_inbox_for_reports()
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": response,
                })

        if tool_outputs:
            print("Submitting tool outputs back to the Assistant...")
            run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )

    # Wait for completion *after* submitting tools
    while run.status in ["queued", "in_progress"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status (post-tool): {run.status}")


    # --- Final Report ---
    if run.status == "completed":
        print("--- [Run Completed] ---")
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        report = messages.data[0].content[0].text.value
        print("\n## 📊 Daily Report Audit (Final Output)\n")
        print(report)
    else:
        print(f"Run failed with status: {run.status}")
        if run.last_error:
            print(f"Error: {run.last_error.message}")

    # Clean up the assistant
    try:
        client.beta.assistants.delete(assistant.id)
        print("Audit complete. Assistant deleted.")
    except Exception as e:
        print(f"Error deleting assistant: {e}")


if __name__ == "__main__":
    main()