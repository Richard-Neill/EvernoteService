from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.notestore.ttypes import NoteFilter
from evernote.edam.type.ttypes import NoteSortOrder
from datetime import datetime

# This whole file needs to be restructured but it is currently working so I will continue with it and refactor later

class Event():
    def __init__(self, title, date, startTime, endTime, notes):
        self.title = title
        self.date = date
        self.startTime = startTime
        self.endTime = endTime
        self.notes = notes


class EvernoteConnector(EvernoteClient):
    def __init__(self, token, sandbox):
        super(EvernoteConnector, self).__init__(token=token, sandbox=sandbox)
        self.last_check_time = self.get_last_check_time()
        self.note_store = self.get_note_store()
        self.auth_token = token

    def get_new_events(self):

        noteFilter = self.get_new_event_note_filter()
        spec = NoteStore.NotesMetadataResultSpec()

        newEventNoteList = self.note_store.findNotesMetadata(self.auth_token, noteFilter, 0, 5, spec)

        events = []
        for noteMetadata in newEventNoteList.notes:
            fullNote = self.note_store.getNote(self.auth_token, noteMetadata.guid, True, False, False, False)

            events.append(self.convert_note_to_event(fullNote))

        return events

    def convert_note_to_event(self, event_note):
        # we expect the title to be of the form "2000-10-01 1600-1700 Title Name..."
        # clearly need error handling here as it may not be in that format at all

        split_title = event_note.title.split(" ", 2)

        date_timestamp = datetime.strptime(split_title[0], '%Y-%m-%d')
        start_string = split_title[1].split("-")[0]
        end_string = split_title[1].split("-")[1]

        start_timestamp = datetime.strptime(split_title[0] + " " + start_string, '%Y-%m-%d %H%M')
        end_timestamp = datetime.strptime(split_title[0] + " " + end_string, '%Y-%m-%d %H%M')

        return Event(event_note.title, date_timestamp, start_timestamp, end_timestamp, event_note.content)

    def get_new_event_note_filter(self):

        self.save_check_time(datetime.now().strftime('%Y%m%dT%H%M%S'))

        for n in self.note_store.listNotebooks():
            if n.name == 'Events':
                eventNotebookGuid = n.guid
                break

        noteFilter = NoteFilter()
        noteFilter.order = NoteSortOrder.CREATED
        noteFilter.ascending = True
        noteFilter.notebookGuid = eventNotebookGuid
        #noteFilter.words = "created:" + self.last_check_time

        return noteFilter

    def get_last_check_time(self):
        # what happens if file does not exist?
        # or file is empty
        # or time is invalid?

        with open('last_check_time.txt', 'r') as f:
            last_check_time = f.readline()
        return last_check_time

    def save_check_time(self, savedTime):
        with open('last_check_time.txt', 'w') as f:
            f.write(str(savedTime))
