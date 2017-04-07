#!/usr/bin/python

import sys
import subprocess
import datetime

######################################################################################
#Shell Command related configuration and process
class cShellCommand:
    def __init__(self,cmd,msg="",debug=False):
        self.cmd = cmd
        self.msg = msg
        self.log = None
        self.debug = debug

    def logOutput(self,out):
        if self.log == None:
            self.log = out
        else:
            self.log+=str(out)

    def exe(self):
        self.log = None
        if len(self.msg):
            print self.msg + ' ... ',
        sys.stdout.flush()
        self.logOutput(str(datetime.datetime.now()) + '\n')
        self.logOutput(self.cmd + '\n')
        process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            self.logOutput(err + '\n')
            if len(self.msg):
                print 'Failed'
            if self.debug and self.log is not None:
                print 'DEBUG OUTPUT'
                print self.log
            return False
        else:
            self.logOutput(out + '\n')
            if len(self.msg):
                print 'Done'
            if self.debug and self.log is not None:
                print 'DEBUG OUTPUT'
                print self.log
        return True

    def exeGet(self):
        self.log = None
        if len(self.msg):
            print self.msg + ' ... ',
        sys.stdout.flush()
        self.logOutput(str(datetime.datetime.now()) + '\n')
        self.logOutput(self.cmd + '\n')
        process = subprocess.Popen(self.cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode != 0:
            self.logOutput(err + '\n')
            if len(self.msg):
                print 'Failed'
            if self.debug and self.log is not None:
                print 'DEBUG OUTPUT'
                print self.log
            return None
        else:
            self.logOutput(out + '\n')
            if len(self.msg):
                print 'Done'
            if self.debug and self.log is not None:
                print 'DEBUG OUTPUT'
                print self.log
            return out.strip()
