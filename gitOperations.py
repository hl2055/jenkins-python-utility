#!/usr/bin/python

import os
import shutil
import git
import re
import subprocess

import argparse
import json
import collections

import logging

class cGitRepo:
    def __init__(self, repo, location, debug=False):
        self.repo = None
        self.debug = debug
        if self.debug:
            logFile = 'gitOperations.log'
            if os.path.exists(logFile):
                os.remove(logFile)
            logging.basicConfig(filename=logFile,level=logging.DEBUG)
        self.repoName = repo
        self.repoUrl = 'git@git:' + repo
        if '.git' in os.path.basename(repo):
            self.repoBasename = os.path.basename(repo).split('.git')[0]
        else:
            self.repoBasename = os.path.basename(repo)
        self.repoLocation = location + '/' + self.repoBasename
        #Assign existing location
        if os.path.exists(self.repoLocation):
            self.repo = git.Repo(self.repoLocation)
        else:
            self.clone()
            if not self.setBranch('master'):
                print 'Failed to set master branch'

    def clone(self):
        if not os.path.exists(self.repoLocation):
            print 'Clone Repo [%s]' % self.repoName
            self.repo = git.Repo.clone_from(self.repoUrl,self.repoLocation)

    def clean(self):
        if os.path.exists(self.repoLocation):
            print 'Cleanup Repo [%s]' % self.repoName
            shutil.rmtree(self.repoLocation)

    def fetch(self):
        if self.repo is not None:
            print 'Fetch Repo [%s]' % self.repoName
            self.repo.remotes.origin.fetch()

    def status(self):
        if self.repo is not None:
            print 'Repo [%s] Status' % self.repoName
            print self.repo.git.status()

    def showBranch(self):
        if self.repo is not None:
            print 'Current Branch on Repo [%s]' % self.repoName
            print [str(branch) for branch in self.repo.heads]

    def readBranches(self):
        self.branches = {}
        g = git.cmd.Git(self.repoLocation)
        for ref in g.ls_remote('--heads').split('\n'):
            if len(ref) == 0:
                continue
            hashes = ref.split('\t')
            branch = hashes[1].split('refs/heads/')[1]
            self.branches[branch] = hashes[0]

    def showBranches(self):
        print 'Branches on Repo [%s]' % self.repoName
        self.readBranches()
        for branch in self.branches:
            print 'Branch [%s] is at Hash [%s]' % (branch,self.branches[branch])

    def readTags(self):
        self.tags = {}
        g = git.cmd.Git(self.repoLocation)
        for ref in g.ls_remote('--tags').split('\n'):
            if len(ref) == 0:
                continue
            hashes = ref.split('\t')
            tag = hashes[1].split('refs/tags/')[1]
            self.tags[tag] = hashes[0]

    def showTags(self):
        print 'Tags on Repo [%s]' % self.repoName
        self.readTags()
        for tag in self.tags:
            print 'Tag [%s] is at Hash [%s]' % (tag,self.tags[tag])

    def setBranch(self,branch):
        if self.repo == None:
            return False
        self.readBranches()
        if branch in self.branches:
            self.repo.git.checkout(branch)
            return True
        else:
            print 'Branch [%s] does not exist' % branch
            return False

    def diffRefs(self,ref1,ref2,nameOnly=False,log=False):
        differ = ''
        if self.debug:
            print 'Diff References [%s] and [%s] on Repo [%s]' % (ref1,ref2,self.repoName)
        g = git.Git(self.repoLocation)
        options = []
        if log:
            options.extend(['--no-merges'])
        if nameOnly:
            options.extend(['--name-only'])
        options.extend(['remotes/origin/%s..remotes/origin/%s' % (ref1, ref2)])
        differ = g.diff(options)
        return differ

    #Jenkins Format: "YYYY-MM-DD_HH-MM-SS"
    #Git Format: "YYYY-MM-DD HH:MM:SS"
    #Before for latest
    #After for oldest
    def commitsByTime(self,afterTime,beforeTime,path='',exclude=''):
        differ = ''
        g = git.Git(self.repoLocation)
        #Handle Jenkins Format
        if "_" in afterTime and "_" in beforeTime:
            latestTime = beforeTime.split("_")[0] + ' ' + (beforeTime.split("_")[1]).replace("-",":")
            oldestTime = afterTime.split("_")[0] + ' ' + (afterTime.split("_")[1]).replace("-",":")
        else:
            latestTime = beforeTime
            oldestTime = afterTime
        options = []
        options.extend(['--before="%s"' % (latestTime)])
        options.extend(['--after="%s"' % (oldestTime)])
        options.extend(['--pretty=oneline'])
        options.extend(['--no-merges'])
        logMsg = 'Log From [%s] To [%s] on Repo [%s]' % (latestTime,oldestTime,self.repoName)
        if len(path) != 0:
            logMsg += ' in folder [%s]' % (path)
            options.extend(['--'])
            options.extend([path])
        if len(exclude) != 0:
            logMsg += ' excluding [%s]' % (exclude)
            options.extend(['":(exclude)%s"' % (exclude)])
        if self.debug:
            print logMsg
        if len(exclude) != 0:
            logCmdString='git log'
            for opt in options:
                logCmdString += ' ' + opt
            if self.debug:
                print logCmdString
            p = subprocess.Popen(logCmdString,cwd=self.repoLocation,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
            out,err = p.communicate()
            if len(err) != 0:
                if self.debug:
                    print err
                return None
            else:
                commits = out.split('\n')
        else:
            commits = g.log(options).split('\n')
        if self.debug:
            print commits
        for commit in commits:
            if len(commit.strip()) == 0:
                commits.remove(commit)
        if len(commits) == 0:
            differ = ''
        else:
            differ = 'Commit List -- Git Repo %s\n\n' % self.repoName
        for commit in commits:
            commitHash = commit.split()[0]
            commitLog = '----------------------------------------\n\n'
            commitLog += 'http://git.bluecatnetworks.corp/?p=' + self.repoName + ';a=commit;h=' + commitHash + '\n'
            cOptions = ['-1','-U',commitHash,'--name-only']
            commitLog += g.log(cOptions)
            commitLog += '\n\n'
            differ += commitLog
        if len(differ) > 0:
            differ += '----------------------------------------\n\n'
        return differ

    def commitsByTag(self,startTag, endtag, path='',exclude=''):
        if self.repo == None:
            return False
            
        differ = ''
        logMsg = ''
        startTagCommit = ''

        g = git.Git(self.repoLocation)
        self.readTags()
        temptags = []
        if startTag not in self.tags and startTag not in self.repo.tags:
            print "Tag [%s] does not exist" % (startTag)
            return False
        if endtag is not None and endtag not in self.tags and endtag not in self.repo.tags:
            for tag in self.tags:
                if tag.startswith(endtag + '_') and tag[len(endtag)+1:].isdigit():

                    temptags.append(tag)

            if temptags == []:
                print "Tag [%s] does not exist" % (endtag)
                return False
            else:
                temptags.sort()
                endtag = temptags[-1]

        if endtag is None and temptag is None:
            endtag = self.repo.head


        options = []
        options.extend(['--pretty=oneline'])
        options.extend(['--no-merges'])
        options.extend(["%s...%s" %(startTag,endtag)])

        if len(path) != 0:
            logMsg += ' in folder [%s]' % (path)
            options.extend(['--'])
            options.extend([path])
        if len(exclude) != 0:
            logMsg += ' excluding [%s]' % (exclude)
            options.extend(['":(exclude)%s"' % (exclude)])
        if self.debug:
            print logMsg
        if len(exclude) != 0:
            logCmdString='git log'
            for opt in options:
                logCmdString += ' ' + opt
            if self.debug:
                print logCmdString
            p = subprocess.Popen(logCmdString,cwd=self.repoLocation,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=True)
            out,err = p.communicate()
            if len(err) != 0:
                if self.debug:
                    print err
                return None
            else:
                commits = out.split('\n')
        else:
            commits = g.log(options).split('\n')
        if self.debug:
            print commits
        for commit in commits:
            if len(commit.strip()) == 0:
                commits.remove(commit)
        if len(commits) == 0:
            differ = ''
        else:
            differ = 'Commit List -- Git Repo %s\n\n' % self.repoName
        for commit in commits:
            commitHash = commit.split()[0]
            commitLog = '----------------------------------------\n\n'
            commitLog += 'http://git.bluecatnetworks.corp/?p=' + self.repoName + ';a=commit;h=' + commitHash + '\n'
            cOptions = ['-1','-U',commitHash,'--name-only']
            commitLog += g.log(cOptions)
            commitLog += '\n\n'
            differ += commitLog
        if len(differ) > 0:
            differ += '----------------------------------------\n\n'
        return differ

    def getNextTempTag(self,basetag):
        if self.repo == None:
            return False

        tagNumber = 0
        for tag in self.repo.tags:

            temptagNumber = 0
            if str(tag).startswith(basetag):
                try:
                    temptagNumber = int(str(tag).split("_")[-1])
                except ValueError:
                    print '[%s] is not a Number' % (str(tag).split("_")[-1])
                if temptagNumber > tagNumber:
                    tagNumber = temptagNumber
        tagNumber = tagNumber + 1

        status = basetag + '_' + str(tagNumber)
        print  status
        return True

    def removeTempTags(self,basetag):
        if self.repo ==  None:
            return False

        if not self.remotePull():
            print "Failed to pull from repo [%s]" % (self.repoName)
            return False

        for tag in self.repo.tags:
            if str(tag).startswith(basetag):
                status = self.removeTag(str(tag))
                if not status:
                    print "Tag [%s] could not be removed" % (str(tag))
                    return status

        return True

    def removeLastTempTag(self,basetag):
        if self.repo == None:
            return False

        if not self.remotePull():
            print "Failed to pull from repo [%s]" % (self.repoName)
            return False
        temptags = []

        for tag in self.repo.tags:
            tag = str(tag)
            if tag.startswith(basetag + '_') and tag[len(basetag)+1:].isdigit():
                temptags.append(tag)

        if temptags == []:
            print "No temp tags to remove"
            return True

        temptags.sort()
        status = self.removeTag(temptags[-1])
        if not status:
            print "Tag [%s] could not be removed" % (temptags[-1])
            return status
        return True 

    def getUncommittedChanges(self,path=''):
        differ = ''
        g = git.Git(self.repoLocation)
        if len(path) == 0:
            if self.debug:
                print 'Uncommitted Changes on Repo [%s]' % (self.repoName)
            differ = g.diff()
            differ += g.add('-A','-n')
        else:
            if self.debug:
                print 'Uncommitted Changes on Repo [%s] in folder [%s]' % (self.repoName,path)
            differ = g.diff(path)
            differ += g.add('-A','-n',path)
        return differ

    def applyTag(self,tag):
        print 'Apply tag [%s] on Repo [%s]' % (tag,self.repoName)
        if self.repo == None:
            return False
        self.readTags()
        if tag in self.tags or tag in self.repo.tags:
            print 'Tag [%s] already exists' % tag
            return True
        newTag = self.repo.create_tag(tag)
        if newTag == None:
            print 'Failed to create tag [%s]' % tag
            return False
        if not self.remotePush(refObj=newTag):
            print 'Failed to apply tag [%s]' % tag
            return False
        return True

    def removeTag(self,tag):
        print 'Delete tag [%s] from Repo [%s]' % (tag,self.repoName)
        if self.repo == None:
            return False
        if not self.remotePull():
            print 'Failed to pull from repo [%s]' % (self.repoName)
            return False
        self.readTags()
        if tag not in self.tags and tag not in self.repo.tags:
            print 'Tag [%s] does not exist' % tag
            return True
        self.repo.delete_tag(tag)
        g = git.Git(self.repoLocation)
        g.push('origin',':refs/tags/'+tag)
        return True

    def submitChanges(self,msg):
        print 'Submit Changes on Repo [%s]' % (self.repoName)
        if self.repo == None:
            return False
        if not self.remotePull():
            print 'Failed to pull from repo [%s]' % (self.repoName)
            return False
        #Detect uncommitted changes
        if len(self.getUncommittedChanges()) == 0:
            print 'No changes to be pushed on repo [%s]' % self.repoName
            return True
        #Commit them
        g = git.Git(self.repoLocation)
        g.add('-A')
        g.commit('-a','-m','%s' % msg)
        #Push them
        if not self.remotePush():
            print 'Failed to push to repo [%s]' % (self.repoName)
            return False
        return True

    def remotePull(self):
        status = True
        infoList = self.repo.remotes.origin.pull()
        for aInfo in infoList:
            if self.debug:
                print 'PullInfo Summary: %s' % aInfo.summary
                print 'PullInfo Flags: %s' % aInfo.flags
            if aInfo.flags & aInfo.ERROR:
                print 'Failure Reason: %s, Flags: %s' % (aInfo.summary,aInfo.flags)
                status = False
        return status

    def remotePush(self,refObj=None):
        status = True
        if refObj == None:
            infoList = self.repo.remotes.origin.push()
        else:
            infoList = self.repo.remotes.origin.push(refObj)
        for aInfo in infoList:
            if self.debug:
                print 'PushInfo Summary: %s' % aInfo.summary
                print 'PushInfo Flags: %s' % aInfo.flags
            if aInfo.flags & aInfo.ERROR:
                print 'Failure Reason: %s, Flags: %s' % (aInfo.summary,aInfo.flags)
                status = False
        return status

    def action(self,action,branch=None,ref1=None,ref2=None,start=None,end=None,path='',tag=None,endtag=None,message=None,ignore=''):
        if action == 'clean':
            self.clean()
        elif action == 'clone':
            self.clone()
        elif action == 'set-branch':
            if branch == None:
                print 'Invalid parameters'
                return False
            return self.setBranch(branch)
        elif action == 'status':
            self.status()
        elif action == 'current-branch':
            self.showBranch()
        elif action == 'list-branches':
            self.showBranches()
        elif action == 'list-tags':
            self.showTags()
        elif action == 'diff-refs':
            if ref1 == None or ref2 == None:
                print 'Invalid parameters'
                return False
            print self.diffRefs(ref1,ref2)
        elif action == 'commits-by-time':
            if start == None or end == None:
                print 'Invalid parameters'
                return False
            commitMsg = self.commitsByTime(start,end,path=path,exclude=ignore)
            if commitMsg == None:
                return False
            else:
                if len(commitMsg) > 0:
                    print commitMsg
                return True
        elif action == 'commits-by-tag':
            if tag == None:
                print 'Invalid parameters'
                return False
            
            commitMsg = self.commitsByTag(tag,endtag,path=path,exclude=ignore)
            if commitMsg == None or commitMsg is False:
                return False
            else:
                if len(commitMsg) > 0:
                    print commitMsg
                return True
        elif action == 'list-uncommitted-changes':
            unCommittedChanges = self.getUncommittedChanges(path=path)
            if len(unCommittedChanges) > 0:
                print unCommittedChanges
        elif action == 'apply-tag':
            if tag == None:
                print 'Invalid parameters'
                return False
            return self.applyTag(tag)
        elif action == 'get-next-temp-tag':
            if tag == None:
                print 'Invalid parameters'
                return False
            return self.getNextTempTag(tag)
        elif action == 'remove-tag':
            if tag == None:
                print 'Invalid parameters'
                return False
            return self.removeTag(tag)
        elif action == 'remove-temp-tags':
            if tag == None:
                print 'Invalid parameters'
                return False
            return self.removeTempTags(tag)
        elif action == 'remove-last-temp-tag':
            if tag == None:
                print 'Invalid parameters'
                return False
            return self.removeLastTempTag(tag)
        elif action == 'submit-changes':
            if message == None:
                print 'Invalid parameters'
                return False
            return self.submitChanges(message)
        else:
            print 'Invalid Action [%s]' % (action)
            return False
        return True

class cGitArgs:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Git Operations')
        parser.add_argument('-r','--repo',nargs=1,required=True,type=str,help='Git Repository')
        parser.add_argument('-p','--path',nargs=1,required=True,type=str,help='Local Directory Excluding Home')
        actionList = ['clean','set-branch','clone','status','current-branch','list-branches','list-tags','diff-refs','commits-by-time','commits-by-tag','list-uncommitted-changes','apply-tag','get-next-temp-tag','remove-tag','remove-temp-tags','remove-last-temp-tag','submit-changes']
        parser.add_argument('-a','--action',nargs=1,required=True,type=str,choices=actionList,help='Action')

        parser.add_argument('-b','--branch',nargs=1,type=str,help='Git Repo Branch')
        parser.add_argument('-d','--directory',nargs=1,type=str,help='Git Repo Directory')
        parser.add_argument('-x','--ref1',nargs=1,type=str,help='Git Repo Reference 1')
        parser.add_argument('-y','--ref2',nargs=1,type=str,help='Git Repo Reference 2')
        parser.add_argument('-s','--start',nargs=1,type=str,help='Start Date and Time for Git Commits')
        parser.add_argument('-e','--end',nargs=1,type=str,help='End Date and Time for Git Commits')
        parser.add_argument('-t','--tag',nargs=1,type=str,help='Git Tag')
        parser.add_argument('-z','--endtag',nargs=1,type=str,help='Ending Git tag for Git Commits')
        parser.add_argument('-m','--message',nargs=1,type=str,help='Git Commit Message')
        parser.add_argument('-i','--ignore',nargs=1,type=str,help='Exclude expression for Git log')
        args = parser.parse_args()

        self.repo = None
        self.path = None
        self.action = None
        self.branch = None
        self.directory = '.'
        self.ref1 = None
        self.ref2 = None
        self.start = None
        self.end = None
        self.tag = None
        self.endtag = None
        self.message = None
        self.ignore = ''

        self.action = args.action[0]
        self.repo = args.repo[0]
        self.path = args.path[0]
        if args.branch is not None:
            self.branch = args.branch[0]
        if args.directory is not None:
            self.directory = args.directory[0]
        if args.ref1 is not None:
            self.ref1 = args.ref1[0]
        if args.ref2 is not None:
            self.ref2 = args.ref2[0]
        if args.start is not None:
            self.start = args.start[0]
        if args.end is not None:
            self.end = args.end[0]
        if args.tag is not None:
            self.tag = args.tag[0]
        if args.endtag is not None:
            self.endtag = args.endtag[0]
        if args.message is not None:
            self.message = args.message[0]
        if args.ignore is not None:
            self.ignore = args.ignore[0]

def testGitRepo(repo,location):
    gRepo = cGitRepo(repo,location)
    #gRepo.clone()
    #gRepo.status()
    #gRepo.showBranch()
    #gRepo.showBranches()
    #gRepo.showTags()
    #print gRepo.diffRefs('master','testing-git-hook',nameOnly=True)
    #print gRepo.commitsByTime('2016-03-01 00:00:01','2016-04-01 00:00:01')
    #print gRepo.commitsByTime('2016-03-01 00:00:01','2016-04-01 00:00:01','expect')
    #print gRepo.commitsByTime('2016-03-01_00-00-01','2016-04-01_00-00-01')
    #print gRepo.diffRefs('master','testing-git-hook',log=True)
    #print gRepo.getUncommittedChanges()
    #print gRepo.getUncommittedChanges('expect')
    #gRepo.applyTag('Testing_Tag')
    #gRepo.showTags()
    #gRepo.removeTag('Testing_Tag')
    #gRepo.showTags()
    gRepo.submitChanges('Testing Python Git API')
    #gRepo.clean()

#testGitRepo('sandbox/vpandya/prepare-appliance.git','/home/vpandya/Development')
