import json
import time
import datetime
import pytz
from openai import OpenAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- 1. Configuration (Set your details here) ---

# -- Google Config --
# The path to the secret JSON key file you downloaded
SERVICE_ACCOUNT_FILE = 'dulcet-nucleus-455309-e4-2fa6bee7ce63.json' 
# The team members your agent has permission to check
USERS_TO_AUDIT = [
    'vijay.shankar@ateamsoftsolutions.com', 
    'sarath.krishnan@ateamsoftsolutions.com', 
    'nanda.krishnan@ateamsoftsolutions.com', 
    'vineeth@ateamsoftsolutions.com',
    'saran.raj@ateamsoftsolutions.com',
    'nevin.m@ateamsoftsolutions.com',
    'aneesh@ateamsoftsolutions.com'
]
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# -- OpenAI Config --
client = OpenAI(
    api_key='XXXXXXXXXXXXXXXX'
)


# --- 2. The REAL Tool Definition (The "Login" Logic) ---

def search_all_required_inboxes():
    """
    Searches the inboxes of all required users (Alice, Bob, Charlie) 
    for 'Daily Task Report' and returns a JSON list of found emails.
    """
    print("--- [Real Tool Called: search_all_required_inboxes] ---")
    
    all_found_emails = []
    
    # 1. Load the agent's base credentials from the secret file
    try:
        base_creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    except FileNotFoundError:
        print(f"ERROR: Service account key not found at {SERVICE_ACCOUNT_FILE}")
        return json.dumps([{"error": "Service account key file not found."}])
    except Exception as e:
        print(f"ERROR: Could not load service account credentials: {e}")
        return json.dumps([{"error": f"Error loading credentials: {e}"}])

    # 2. Loop through each user to "log in" and check their inbox
    for user_email in USERS_TO_AUDIT:
        try:
            print(f"Attempting to 'log in' as {user_email}...")
            
            # This is the "agent login": Impersonate the user
            delegated_creds = base_creds.with_subject(user_email)
            
            # Build the Gmail "tool" using these temporary credentials
            service = build('gmail', 'v1', credentials=delegated_creds)

            # Search for messages sent *from* this user today
            # (Note: 'today' is tricky with timezones. A robust query would use 'after:...' and 'before:...')
            results = service.users().messages().list(
                userId='me',  # 'me' refers to the impersonated user (user_email)
                q='subject:"Daily Task Report" from:me'
            ).execute()
            
            messages = results.get('messages', [])

            if not messages:
                print(f"No reports found for {user_email}.")
                continue

            # 3. Get the *real* timestamp for each found message
            for msg_stub in messages[:3]: # Check last 3 reports max
                msg = service.users().messages().get(
                    userId='me', id=msg_stub['id'], format='metadata',
                    metadataHeaders=['Subject', 'Date']
                ).execute()
                
                subject = next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Subject')
                date_str = next(h['value'] for h in msg['payload']['headers'] if h['name'] == 'Date')

                # 'internalDate' is a reliable UNIX timestamp in milliseconds
                timestamp_unix = int(msg['internalDate']) // 1000 
                
                all_found_emails.append({
                    "sender": user_email,
                    "subject": subject,
                    "timestamp_unix": timestamp_unix,
                    "timestamp_human": date_str
                })
                print(f"Found report from {user_email}: '{subject}'")

        except HttpError as e:
            print(f"ERROR accessing {user_email}'s inbox: {e}")
            # This *will* fail if Domain-Wide Delegation is not set up correctly
            all_found_emails.append({
                "sender": user_email,
                "error": f"Failed to access inbox. Check permissions: {e.details}"
            })
        except Exception as e:
             print(f"An unexpected error occurred for {user_email}: {e}")

    return json.dumps(all_found_emails)


# --- 3. The Assistant's Definition (The "Instructions") ---

# Calculate the 5:00 PM EST deadline as a UNIX timestamp
try:
    tz = pytz.timezone("EST")
    today = datetime.datetime.now(tz).date()
    deadline_dt = tz.localize(datetime.datetime.combine(today, datetime.time(17, 0, 0)))
    DEADLINE_UNIX = int(deadline_dt.timestamp())
    print(f"Today's 5:00 PM EST deadline is UNIX timestamp: {DEADLINE_UNIX}")
except Exception as e:
    print(f"Warning: Could not set EST timezone. Using simple timestamp. {e}")
    DEADLINE_UNIX = int(datetime.datetime.now().replace(hour=17, minute=0, second=0, microsecond=0).timestamp())


AUDITOR_INSTRUCTIONS = f"""
Role: You are the Daily Report Auditor.
Deadline: The deadline for all reports was 5:00 PM EST today.
Today's Deadline Timestamp (UNIX): {DEADLINE_UNIX}

Team to Check:
- Alice (alice@yourcompany.com)
- Bob (bob@yourcompany.com)
- Charlie (charlie@yourcompany.com)

Action & Output:
1.  Call the `search_all_required_inboxes` tool. This tool will check the inboxes of all three required members and return a JSON list of matching emails.
2.  Analyze the JSON list from the tool.
3.  For each team member (Alice, Bob, Charlie), determine their status:
    - **On Time:** A valid report was found AND its `timestamp_unix` is less than or equal to {DEADLINE_UNIX}.
    - **Late:** A valid report was found BUT its `timestamp_unix` is greater than {DEADLINE_UNIX}.
    - **Missing:** The user is not in the list, OR the tool reported an 'error' for them, OR no valid email with "Daily Task Report" in the subject was found.
4.  Generate the final report table.
5.  Present *only* the final table as your response.
"""

# Tool schema for the assistant
email_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_all_required_inboxes",
        "description": "Searches the Gmail inboxes of all required team members (Alice, Bob, Charlie) for emails they sent with the subject 'Daily Task Report'.",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}


# --- 4. The Agent Execution (The "Run") ---

def main():
    print("Creating Daily Report Auditor agent...")
    assistant = client.beta.assistants.create(
        name="Daily Report Auditor",
        instructions=AUDITOR_INSTRUCTIONS,
        model="gpt-4-turbo",
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

    # --- This is the agent loop ---
    while run.status in ["queued", "in_progress"]:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        print(f"Run status: {run.status}")

    # Check if the Assistant needs to use our "login" tool
    if run.status == "requires_action":
        print("Run requires action. Assistant is calling the Gmail tool...")
        tool_outputs = []
        
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.function.name == "search_all_required_inboxes":
                
                # Call our real Python function
                response = search_all_required_inboxes()
                
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": response,
                })

        # Submit the tool's findings back to the Assistant
        if tool_outputs:
            print("Submitting tool outputs back to the Assistant...")
            run = client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )
            
            # Wait for the Assistant to analyze the data
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
        print(run.last_error)

    # Clean up the assistant
    client.beta.assistants.delete(assistant.id)
    print("Audit complete. Assistant deleted.")


if __name__ == "__main__":
    main()