Step-by-step: Service Account setup (no OAuth consent needed)

1. Create the Service Account credential

In the Google Cloud Console, with your project selected:

1. Go to APIs & Services → Credentials
2. Click + Create Credentials (top of page)
3. Choose Service account — NOT "OAuth client ID" (that's what triggers the consent screen prompt)
4. Fill in:
  - Service account name: ib-nutricao-calendar (or anything)
  - Service account ID: auto-fills, leave it
  - Description: optional
5. Click Create and continue
6. On "Grant this service account access to project" — skip this, click Continue
7. On "Grant users access to this service account" — skip this too, click Done

You'll land back on the Credentials page and see your new service account listed.

---
2. Download the JSON key

1. Click the service account email you just created (e.g. ib-nutricao-calendar@your-project.iam.gserviceaccount.com)
2. Go to the Keys tab
3. Click Add Key → Create new key
4. Select JSON → click Create
5. A file downloads automatically — this is your credentials.json
6. Move it to D:\Other\ineswebsite\backend\credentials.json

▎ The .gitignore already excludes this file so it won't be committed accidentally.

---
3. Share the nutritionist's Google Calendar with the service account

This is the key step that grants the backend access to her calendar:

1. Open Google Calendar (calendar.google.com) logged in as the nutritionist (or whoever manages her calendar)
2. On the left sidebar, find her calendar → hover → click the three dots → Settings and sharing
3. Scroll to "Share with specific people or groups"
4. Click + Add people
5. Paste the service account email — it looks like:
ib-nutricao-calendar@your-project-id.iam.gserviceaccount.com
5. You can find this exact email on the Credentials page or inside the downloaded JSON under "client_email"
6. Set permissions to "Make changes to events"
7. Click Send

---
4. Get the Calendar ID

While still in Calendar Settings for her calendar:

1. Scroll down to "Integrate calendar"
2. Copy the Calendar ID — it looks like one of:
  - Her Gmail address: ines@gmail.com (if it's the primary calendar)
  - A long string: abc123xyz@group.calendar.google.com (if it's a secondary calendar)

---
5. Configure backend/.env

GOOGLE_CALENDAR_ID=paste_calendar_id_here
GOOGLE_CREDENTIALS_FILE=/app/credentials.json

For local dev (outside Docker), set the path to the actual file:
GOOGLE_CREDENTIALS_FILE=D:/Other/ineswebsite/backend/credentials.json