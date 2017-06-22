from oauth2client import tools
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from apiclient import discovery

from xml.etree import cElementTree
import argparse
import httplib2
import json
import logging

import os
from datetime import datetime

from mendeley import Mendeley, MendeleyClientCredentialsAuthenticator 
from mendeley.session import MendeleySession
from mendeley.auth import MendeleyClientCredentialsTokenRefresher,MendeleyAuthorizationCodeTokenRefresher
from mendeley.exception import MendeleyApiException

TIMEZONE_OFFSET = '+01'

class MendeleyConnector():
    def __init__(self, credentials_file):

        # initialise credentials to use for mendeley connections
        with open(credentials_file) as credentials:
            secrets = json.load(credentials)

        flow = OAuth2WebServerFlow(  
            client_id=secrets['web']['client_id'],
            client_secret=secrets['web']['client_secret'],
            scope=['all'],
            redirect_uri=secrets['web']['redirect_uris'][0],
            auth_uri=secrets['web']['auth_uri'],
            token_uri=secrets['web']['token_uri'],
            grant_type=secrets['web']['grant_type']
        )

        parser = argparse.ArgumentParser(parents=[tools.argparser])
        flags = parser.parse_args()

        storage = Storage(str(credentials_file) + ".authenticated")

        mcredentials = None
        previous_creds = False
        try:
            mcredentials = storage.get()
        except Exception as e:
            logging.debug("No authorised mendeley credentials found.")
            pass

        if mcredentials is None:
            mcredentials = tools.run_flow(flow, storage, flags)
        elif mcredentials.invalid:
            logging.debug("The authorised mendeley credentials are invalid.")
            mcredentials = tools.run_flow(flow, storage, flags)
        else:
            previous_creds = True

        if previous_creds is False:
            storage.put(mcredentials)

        # Now create the mendeley session with the access token
        self.mendeley = Mendeley(secrets['web']['client_id'], secrets['web']['client_secret'],secrets['web']['redirect_uris'][0])
        auth = MendeleyClientCredentialsAuthenticator(self.mendeley)
        
        creds = {"access_token": mcredentials.access_token, "refresh_token": mcredentials.refresh_token}

        self.session = MendeleySession(self.mendeley,
            creds,
            client=auth.client,
            refresher=MendeleyClientCredentialsTokenRefresher(auth))
        
        time_now = datetime.now()

        if time_now >= mcredentials.token_expiry:
            logging.debug("Mendeley access token has expired. Refreshing...")

            refresher = MendeleyAuthorizationCodeTokenRefresher(auth)
            refresher.refresh(self.session)

            mcredentials.access_token = self.session.token["access_token"]
            mcredentials.refresh_token = self.session.token["refresh_token"]

            expiry = datetime.fromtimestamp(self.session.token["expires_at"])
            mcredentials.token_expiry = expiry

            storage.put(mcredentials)

        logging.debug('Successfully authenticated with Mendeley and created service object')

    def test(self):
    
        logging.debug('Testing')

        docs = self.session.documents.iter()
        for doc in docs:
            print doc.title


        # doc has:
        # "authors"
        # "title"
        # "created"
        # "year"


