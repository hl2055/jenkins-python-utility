#!/usr/bin/python

from ftpOperations import cFtpConnection
from ftpOperations import cFtpArgs

ftpArgs = cFtpArgs()
ftpConn = cFtpConnection(ftpArgs.server,ftpArgs.user,ftpArgs.password)
if not ftpConn.action(ftpArgs.action,ftpArgs.filename,ftpArgs.localpath,ftpArgs.remotepath,ftpArgs.maxBuilds,ftpArgs.lastBuild):
    exit(1)
