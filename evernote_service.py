from evernote_connector import EvernoteConnector, Event
import api_settings

# Get new events from Evernote

client = EvernoteConnector(token=api_settings.EVERNOTE_AUTH_TOKEN, sandbox=api_settings.EVERNOTE_SANDBOX_MODE)
events = client.get_new_events()

for event in events:
    print "Title is " + event.title


# Add them to Google Calender
