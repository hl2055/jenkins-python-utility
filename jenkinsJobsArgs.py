#!/usr/bin/python
import argparse
import json
import collections

class cJobArgs:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Jenkis Job Actions')
        parser.add_argument('-c','--credentials',nargs=1,type=str,help='Credential JSON file')
        actionList = ['delete','reload','show','build','last_successful_build','last_build_status','monitor']
        parser.add_argument('-a','--action',nargs=1,required=True,type=str,choices=actionList,help='Action')
        parser.add_argument('-s','--server',nargs=1,type=str,help='Jenkins Server URL')
        parser.add_argument('-u','--user',nargs=1,type=str,help='Jenkins Server User')
        parser.add_argument('-p','--password',nargs=1,type=str,help='Jenkins Server Password')
        args = parser.parse_args()

        self.credentials = None
        self.credJson = None

        self.action = args.action[0]
        if args.credentials is not None:
            self.credentials = args.credentials[0]
            credJsonString = open(self.credentials).read()
            self.credJson = json.loads(credJsonString,object_pairs_hook=collections.OrderedDict)
        self.server = 'http://172.36.21.41:8080/'
        if args.server is not None:
            self.server = args.server[0]
        self.user = ''
        if args.user is not None:
            self.user = args.user[0]
        self.password = ''
        if args.password is not None:
            self.password = args.password[0]

    def show(self):
        if len(self.credentials):
            print 'Credential File: ' + self.credentials
            print self.credJson
        if len(self.action):
            print 'Action: ' + self.action

#jobArgs = cJobArgs()
#jobArgs.show()
