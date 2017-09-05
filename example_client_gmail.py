########################################
# Music Signaling Pipeline Prototype
#   Example GMail: sample connection
#       between client and GMail API
#
# Author: Ishwarya Ananthabhotla
#########################################

# Check every N minutes for new email. If present, send a signal(1) to server

# Other filters
# M.search(None, '(SINCE "01-Jan-2012")')
# M.search(None, '(BEFORE "01-Jan-2012")')
# M.search(None, '(SINCE "01-Jan-2012" BEFORE "02-Jan-2012")')

import time
import client
from datetime import datetime
import threading
import pytz
import imaplib

class Client_Email:
    def __init__(self):
        self.session = imaplib.IMAP4_SSL('imap.gmail.com', '993')
        self.user= 'soundsignaling'
        self.password= 'musictest'
        self.finished_flag = threading.Event()

    def start_server_connection(self):
        self.client_session = client.Client()

    def start_gmail_connection(self, username, password):
        self.session.login(self.user, self.password)        

    # check for new messages once every 5 minutes, and signal if present
    def check_and_signal(self, finished_flag, wait_mins=1):

        self.session.select("inbox")
        today = datetime.now(pytz.utc)
        datestr = str(today.day) + '-' + today.strftime('%b') + '-' + str(today.year)
        
        # load the day's email into list
        response, old_email_fetch = self.session.search(None, '(SINCE "' + datestr + '")')

        while not self.finished_flag.isSet():
            print "Checking now.."
            self.session.select("inbox")
            # store the email ids from each query and compare against the next
            response, new_email_fetch = self.session.search(None, '(SINCE "' + datestr + '")')

            # check for a new email
            if len(new_email_fetch[0].split()) - len(old_email_fetch[0].split()) > 0:
                # signal
                self.client_session.signal(1)
                print "Found new mail!"

                old_email_fetch = new_email_fetch

            # sleep
            time.sleep(wait_mins * 60)

    def start_monitoring(self):
        t1 = threading.Thread(target=self.check_and_signal, args=(self.finished_flag, ))
        t1.daemon = True
        t1.start()

    def end_monitoring(self):
        self.finished_flag.set()

    def end_gmail(self):
        self.session.logout()
        self.client_session.end_server()
        self.client_session.end_client()


if __name__ == "__main__":
    e = Client_Email()
    e.start_server_connection()
    e.start_gmail_connection('soundsignaling', 'musictest')
    e.start_monitoring()
    time.sleep(5 * 60)
    print "Done."
    e.end_monitoring()
    e.end_gmail()