#!/usr/bin/python

import pexpect
import time
import os

from shellCommand import *

######################################################################################
#SSH Connection  related Operations
class cSshConnection:
    def __init__(self,server,user,password,prompt,retry=30,wait=30):
        self.sshCon = None
        self.server = server
        self.user = user
        self.password = password
        self.jumpUser = None
        self.jumpPassword = None
        self.prompt = prompt
        self.retry = retry
        self.waitTime = wait
        self.cliCon = False
        self.protocol = 'ssh'
        self.spawnCmd = self.protocol + ' ' + self.user + '@' + self.server
        if self.prompt.find('>') > 0:
            self.cliCon = True

    def sshConnect(self):
        status = False
        self.protocol = 'ssh'
        self.spawnCmd = self.protocol + ' ' + self.user + '@' + self.server
        if self.connect():
            status = True
        return status

    def isJumpHostReachable(self,server):
        reachable = False
        aCmd = cShellCommand('ping -c 1 -W 2 ' + server,'Check Jump Host Reachability')
        for i in range(0,3):
            if aCmd.exe():
                reachable = True
                break
        if not reachable:
            self.reachable = False
            print 'Jump Host ' + server + ' is not reachable'
        else:
            self.reachable = True
            print 'Jump Host ' + server + ' is reachable'
        return reachable
        
    def sshJumphostConnect(self,server,user,password):
        if not self.isJumpHostReachable(server):
            return False
        status = False
        prompt = '\$'
        aCon = cSshConnection(server,user,password,prompt)
        if aCon.sshConnect():
            if not aCon.execCmd('ssh-keygen -f ~/.ssh/known_hosts -R' + self.server):
                print 'Failed to clear SSH keys for ' + self.server + ' in jump host ' + server
            else:
                status = True
            aCon.close()

        if not status:
            return status

        #Increase retries for jump host as machine can take time to come up
        self.retry = 120
        self.jumpUser = user
        self.jumpPassword = password
        self.spawnCmd = self.protocol + ' -A -t -l ' + user + ' ' + server
        self.spawnCmd+= ' ssh -A -t -l ' + self.user + ' ' + self.server
        if self.connect():
            status = True
        return status

    def scpDownload(self,localFile,remoteFile):
        status = False
        self.protocol = 'scp'
        self.spawnCmd = self.protocol + ' -r ' + self.user + '@' + self.server + ':' + remoteFile + ' ' + localFile
        if self.connect():
            if os.path.exists(localFile):
                status = True
            self.close()
        return status

    def scpUpload(self,localFile,remoteFile):
        status = False
        if not os.path.exists(localFile):
            print 'Local file do not exists'
            return status
        self.protocol = 'scp'
        self.spawnCmd = self.protocol + ' -r ' + localFile + ' ' + self.user + '@' + self.server + ':' + remoteFile
        if self.connect():
            self.close()
            status = True
        return status

    def clearSshKey(self):
        #Clear ssh-keygen before connecting
        print pexpect.run("ssh-keygen -R " + self.server)

    def connect(self):
        print 'Spawn: ' + self.spawnCmd
        sshExpectList = [pexpect.EOF,pexpect.TIMEOUT]
        sshNewKeyMatch = 'Are you sure you want to continue connecting'
        sshExpectList.append(sshNewKeyMatch)
        passwordMatch = self.user + ".*assword:"
        sshExpectList.append(passwordMatch)
        promptMatch = ".*" + self.prompt
        sshExpectList.append(promptMatch)
        cliTerminateMatch = "Terminate existing session\? \(Yes or No\):"
        sshExpectList.append(cliTerminateMatch)
        wrongPasswordMatch = "Permission denied"
        sshExpectList.append(wrongPasswordMatch)
        missingFileMatch = ".*No such file or directory.*"
        sshExpectList.append(missingFileMatch)
        if self.jumpUser is not None and self.jumpPassword is not None:
            jumpUserMatch = self.jumpUser + ".*assword:"
            sshExpectList.append(jumpUserMatch)
        connected = False
        self.clearSshKey()
        for r in range(0,self.retry):
            self.sshCon = pexpect.spawn(self.spawnCmd,maxread=10000,logfile=sys.stdout,timeout=self.waitTime)
            while not connected:
                if not self.sshCon.isalive():
                    print 'Not connected'
                    return False
                index = self.sshCon.expect(sshExpectList)
                #EOF
                if index == 0 and self.protocol == 'ssh':
                    print "Unable to connect to " + self.server + " in " + str(r+1) + " try"
                    self.sshCon.close(force=True)
                    self.sshCon = None
                    time.sleep(1)
                    break
                elif index == 0 and self.protocol == 'scp':
                    print 'Finished scp operation'
                    return True
                #Timeout
                elif index == 1: #timeout
                    print "Timed out after " + str(self.waitTime) + " seconds"
                    self.sshCon.close(force=True)
                    self.sshCon = None
                    time.sleep(1)
                    break
                    #return connected
                #SSH New Key
                elif index == 2:
                    self.sshCon.sendline('yes')
                #Password
                elif index == 3:
                    self.sshCon.sendline(self.password)
                    print 'Enter User Password'
                #Prompt
                elif index == 4 and self.protocol == 'ssh':
                    connected = True
                #CLI Terminate
                elif index == 5:
                    self.sshCon.sendline('yes')
                #Wrong password
                elif index == 6:
                    print 'Please check password'
                    self.sshCon.close(force=True)
                    self.sshCon = None
                    return connected
                #Missing file or directory
                elif index == 7 and self.protocol == 'scp':
                    print 'Please check remote file/directory'
                    self.sshCon.close(force=True)
                    self.sshCon = None
                    return connected
                #Jump host password
                elif index == 8 and self.protocol == 'ssh':
                    self.sshCon.sendline(self.jumpPassword)
                    print 'Enter Jump Host Password'
                #print self.sshCon.before + self.sshCon.after
            time.sleep(1)
            if connected:
                break
        return connected
                
    def setWait(self,time):
        self.waitTime = time

    def setRetry(self,count):
        self.retry = count

    def execCmd(self,cmd,exitWithoutSave=False,waitTime=30,waitRetry=6):
        #print 'Executing command: ' + cmd
        self.cmdout = ''
        cmdExpectList = [pexpect.EOF,pexpect.TIMEOUT]
        promptMatch = ".*" + self.prompt
        cmdExpectList.append(promptMatch)
        cliConfirmationMatch = '\(Y/y or N/n\)\?'
        patchConfirmationMatch='Please answer yes or no'
        rebootMatch='rebooting the system'
        cmdExpectList.append(cliConfirmationMatch)
        cmdExpectList.append(patchConfirmationMatch)
        #cmdExpectList.append(rebootMatch)
        status = False
        if self.sshCon == None:
            return False
        if not self.sshCon.isalive():
            print 'Connection is not alive'
            return False
        self.sshCon.logfile = None
        self.sshCon.sendline(cmd)
        self.sshCon.logfile = sys.stdout
        finished = False
        cliFailed = False
        timeoutRetry = 0
        while not finished:
            index = self.sshCon.expect(cmdExpectList,waitTime)
            #EOF
            if index == 0:
                print "Connection closed"
                finished = True
            #Timeout
            elif index == 1: #timeout
                print self.sshCon.before
                if timeoutRetry == waitRetry:
                    print "TIMED OUT"
                    finished = True
                else:
                    timeoutRetry += 1
                    print "Timed out after " + str(waitTime) + " seconds...waiting"
                    time.sleep(1)
            #Prompt
            elif index == 2:
                #Remove first and last line as first is command and last is prompt
                outputLines = self.sshCon.after.split('\r\n')
                if len(outputLines) > 0:
                    outputLines.pop(0)
                if len(outputLines) > 0:
                    outputLines.pop()
                self.cmdout = '\n'.join(outputLines)
                if self.cmdout.find('Illegal parameter') > 0:
                    cliFailed = True
                    self.sshCon.sendcontrol('c')
                else:
                    if not cliFailed:
                        status = True
                    finished = True
            #CLI Confirmation
            elif index == 3:
                if exitWithoutSave:
                    self.sshCon.sendline('n')
                else:
                    self.sshCon.sendline('y')
            #Patch Confirmation
            elif index == 4:
                self.sshCon.sendline('yes')
            #Reboot Check
            elif index == 5:
                print 'Appliance Rebooting'
                status = True
                finished = True
        return status

    def getCmdOut(self):
        if hasattr(self,'cmdout'):
            return self.cmdout
        else:
            return ''
        
    def getExpectCon(self):
        if self.sshCon is not None and self.sshCon.isalive():
            return self.sshCon
        else:
            return None

    def isConAlive(self):
        if self.sshCon is not None and self.sshCon.isalive():
            return True
        else:
            return False

    def close(self):
        if self.sshCon is not None and self.sshCon.isalive():
            if self.cliCon:
                self.execCmd('exit',waitTime=10,waitRetry=0)
            self.sshCon.close(force=True)
            self.sshCon = None
        else:
            print 'SSH connection closed'
