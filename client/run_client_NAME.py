########################################
# Music Signaling Pipeline Prototype
#   Example GMail: sample connection
#       between client and GMail API
#
# Author: Ishwarya Ananthabhotla
#########################################

# Check every N minutes for new email. If present, send a signal(1) to server

# template for all individual customizations

# Other filters
# M.search(None, '(SINCE "01-Jan-2012")')
# M.search(None, '(BEFORE "01-Jan-2012")')
# M.search(None, '(SINCE "01-Jan-2012" BEFORE "02-Jan-2012")')

import time
import client
from datetime import datetime, timedelta
import threading
import pytz
import imaplib
import oauth2 as o
import pickle
import argparse

class Client_Email:
    def __init__(self, email_id, log=True):
        # self.session = imaplib.IMAP4_SSL('imap.gmail.com', '993')
        self.finished_flag = threading.Event()
        self.t1 = None
        self.token_expire_time = None
        self.email_id = email_id
        self.client_session = None
        self.log_file = open('soundsignal_log.txt', 'ab')
        self.log_file.write('START ' + str(datetime.now()) + '\n')

    def start_server_connection(self):
        self.client_session = client.Client()

    def start_gmail_connection(self, refresh=False):
        if refresh:
            self.session.logout()

        # make new connection
        self.session = imaplib.IMAP4_SSL('imap.gmail.com')

        # load refresh token and use to generate new access token
        refresh_token, client_id, client_secret = pickle.load(open('client_auth.pkl', 'rb'))
        response = o.RefreshToken(client_id, client_secret, refresh_token)
        access_token = response['access_token']
        self.token_expire_time = datetime.now() + timedelta(0,response['expires_in'])

        # use access token to generate new auth string
        auth_string = 'user=%s\1auth=Bearer %s\1\1' % (self.email_id, access_token)

        self.session.debug = 1
        self.session.authenticate('XOAUTH2', lambda x: auth_string) 
        self.session.select('inbox')       

    # check for new messages once every 5 minutes, and signal if present
    def check_and_signal(self, finished_flag, wait_mins):
        today = datetime.now(pytz.utc)
        datestr = str(today.day) + '-' + today.strftime('%b') + '-' + str(today.year)
        
        # load the day's email into list
        response, old_email_fetch = self.session.search(None, '(SINCE "' + datestr + '")')

        while not self.finished_flag.isSet():
            # check access token expiry
            if datetime.now() > self.token_expire_time - timedelta(minutes=10):
                print "Refreshing Access.."
                print self.token_expire_time - timedelta(minutes=10)
                self.start_gmail_connection(refresh=True)

            print "Checking now at: ", datetime.now()
            self.session.select("inbox")
            # store the email ids from each query and compare against the next
            response, new_email_fetch = self.session.search(None, '(SINCE "' + datestr + '")')

            # check for a new email
            if len(new_email_fetch[0].split()) - len(old_email_fetch[0].split()) > 0:
                # signal
                if self.client_session != None:
                    try:
                        self.client_session.signal(0)
                    except:
                        print "Can't send signal, retrying.."
                        try:
                            time.sleep(1)
                            self.client_session.signal(0)
                        except:
                            print "Can't send signal, quitting.."
                            return
                    print "Found new mail!"
                    self.log_file.write('NOTIF ' + str(datetime.now()) + '\n')
                else:
                    print "No connection to server."

                old_email_fetch = new_email_fetch

            # sleep
            time.sleep(wait_mins * 60)

    def start_monitoring(self, wait_mins=1):
        self.t1 = threading.Thread(target=self.check_and_signal, args=(self.finished_flag, wait_mins, ))
        self.t1.daemon = True
        self.t1.start()

    def end_monitoring(self):
        self.finished_flag.set()
        self.t1.kill = True
        # self.t1.join()

    def end_gmail(self):
        self.session.logout()
        self.client_session.end_server()
        self.client_session.end_client()
        self.log_file.write('STOP ' + str(datetime.now()) + '\n')
        self.log_file.close()


if __name__ == "__main__":
    # sample parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-id', action="store", dest="id", type=str)
    parser.add_argument('-start', action='store_true')
    parser.add_argument('-mins', action="store", dest="mins", type=int)
    parser.add_argument('-check_freq', action="store", dest="check", type=int, default=1)
    args = parser.parse_args()

    if args.id != None and args.start != None:
        if args.mins > 0:
            # start all connections by default
            e = Client_Email(args.id)    
            e.start_server_connection()
            e.start_gmail_connection()

            e.start_monitoring(wait_mins=args.check)
            i = 0
            while i < args.mins:
                try:
                    time.sleep(i * 60)
                    i += 1
                except KeyboardInterrupt:
                    break

            print "Monitored for " + str(args.mins) + " mins. Finished."
            e.end_monitoring()
            e.end_gmail()
        else:
            # start all connections by default
            e = Client_Email(args.id)    
            e.start_server_connection()
            e.start_gmail_connection()

            
            e.start_monitoring(wait_mins=args.check)
            while True:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    print "Ending monitoring, shutting down."
                    e.end_monitoring()
                    e.end_gmail()
                    break
    else:
        print "Incorrect arguments. Specify start mins, or use python command line."