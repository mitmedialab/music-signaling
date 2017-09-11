########################################
# Music Signaling Pipeline Prototype
#   Example GMail setup: generating
#       authentication tokens
#
# Author: Ishwarya Ananthabhotla
#########################################

# https://github.com/google/gmail-oauth2-tools/wiki/OAuth2DotPyRunThrough

import oauth2 as o
import pickle

def setup(client_id, client_secret):
    print "Welcome to the sound signaling project.  Let's get your consent to monitor your email."
    print 'Visit this url and follow the directions:'
    print o.GeneratePermissionUrl(client_id)
    authorization_code = raw_input('Enter verification code: ')
    response = o.AuthorizeTokens(client_id, client_secret, authorization_code)
    refresh_token = response['refresh_token']
    # write the refresh token for use by client application
    pickle.dump((refresh_token, client_id, client_secret), open("client_auth.pkl", "wb"))


if __name__ == '__main__':
    client_id = "931508103316-nfts50icrd06op2hgh8laojfqveu3ttc.apps.googleusercontent.com"
    client_secret = "bcpmqwKhnMJaxYn04Q1fi-Vd"
    
    setup(client_id, client_secret)
