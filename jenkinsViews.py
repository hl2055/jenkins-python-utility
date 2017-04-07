#!/usr/bin/python

import argparse
import os
import jenkins
import xml.etree.ElementTree as et
import lxml.etree as etree
import time
import json
import collections

class cView:
    def __init__(self,name,connection=None,host='',user='',password='',debug=False,job=''):
        self.server = None
        self.name = name
        self.debug = debug
        self.job = job
        self.jobs = []
        if connection is not None:
            self.server = connection
        else:
            if len(user) == 0:
                self.connect(host)
            else:
                self.connect(host,user=user,password=password)
        parser = etree.XMLParser(remove_blank_text=True)
        if self.server is not None:
            if self.server.view_exists(self.name):
                self.configXml = self.server.get_view_config(self.name).strip()
                root = etree.XML(et.tostring(et.fromstring(self.configXml)),parser)
            else:
                print 'View does not exist -- Defaulting to empty configuation'
                self.configXml = jenkins.EMPTY_VIEW_CONFIG_XML.strip()
                root = etree.XML(self.configXml,parser)
            indentedConfigString = etree.tostring(root,pretty_print=True)
            self.configXml = et.tostring(et.fromstring(indentedConfigString))
            if self.debug:
                print et.tostring(et.fromstring(self.configXml))

    def create(self):
        if self.server ==  None:
            return False
        if not self.server.view_exists(self.name):
            print 'Creating view [%s]' % self.name
            self.server.create_view(self.name,self.configXml)
        return True

    def update(self):
        if self.server ==  None:
            return False
        print 'Update view [%s]' % self.name
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(et.tostring(et.fromstring(self.configXml)),parser)
        indentedConfigString = etree.tostring(root,pretty_print=True)
        self.configXml = et.tostring(et.fromstring(indentedConfigString))
        if self.debug:
            print 'Update View Config'
            print et.tostring(et.fromstring(self.configXml))
        self.server.reconfig_view(self.name,self.configXml)
        self.configXml = self.server.get_view_config(self.name).strip()
        return True

    def delete(self):
        if self.server ==  None:
            return False
        if self.server.view_exists(self.name):
            print 'Deleting view [%s]' % self.name
            self.server.delete_view(self.name)
            self.configXml = jenkins.EMPTY_VIEW_CONFIG_XML
        return True

    def connect(self,server,user=None,password=None):
        if user == None:
            self.server = jenkins.Jenkins(server)
        else:
            self.server = jenkins.Jenkins(server, username=user, password=password)
        if self.server == None:
            print 'Failed to connect to Jenkins server'

    def constructView(self):
        #Start clean to do proper reload
        self.configXml = jenkins.EMPTY_VIEW_CONFIG_XML.strip()
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(self.configXml,parser)
        jobNames = self.addElementAfterCheck(root,'jobNames')
        for aJob in self.jobs:
            stringEl = self.addElement(jobNames,'string')
            stringEl.text = aJob
        indentedConfigString = etree.tostring(root,pretty_print=True)
        self.configXml = et.tostring(et.fromstring(indentedConfigString))
        return True

    def reload(self,jobModified=False):
        status = True
        if self.server ==  None:
            return False
        self.create()
        self.printConfig()
        if not jobModified:
            self.getViewJobs()
        self.constructView()
        self.update()
        self.printConfig()
        return True

    def getViewJobs(self):
        self.jobs = []
        #Find all jobs and sort
        rootEl = et.fromstring(self.configXml)
        jobNamesEl = self.addElementAfterCheck(rootEl,'jobNames')
        for aJob in jobNamesEl.findall('string'):
            if aJob == None:
                continue
            #print 'Testing Add'
            #print aJob.text
            self.jobs.append(aJob.text)
            #print 'Done'
        return True

    def addJob(self,job):
        self.getViewJobs()

        if len(self.jobs) > 0:
            if job not in self.jobs:
                self.jobs.append(job)
            #print self.jobs
            self.jobs.sort()
            #print self.jobs
        else:
            self.jobs = [job]

        return self.reload(jobModified=True)

    def removeJob(self,job):
        self.getViewJobs()

        if len(self.jobs) > 0:
            if job in self.jobs:
                self.jobs.remove(job)
            #print jobs
            self.jobs.sort()
            #print jobs

        return self.reload(jobModified=True)

    def setElementBooleanValue(self,parent,name,boolValue):
        element = self.addElementAfterCheck(parent,name)
        if boolValue:
            element.text = 'true'
        else:
            element.text = 'false'
        return element

    def addElementAfterCheck(self,parent,name):
        element = parent.find(name)
        if element == None:
            element = et.SubElement(parent,name)
        return element

    def addElement(self,parent,name):
        element = et.SubElement(parent,name)
        return element

    def getScriptOutput(self,script):
        if self.server ==  None:
            return False
        return self.server.run_script(script).strip()

    def printInfo(self):
        if self.server ==  None:
            return False
        if self.server.view_exists(self.name):
            print self.server.get_view_info(self.name)
        return True

    def getPluginVersion(self,name):
        if self.server ==  None:
            return None
        if self.debug:
            print self.server.get_plugin_info(name)['version']
        return self.server.get_plugin_info(name)['version']

    def printPlugins(self):
        if self.server ==  None:
            return False
        print self.server.get_plugins()
        return True

    def printConfig(self):
        if self.server ==  None:
            return False
        if self.server.view_exists(self.name):
            print 'Print View [%s] Config' % self.name
            print et.tostring(et.fromstring(self.configXml))
        return True

    def printViews(self):
        if self.server == None:
            return False
        views = self.server.get_views()
        for view in views:
            print 'View [%s]' % view['name']
        return True

    def action(self,action):
        if action == 'delete':
            self.delete()
        elif action == 'reload':
            self.reload()
        elif action == 'show':
            self.printConfig()
            self.printViews()
        elif action == 'add':
            if len(self.job) < 0:
                print 'Invalid Argument'
                exit(1)
            self.addJob(self.job)
        elif action == 'remove':
            if len(self.job) < 0:
                print 'Invalid Argument'
                exit(1)
            self.removeJob(self.job)
        else:
            print 'Invalid Action [%s]' % (action)

class cViewArgs:
    def __init__(self):
        parser = argparse.ArgumentParser(description='Jenkis View Actions')
        actionList = ['delete','reload','show','add','remove']
        parser.add_argument('-a','--action',nargs=1,required=True,type=str,choices=actionList,help='Action')
        parser.add_argument('-s','--server',nargs=1,type=str,help='Jenkins Server URL')
        parser.add_argument('-u','--user',nargs=1,type=str,help='Jenkins Server User')
        parser.add_argument('-p','--password',nargs=1,type=str,help='Jenkins Server Password')
        parser.add_argument('-d','--debug',help='Turn debug on',action="store_true")
        parser.add_argument('-j','--job',nargs=1,type=str,help='Jenkins Job')
        args = parser.parse_args()

        self.action = args.action[0]
        self.server = 'http://172.36.21.41:8080/'
        if args.server is not None:
            self.server = args.server[0]
        self.user = ''
        if args.user is not None:
            self.user = args.user[0]
        self.password = ''
        if args.password is not None:
            self.password = args.password[0]
        self.debug = False
        if args.debug:
            self.debug = True
        self.job = ''
        if args.job is not None:
            self.job = args.job[0]

#viewArgs = cViewArgs()
#testView = cView('aws',host=viewArgs.server,user=viewArgs.user,password=viewArgs.password,debug=viewArgs.debug,job=viewArgs.job)
#testView.action(viewArgs.action)
