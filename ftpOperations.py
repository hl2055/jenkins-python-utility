#!/usr/bin/python

import sys
import subprocess
import datetime
import ftplib
import os

import argparse

######################################################################################
#FTP related process
class cFtpConnection:
    def __init__(self,server,user,password,debug=False):
        self.server = server
        self.user = user
        self.password = password
        self.debug = debug
        self.connection = None
        #Validate information
        if server == None or len(server) == 0:
            print 'FTP_SERVER not defined'
            return None
        if user == None or len(user) == 0:
            print 'FTP_USER not defined'
            return None
        if password == None or len(password) == 0:
            print 'FTP_PASSWORD not defined'
            return None
        #Connect to FTP
        try:
            self.connection = ftplib.FTP(self.server)
            self.connection.login(self.user,self.password)
        except ftplib.all_errors, e: 
            if self.debug:
                print '\nFTP communication failed with server ' + self.server + ' with error:'
                print str(e)
            self.connection = None

    def isActive(self):
        if self.connection is not None:
            return True
        else:
            return False

    def close(self):
        if self.isActive():
            self.connection.quit()

    def download(self,filename,remotePath,localPath):
        status = True
        remoteFilename = remotePath + '/' + filename
        localFilename = localPath + '/' + filename
        if not self.isActive():
            print 'ERROR: FTP connection invalid'
            status = False
            return status
        #Check localPath if exists, otherwise create
        if not os.path.exists(localPath):
            os.makedirs(localPath)
        print 'Downloading file ' + filename + ' from ' + remoteFilename + ' to ' + localFilename + ' ... ',
        sys.stdout.flush()
        try:
            self.connection.cwd(remotePath)
            localFileHandle = open(localFilename, 'wb')
            self.connection.retrbinary('RETR '+filename,localFileHandle.write)
            print 'Done'
            sys.stdout.flush()
            localFileHandle.close()
        except ftplib.all_errors, e: 
            if self.debug:
                print '\nFTP communication failed with server ' + self.server + ' with error:'
                print str(e)
            status = False
        return status

    def upload(self,filename,remotePath,localPath):
        status = True
        remoteFilename = remotePath + '/' + filename
        localFilename = localPath + '/' + filename
        if not self.isActive():
            print 'ERROR: FTP connection invalid'
            status = False
            return status
        #Check remotePath if exists, otherwise create
        if not self.createDirectory(remotePath):
            print 'Failed to have path [%s]' % remotePath
            status = False
            return status
        print 'Uploading file ' + filename + ' from ' + localFilename + ' to ' + remoteFilename + ' ... ',
        sys.stdout.flush()
        try:
            self.connection.cwd(remotePath)
            localFileHandle = open(localFilename, 'rb')
            self.connection.storbinary('STOR '+filename,localFileHandle)
            print 'Done'
            sys.stdout.flush()
            localFileHandle.close()
        except ftplib.error_perm, e: 
                print str(e)
        except ftplib.all_errors, e: 
            if self.debug:
                print '\nFTP communication failed with server ' + self.server + ' with error:'
                print str(e)
            status = False
        return status

    def createDirectory(self,remotePath):
        status = True
        created = False
        if not self.isActive():
            print 'ERROR: FTP connection invalid'
            status = False
            return status
        try:
            #Split remotePath to directories
            dirList = remotePath.split('/')
            dirList.pop(0)
            filelist = []
            self.connection.retrlines('NLST',filelist.append)
            for aDir in dirList:
                if len(aDir) == 0:
                    continue
                if aDir not in filelist:
                    print 'Directory [%s] does not exist' % aDir
                    self.connection.mkd(aDir)
                    print 'Directory [%s] created' % aDir
                    created = True
                self.connection.cwd(aDir)
                filelist = []
                self.connection.retrlines('NLST',filelist.append)
            if not created:
                print 'Directory [%s] already exists' % remotePath
        except ftplib.error_perm, e: 
                print str(e)
        except ftplib.all_errors, e: 
            if self.debug:
                print '\nFTP communication failed with server ' + self.server + ' with error:'
                print str(e)
            status = False
        return status

    def removeRecursiveDirectory(self,directory,ftpCon):
        status = True
        print 'Process deletion of [%s]' % directory
        try:
            ftpCon.cwd(directory)
            print ftpCon.nlst()
        except:
            print 'Unable to access [%s]' % directory
            status = False
            return status
        for aDir in ftpCon.nlst():
            print 'Item [%s]' % aDir
            try:
                #treat it as a file
                print 'Attempt deleting file [%s]' % aDir
                ftpCon.delete(aDir)
            except:
                #its a directory
                status = self.removeRecursiveDirectory(aDir,ftpCon)
                if not status:
                    break
        print ftpCon.pwd()
        print ftpCon.nlst()
        if status:
            try:
                print 'Attempt deleting parent directory [%s]' % directory
                ftpCon.cwd('..')
                print ftpCon.pwd()
                ftpCon.rmd(directory)
            except:
                status = False
        return status

    def removeDirectory(self,remotePath,build=True):
        status = True
        deleted = False

        if not self.isActive():
            print 'ERROR: FTP connection invalid'
            status = False
            return status

        if remotePath == None or remotePath == '/' or len(remotePath) == 0:
            status = False

        if status:
            try:
                #Split remotePath to directories
                dirList = remotePath.split('/')
                dirList.pop(0)
                itemlist = []
                self.connection.retrlines('NLST',itemlist.append)
                for index,aDir in enumerate(dirList):
                    print str(index) + ' ' + aDir
                    if len(aDir) == 0:
                        continue
                    #The leaf folder to be deleted
                    if index+1 == len(dirList) and aDir in itemlist:
                        print 'Directory [%s] does exist' % aDir
                        if build and not aDir.isdigit():
                            print 'Directory [%s] is not a build directory' % aDir
                            status = False
                            break
                        #Delete all files and folders within this directory first
                        deleted = self.removeRecursiveDirectory(aDir,self.connection)
                        if deleted:
                            print 'Directory [%s] deleted' % aDir
                        else:
                            status = False
                            print 'Directory [%s] deletion failed' % aDir
                        break
                    if aDir not in itemlist:
                        print 'Directory [%s] does not exist' % aDir
                        status = False
                        break
                    self.connection.cwd(aDir)
                    itemlist = []
                    self.connection.retrlines('NLST',itemlist.append)
            except ftplib.error_perm, e: 
                    print str(e)
            except ftplib.all_errors, e: 
                if self.debug:
                    print '\nFTP communication failed with server ' + self.server + ' with error:'
                    print str(e)
                status = False
        return status

    def removeBuilds(self,remotePath,maxBuilds,lastBuild):
        status = True
        #Make sure the path is not destructive
        if remotePath == None or remotePath == '/' or len(remotePath) == 0:
            print 'Invalid remote path'
            status = False

        #Make sure the path is not destructive
        if maxBuilds == None or maxBuilds <= 0 or lastBuild == None or lastBuild <= 0:
            print 'Invalid build parameter'
            status = False

        if status:
            #Get list of folders
            status, foldersList = self.listDirectory(remotePath)
            if foldersList == None:
                status = False

        #Verify last build exists
        if status:
            print foldersList
            if str(lastBuild) not in foldersList:
                status = False

        #Verify all builds to keep exists
        if status:
            firstKeepBuild=lastBuild-maxBuilds+1
            if firstKeepBuild <= 0:
                firstKeepBuild=1
            buildsToKeep = [str(x) for x in range(firstKeepBuild,lastBuild+1)]
            print buildsToKeep
            if len(buildsToKeep) > len(foldersList):
                buildsToKeep = foldersList
            
            for aBuild in buildsToKeep:
                if aBuild not in foldersList:
                    print 'Build [%s] do not exist' % aBuild
                    status = False
                    break

        #Remove all other builds than builds to keep
        if status:
            for aPath in foldersList:
                if aPath in buildsToKeep:
                    continue
                self.connection.cwd(remotePath)
                status = self.removeDirectory('/' + aPath,build=True)
                if not status:
                    break
        #Delete them
        return status

    def listDirectory(self,remotePath,show=False):
        status = True
        if not self.isActive():
            print 'ERROR: FTP connection invalid'
            status = False
            return status
        try:
            #Split remotePath to directories
            dirList = remotePath.split('/')
            dirList.pop(0)
            filelist = []
            self.connection.retrlines('NLST',filelist.append)
            for aDir in dirList:
                if len(aDir) == 0:
                    #Show current level
                    continue
                if aDir in filelist:
                    self.connection.cwd(aDir)
                else:
                    print 'Directory [%s] does not exist' % aDir
                    status = False
                    break
                filelist = []
                self.connection.retrlines('NLST',filelist.append)
            if status and show:
                print filelist
        except ftplib.all_errors, e: 
            if self.debug:
                print '\nFTP communication failed with server ' + self.server + ' with error:'
                print str(e)
            status = False
        if status:
            return status, filelist
        else:
            return status, None

    def action(self,action,filename=None,localPath=None,remotePath=None,maxBuilds=None,lastBuild=None):
        if action == 'upload':
            if filename == None or localPath == None or remotePath == None:
                print 'Invalid parameters'
                return False
            return self.upload(filename,remotePath,localPath)
        elif action == 'download':
            if filename == None or localPath == None or remotePath == None:
                print 'Invalid parameters'
                return False
            return self.download(filename,remotePath,localPath)
        elif action == 'check':
            if self.isActive():
                print 'Connected'
            return self.isActive()
        elif action == 'list':
            if remotePath == None:
                print 'Invalid parameters'
                return False
            status, filelist = self.listDirectory(remotePath,show=True)
            return status
        elif action == 'create':
            self.debug = True
            if remotePath == None:
                print 'Invalid parameters'
                return False
            return self.createDirectory(remotePath)
        elif action == 'remove':
            self.debug = True
            if remotePath == None:
                print 'Invalid parameters'
                return False
            return self.removeDirectory(remotePath,build=False)
        elif action == 'remove-builds':
            self.debug = True
            if remotePath == None or maxBuilds == None or lastBuild == None:
                print 'Invalid parameters'
                return False
            return self.removeBuilds(remotePath,maxBuilds,lastBuild)
        else:
            print 'Invalid Action [%s]' % (action)
            return False
        return True

class cFtpArgs:
    def __init__(self):
        parser = argparse.ArgumentParser(description='FTP Operations')
        parser.add_argument('-s','--server',nargs=1,required=True,type=str,help='FTP Server')
        parser.add_argument('-u','--user',nargs=1,required=True,type=str,help='FTP User')
        parser.add_argument('-p','--password',nargs=1,required=True,type=str,help='FTP Password')
        actionList = ['check','list','create','remove','upload','download','remove-builds']
        parser.add_argument('-a','--action',nargs=1,required=True,type=str,choices=actionList,help='Action')
        parser.add_argument('-f','--filename',nargs=1,type=str,help='File for upload/download')
        parser.add_argument('-l','--localpath',nargs=1,type=str,help='Local path for upload/download')
        parser.add_argument('-r','--remotepath',nargs=1,type=str,help='Remote path for upload/download')
        parser.add_argument('-m','--maxbuilds',nargs=1,type=int,help='Max number of builds to keep')
        parser.add_argument('-b','--lastbuild',nargs=1,type=int,help='Last successful build')
        args = parser.parse_args()

        self.server = None
        self.user = None
        self.password = None
        self.action = None
        self.filename = None
        self.localpath = None
        self.remotepath = None
        self.maxBuilds = None
        self.lastBuild = None

        self.server = args.server[0]
        self.user = args.user[0]
        self.password = args.password[0]
        self.action = args.action[0]
        if args.filename is not None:
            self.filename = args.filename[0]
        if args.localpath is not None:
            self.localpath = args.localpath[0]
        if args.remotepath is not None:
            self.remotepath = args.remotepath[0]
        if args.maxbuilds is not None:
            self.maxBuilds = args.maxbuilds[0]
        if args.lastbuild is not None:
            self.lastBuild = args.lastbuild[0]

