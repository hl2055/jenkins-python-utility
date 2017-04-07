#!/usr/bin/python

import os
import jenkins
import xml.etree.ElementTree as et
import lxml.etree as etree
import time
import json
import collections

from jenkinsViews import *

class cJob:
    def __init__(self,name,jobJson='',jobCredJson='',host='',user='',password='',debug=False):
        self.server = None
        self.jobJson = jobJson
        self.jobCredJson = jobCredJson
        self.buildParams = ''
        if len(self.jobJson) == 0:
            self.name = name
        else:
            self.name = self.jobJson['name']
            if 'build_params' in self.jobJson:
                self.buildParams = self.jobJson['build_params']
        
        self.debug = debug
        if len(user) == 0:
            self.connect(host)
        else:
            self.connect(host,user=user,password=password)
        self.nextBuildNumber = 0
        self.lastBuildNumber = 0
        parser = etree.XMLParser(remove_blank_text=True)
        if self.server is not None:
            if self.server.job_exists(self.name):
                self.configXml = self.server.get_job_config(self.name).strip()
                root = etree.XML(et.tostring(et.fromstring(self.configXml)),parser)
            else:
                print 'Job does not exist -- Defaulting to empty configuation'
                self.configXml = jenkins.EMPTY_CONFIG_XML.strip()
                root = etree.XML(self.configXml,parser)
            indentedConfigString = etree.tostring(root,pretty_print=True)
            self.configXml = et.tostring(et.fromstring(indentedConfigString))

    def create(self,jobType='project'):
        if self.server ==  None:
            return False
        print 'Creating job [%s]' % self.name
        if jobType == 'multijob':
            #Update root from project to com.tikal.jenkins.plugins.multijob.MultiJobProject
            self.configXml = self.configXml.replace('<project>','<com.tikal.jenkins.plugins.multijob.MultiJobProject>')
            self.configXml = self.configXml.replace('</project>','</com.tikal.jenkins.plugins.multijob.MultiJobProject>')
        self.server.create_job(self.name,self.configXml)
        return True

    def update(self):
        if self.server ==  None:
            return False
        print 'Update job [%s]' % self.name
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(et.tostring(et.fromstring(self.configXml)),parser)
        indentedConfigString = etree.tostring(root,pretty_print=True)
        self.configXml = et.tostring(et.fromstring(indentedConfigString))
        if self.debug:
            print 'Update Job Config'
            print et.tostring(et.fromstring(self.configXml))
        self.server.reconfig_job(self.name,self.configXml)
        self.configXml = self.server.get_job_config(self.name).strip()
        return True

    def delete(self):
        if self.server ==  None:
            return False
        if self.server.job_exists(self.name):
            print 'Deleting job [%s]' % self.name
            self.server.delete_job(self.name)
            self.configXml = jenkins.EMPTY_CONFIG_XML
        return True

    def connect(self,server,user=None,password=None):
        if user == None:
            self.server = jenkins.Jenkins(server)
        else:
            self.server = jenkins.Jenkins(server, username=user, password=password)
        if self.server == None:
            print 'Failed to connect to Jenkins server'

    def build(self):
        status = True
        if self.server ==  None:
            return False
        if self.server.job_exists(self.name):
            jobInfo = self.server.get_job_info(self.name)
            self.nextBuildNumber = jobInfo['nextBuildNumber']
            if 'lastBuild' in jobInfo and jobInfo['lastBuild'] is not None and 'number' in jobInfo['lastBuild']:
                self.lastBuildNumber = jobInfo['lastBuild']['number']
            if len(self.buildParams) == 0:
                self.server.build_job(self.name)
            else:
                self.server.build_job(self.name,self.buildParams)
            if self.debug:
                print json.dumps(jobInfo, default=lambda o: o.__dict__,sort_keys=True, indent=4)
        return status

    def lastSuccessfulBuild(self):
        status = True
        if self.server ==  None:
            return False
        if self.server.job_exists(self.name):
            lastSuccessfulBuild = self.server.get_job_info(self.name)['lastSuccessfulBuild']['number']
            print '%s - Last Successful Build [%d]' % (self.name,lastSuccessfulBuild)
        return status

    def lastBuildStatus(self):
        status = True
        if self.server ==  None:
            return False
        if self.server.job_exists(self.name):
            lastSuccessfulBuild = self.server.get_job_info(self.name)['lastSuccessfulBuild']['number']
            lastBuild = self.server.get_job_info(self.name)['lastBuild']['number']
            if lastSuccessfulBuild == lastBuild:
                print '%s - Build [%d] Successful' % (self.name,lastBuild)
            else:
                print '%s - Build [%d] Failed' % (self.name,lastBuild)
                status = False
        return status

    def monitor(self,timeout=300):
        status = True
        if self.server ==  None:
            return False
        runningBuildNames = []
        runningBuilds = self.server.get_running_builds()
        if len(runningBuilds) > 0:
            for rBuild in runningBuilds:
                runningBuildNames.append(rBuild['name'])
        count = 0
        while ( ( len(runningBuildNames) > 0 and self.name in runningBuildNames ) or 
                ( self.nextBuildNumber != 0 and self.nextBuildNumber != self.lastBuildNumber ) ):
            if len(runningBuildNames) > 0 and self.name in runningBuildNames:
                print '%s Running...Wait[%d]' % (self.name,count)
            else:
                print '%s Will Start...Wait[%d]' % (self.name,count)
            if self.debug:
                print 'Next Build: [%d], Last Build: [%d]' % (self.nextBuildNumber,self.lastBuildNumber)
                print 'Running Build Names: [%d]' % (len(runningBuildNames))
                print runningBuildNames
                print 'Running Builds: [%d]' % (len(runningBuilds))
                print runningBuilds
                print '%s Running...Wait[%d]' % (self.name,count)
            count = count + 1
            if count > timeout:
                break
            time.sleep(1)
            jobInfo = self.server.get_job_info(self.name)
            if 'lastBuild' in jobInfo and jobInfo['lastBuild'] is not None and 'number' in jobInfo['lastBuild']:
                self.lastBuildNumber = jobInfo['lastBuild']['number']
            runningBuildNames = []
            runningBuilds = self.server.get_running_builds()
            if len(runningBuilds) > 0:
                for rBuild in runningBuilds:
                    runningBuildNames.append(rBuild['name'])
        if count <= timeout:
            print '%s Finished' % (self.name)
        else:
            print '%s Timed out' % (self.name)
            status = False
        return status

    def setDescription(self,description):
        rootEl = et.fromstring(self.configXml)
        descriptionEl = self.addElementAfterCheck(rootEl,'description')
        descriptionEl.text = description
        self.configXml = et.tostring(rootEl)
        return True

    def setBuildCleanup(self,numBuilds):
        rootEl = et.fromstring(self.configXml)

        propertiesEl = self.addElementAfterCheck(rootEl,'properties')
        buildDiscarderPropertyEl = self.addElementAfterCheck(propertiesEl,'jenkins.model.BuildDiscarderProperty')
        strategyEl = self.addElementAfterCheck(buildDiscarderPropertyEl,'strategy')
        strategyEl.set('class','hudson.tasks.LogRotator')
        daystokeepEl = self.addElementAfterCheck(strategyEl,'daysToKeep')
        daystokeepEl.text = '-1'
        numtokeepEl = self.addElementAfterCheck(strategyEl,'numToKeep')
        numtokeepEl.text = numBuilds
        artifactDaystokeepEl = self.addElementAfterCheck(strategyEl,'artifactDaysToKeep')
        artifactDaystokeepEl.text = '-1'
        artifactNumtokeepEl = self.addElementAfterCheck(strategyEl,'artifactNumToKeep')
        artifactNumtokeepEl.text = '-1'

        self.configXml = et.tostring(rootEl)
        return True

    def setParameter(self,name,value,description,string=False,password=False,boolean=False):
        rootEl = et.fromstring(self.configXml)

        propertiesEl = self.addElementAfterCheck(rootEl,'properties')
        paramDefPropertyEl = self.addElementAfterCheck(propertiesEl,'hudson.model.ParametersDefinitionProperty')
        paramDefEl = self.addElementAfterCheck(paramDefPropertyEl,'parameterDefinitions')

        if string:
            nodeString = 'hudson.model.StringParameterDefinition' 
            paramValue = value
        elif password:
            nodeString = 'hudson.model.PasswordParameterDefinition'
            #Encrypt password
            script = 'println hudson.util.Secret.fromString("' + value + '").getEncryptedValue()'
            paramValue = self.getScriptOutput(script)
        elif boolean:
            nodeString = 'hudson.model.BooleanParameterDefinition'
            if value == 'yes':
                paramValue = 'true'
            else:
                paramValue = 'false'
        else:
            return False
        #self.delImmediateElement(paramDefEl,nodeString,'name',name)
        paramEl = self.addElement(paramDefEl,nodeString)

        stringNameEl = self.addElement(paramEl,'name')
        stringNameEl.text = name
        stringValueEl = self.addElement(paramEl,'defaultValue')
        stringValueEl.text = paramValue
        stringDescriptionEl = self.addElement(paramEl,'description')
        stringDescriptionEl.text = description

        self.configXml = et.tostring(rootEl)
        return True

    def setGit(self,repo,branch,credential,local_branch=False):
        rootEl = et.fromstring(self.configXml)


        scmEl = self.addElementAfterCheck(rootEl,'scm')
        multipleScmsVersion = self.getPluginVersion('multiple-scms')
        scmEl.set('class','org.jenkinsci.plugins.multiplescms.MultiSCM')
        scmEl.set('plugin','multiple-scms@'+multipleScmsVersion)

        scmsEl = self.addElementAfterCheck(scmEl,'scms')

        repoString = 'ssh://git@git/' + repo
        #self.delTreeElement(scmsEl,'hudson.plugins.git.GitSCM','hudson.plugins.git.UserRemoteConfig','url',repoString)

        hudsonPluginGitEl = self.addElement(scmsEl,"hudson.plugins.git.GitSCM")
        gitVersion = self.getPluginVersion('git')
        hudsonPluginGitEl.set('plugin','git@'+gitVersion)
        configVersionEl = self.addElement(hudsonPluginGitEl,'configVersion')
        configVersionEl.text = '2'
        userRemoteConfigsEl = self.addElement(hudsonPluginGitEl,'userRemoteConfigs')
        gitRemoteConfigEl = self.addElement(userRemoteConfigsEl,'hudson.plugins.git.UserRemoteConfig')

        urlEl = self.addElement(gitRemoteConfigEl,'url')
        urlEl.text = repoString
        credentialsIdEl = self.addElement(gitRemoteConfigEl,'credentialsId')
        script = 'def creds = com.cloudbees.plugins.credentials.CredentialsProvider.lookupCredentials(\ncom.cloudbees.plugins.credentials.common.StandardUsernameCredentials.class,\nJenkins.instance,\nnull,\nnull\n);\nfor (c in creds) {\nuser = c.getUsername()\nif (user.equals("' + credential + '")) println c.getId()\n}'
        credentialsIdEl.text = self.getScriptOutput(script)

        branchesEl = self.addElement(hudsonPluginGitEl,'branches')
        branchSpecEl = self.addElement(branchesEl,'hudson.plugins.git.BranchSpec')
        branchEl = self.addElement(branchSpecEl,'name')
        branchEl.text = branch

        genSubConfigEl = self.addElement(hudsonPluginGitEl,'doGenerateSubmoduleConfigurations')
        genSubConfigEl.text = 'false'

        subModuleCfgEl = self.addElement(hudsonPluginGitEl,'submoduleCfg')
        subModuleCfgEl.set('class','list')

        extensionsEl = self.addElement(hudsonPluginGitEl,'extensions')
        relativeTargetDirEl = self.addElement(extensionsEl,'hudson.plugins.git.extensions.impl.RelativeTargetDirectory')
        relativeTargetDirNameEl = self.addElement(relativeTargetDirEl,'relativeTargetDir')
        #Get directory name from the repo name
        relativeTargetDirNameEl.text = os.path.basename(repo).split('.git')[0]
        cleanBeforeCheckoutEl = self.addElement(extensionsEl,'hudson.plugins.git.extensions.impl.CleanBeforeCheckout')
        if local_branch:
            gitLocalBranchEl = self.addElement(extensionsEl,'hudson.plugins.git.extensions.impl.LocalBranch')
            localBranchEl = self.addElement(gitLocalBranchEl,'localBranch')
            localBranchEl.text = branch

        self.configXml = et.tostring(rootEl)
        return True

    def setOneGit(self,repo,branch,credential):
        rootEl = et.fromstring(self.configXml)

        gitVersion = self.getPluginVersion('git')

        scmEl = self.addElementAfterCheck(rootEl,'scm')
        scmEl.set('class','hudson.plugins.git.GitSCM')
        scmEl.set('plugin','git@'+gitVersion)
        configVersionEl = self.addElementAfterCheck(scmEl,'configVersion')
        configVersionEl.text = '2'
        userRemoteConfigsEl = self.addElementAfterCheck(scmEl,'userRemoteConfigs')

        #For multiple repos
        gitRemoteConfigEl = et.SubElement(userRemoteConfigsEl,'hudson.plugins.git.UserRemoteConfig')

        urlEl = et.SubElement(gitRemoteConfigEl,'url')
        urlEl.text = 'ssh://git@git/' + repo
        credentialsIdEl = et.SubElement(gitRemoteConfigEl,'credentialsId')
        script = 'def creds = com.cloudbees.plugins.credentials.CredentialsProvider.lookupCredentials(\ncom.cloudbees.plugins.credentials.common.StandardUsernameCredentials.class,\nJenkins.instance,\nnull,\nnull\n);\nfor (c in creds) {\nuser = c.getUsername()\nif (user.equals("' + credential + '")) println c.getId()\n}'
        credentialsIdEl.text = self.getScriptOutput(script)

        branchesEl = self.addElementAfterCheck(scmEl,'branches')
        branchSpecEl = self.addElementAfterCheck(branchesEl,'hudson.plugins.git.BranchSpec')
        branchEl = self.addElement(branchSpecEl,'name')
        branchEl.text = branch

        genSubConfigEl = self.addElementAfterCheck(scmEl,'doGenerateSubmoduleConfigurations')
        genSubConfigEl.text = 'false'

        subModuleCfgEl = self.addElementAfterCheck(scmEl,'submoduleCfg')
        subModuleCfgEl.set('class','list')

        extensionsEl = self.addElementAfterCheck(scmEl,'extensions')
        cleanBeforeCheckoutEl = self.addElementAfterCheck(extensionsEl,'hudson.plugins.git.extensions.impl.CleanBeforeCheckout')

        self.configXml = et.tostring(rootEl)
        return True

    def setGlobalPasswords(self,name,value):
        rootEl = et.fromstring(self.configXml)

        buildWrappersEl = self.addElementAfterCheck(rootEl,'buildWrappers')
        envInjectPasswordWrapperEl = self.addElementAfterCheck(buildWrappersEl,'EnvInjectPasswordWrapper')
        envinjectVersion = self.getPluginVersion('envinject')
        envInjectPasswordWrapperEl.set('plugin','envinject@' + envinjectVersion)
        injectGlobalPasswordsEl = self.addElementAfterCheck(envInjectPasswordWrapperEl,'injectGlobalPasswords')
        injectGlobalPasswordsEl.text = "true"
        maskPasswordParametersEl = self.addElementAfterCheck(envInjectPasswordWrapperEl,'maskPasswordParameters')
        maskPasswordParametersEl.text = "true"
        passwordEntriesEl = self.addElementAfterCheck(envInjectPasswordWrapperEl,'passwordEntries')

        #self.delImmediateElement(passwordEntriesEl,'EnvInjectPasswordEntry','name',name)

        envInjectPasswordEntryEl = self.addElement(passwordEntriesEl,'EnvInjectPasswordEntry')
        nameEl = self.addElement(envInjectPasswordEntryEl,'name')
        nameEl.text = name
        valueEl = self.addElement(envInjectPasswordEntryEl,'value')
        #Encrypt password
        script = 'println hudson.util.Secret.fromString("' + value + '").getEncryptedValue()'
        valueEl.text = self.getScriptOutput(script)

        self.configXml = et.tostring(rootEl)
        return True

    def setEnvironmentVariables(self,filePath='',content=''):
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        envInjectBuilderEl = self.addElementAfterCheck(buildersEl,'EnvInjectBuilder')
        envInjectVersion = self.getPluginVersion('envinject')
        envInjectBuilderEl.set('plugin','envinject@' + envInjectVersion)
        infoEl = self.addElementAfterCheck(envInjectBuilderEl,'info')
        propertiesFilePathEl = self.addElementAfterCheck(infoEl,'propertiesFilePath')
        propertiesFilePathEl.text = filePath
        propertiesContentEl = self.addElementAfterCheck(infoEl,'propertiesContent')
        propertiesContentEl.text = content

        self.configXml = et.tostring(rootEl)
        return True

    def setExecGroovyScript(self,fileName,script):
        if len(fileName) == 0 and len(script) == 0:
            return True
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        groovyEl = self.addElementAfterCheck(buildersEl,'hudson.plugins.groovy.SystemGroovy')
        groovyVersion = self.getPluginVersion('groovy')
        groovyEl.set('plugin','groovy@' + groovyVersion)

        scriptSourceEl = et.SubElement(groovyEl,"scriptSource")
        #Exclusive or
        if len(fileName) > 0:
            scriptSourceEl.set('class','hudson.plugins.groovy.FileScriptSource')
            scriptFileEl = et.SubElement(scriptSourceEl,"scriptFile")
            scriptFileEl.text = fileName
            groovyNameEl = et.SubElement(groovyEl,"groovyName")
            groovyNameEl.text = '(Default)'
            parametersEl = et.SubElement(groovyEl,"parameters")
            scriptParametersEl = et.SubElement(groovyEl,"scriptParameters")
            propertiesEl = et.SubElement(groovyEl,"properties")
            javaOptsEl = et.SubElement(groovyEl,"javaOpts")
        else:
            scriptSourceEl.set('class','hudson.plugins.groovy.StringScriptSource')
            commandEl = et.SubElement(scriptSourceEl,"command")
            commandEl.text = script
            classPathEl = et.SubElement(groovyEl,"bindings")
        classPathEl = et.SubElement(groovyEl,"classPath")

        self.configXml = et.tostring(rootEl)
        return True

    def setExecShellScript(self,script):
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        shellEl = self.addElement(buildersEl,"hudson.tasks.Shell")
        commandEl = self.addElement(shellEl,"command")
        commandEl.text = script

        self.configXml = et.tostring(rootEl)
        return True

    def setGradleScript(self,wrapper=False,executableGradlew=False,fromRootBuildScriptDir=False,description='',switches='',tasks='',rootBuildScript='',buildFile='',useWorkspace=False,passParamsAsGradleProperties=False):
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        gradleEl = self.addElementAfterCheck(buildersEl,'hudson.plugins.gradle.Gradle')
        gradleVersion = self.getPluginVersion('gradle')
        gradleEl.set('plugin','gradle@' + gradleVersion)
        descriptionEl = self.addElementAfterCheck(gradleEl,'description')
        if len(description) > 0:
            descriptionEl.text = description
        switchesEl = self.addElementAfterCheck(gradleEl,'switches')
        if len(switches) > 0:
            switchesEl.text = switches
        tasksEl = self.addElementAfterCheck(gradleEl,'tasks')
        if len(tasks) > 0:
            tasksEl.text = tasks
        rootBuildScriptDirEl = self.addElementAfterCheck(gradleEl,'rootBuildScriptDir')
        if len(rootBuildScript) > 0:
            rootBuildScriptDirEl.text = rootBuildScript
        buildFileEl = self.addElementAfterCheck(gradleEl,'buildFile')
        if len(buildFile) > 0:
            buildFileEl.text = buildFile
        gradleNameEl = self.addElementAfterCheck(gradleEl,'gradleName')
        gradleNameEl.text = "(Default)"
        useWrapperEl = self.setElementBooleanValue(gradleEl,'useWrapper',wrapper)
        makeExecutableEl = self.setElementBooleanValue(gradleEl,'makeExecutable',executableGradlew)
        fromRootBuildScriptDirEl = self.setElementBooleanValue(gradleEl,'fromRootBuildScriptDir',fromRootBuildScriptDir)
        useWorkspaceAsHomeEl = self.setElementBooleanValue(gradleEl,'useWorkspaceAsHome',useWorkspace)
        passAsPropertiesEl = self.setElementBooleanValue(gradleEl,'passAsProperties',passParamsAsGradleProperties)

        self.configXml = et.tostring(rootEl)
        return True

    def setJobDsl(self,script):
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        executeDslScriptsEl = self.addElementAfterCheck(buildersEl,'javaposse.jobdsl.plugin.ExecuteDslScripts')
        jobDslVersion = self.getPluginVersion('job-dsl')
        executeDslScriptsEl.set('plugin','job-dsl@' + jobDslVersion)

        targetsEl = self.addElement(executeDslScriptsEl,"targets")
        targetsEl.text = script
        usingScriptTextEl = self.addElement(executeDslScriptsEl,"usingScriptText")
        usingScriptTextEl.text = 'false'
        ignoreExistingEl = self.addElement(executeDslScriptsEl,"ignoreExisting")
        ignoreExistingEl.text = 'false'
        removedJobActionEl = self.addElement(executeDslScriptsEl,"removedJobAction")
        removedJobActionEl.text = 'IGNORE'
        removedViewActionEl = self.addElement(executeDslScriptsEl,"removedViewAction")
        removedViewActionEl.text = 'IGNORE'
        lookupStrategyEl = self.addElement(executeDslScriptsEl,"lookupStrategy")
        lookupStrategyEl.text = 'JENKINS_ROOT'
        additionalClasspathEl = self.addElement(executeDslScriptsEl,"additionalClasspath")

        self.configXml = et.tostring(rootEl)
        return True


    def setTimestamp(self,timeFormat):
        rootEl = et.fromstring(self.configXml)

        propertiesEl = self.addElementAfterCheck(rootEl,'properties')
        zentimestampEl = self.addElementAfterCheck(propertiesEl,'hudson.plugins.zentimestamp.ZenTimestampJobProperty')
        zentimestampVersion = self.getPluginVersion('zentimestamp')
        zentimestampEl.set('plugin','zentimestamp@' + zentimestampVersion)

        changeBuildIdEl = self.addElementAfterCheck(zentimestampEl,'changeBUILDID')
        changeBuildIdEl.text = 'true'
        patternEl = self.addElementAfterCheck(zentimestampEl,'pattern')
        patternEl.text = timeFormat

        self.configXml = et.tostring(rootEl)
        return True

    def setPeriodicBuild(self,period):
        rootEl = et.fromstring(self.configXml)

        triggersEl = self.addElementAfterCheck(rootEl,'triggers')
        timerTriggerEl = self.addElementAfterCheck(triggersEl,'hudson.triggers.TimerTrigger')
        specEl = self.addElementAfterCheck(timerTriggerEl,'spec')
        specEl.text = period

        self.configXml = et.tostring(rootEl)
        return True

    def setSlave(self,name):
        rootEl = et.fromstring(self.configXml)

        nodeEl = self.addElementAfterCheck(rootEl,'assignedNode')
        nodeEl.text = name
        canRoamEl = self.setElementBooleanValue(rootEl,'canRoam',False)

        self.configXml = et.tostring(rootEl)
        return True

    def setConditionalStep(self,fileName,runProject):
        rootEl = et.fromstring(self.configXml)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')

        singleStepConditionEl = self.addElementAfterCheck(buildersEl,'org.jenkinsci.plugins.conditionalbuildstep.singlestep.SingleConditionalBuilder')
        conditionalBuildStepVersion = self.getPluginVersion('conditional-buildstep')
        singleStepConditionEl.set('plugin','conditional-buildstep@' + conditionalBuildStepVersion)

        conditionEl = self.addElementAfterCheck(singleStepConditionEl,'condition')
        conditionVersion = self.getPluginVersion('run-condition')
        conditionEl.set('class','org.jenkins_ci.plugins.run_condition.core.FileExistsCondition')
        conditionEl.set('plugin','run-condition@' + conditionVersion)
        fileEl = self.addElementAfterCheck(conditionEl,'file')
        fileEl.text = fileName
        baseDirEl = self.addElementAfterCheck(conditionEl,'baseDir')
        baseDirEl.set('class','org.jenkins_ci.plugins.run_condition.common.BaseDirectory$Workspace')

        buildStepEl = self.addElementAfterCheck(singleStepConditionEl,'buildStep')
        buildStepEl.set('class','hudson.plugins.parameterizedtrigger.TriggerBuilder')
        buildStepVersion = self.getPluginVersion('parameterized-trigger')
        buildStepEl.set('plugin','parameterized-trigger@' + buildStepVersion)
        configsEl = self.addElementAfterCheck(buildStepEl,'configs')
        blockableBuildTriggerConfigEl = self.addElementAfterCheck(configsEl,'hudson.plugins.parameterizedtrigger.BlockableBuildTriggerConfig')
        configs2El = self.addElementAfterCheck(blockableBuildTriggerConfigEl,'configs')
        configs2El.set('class','empty-list')
        projectsEl = self.addElementAfterCheck(blockableBuildTriggerConfigEl,'projects')
        projectsEl.text = runProject
        condition2El = self.addElementAfterCheck(blockableBuildTriggerConfigEl,'condition')
        condition2El.text = 'ALWAYS'
        triggerWithNoParametersEl = self.addElementAfterCheck(blockableBuildTriggerConfigEl,'triggerWithNoParameters')
        triggerWithNoParametersEl.text = 'false'
        buildAllNodesWithLabelEl = self.addElementAfterCheck(blockableBuildTriggerConfigEl,'buildAllNodesWithLabel')
        buildAllNodesWithLabelEl.text = 'false'

        runnerEl = self.addElementAfterCheck(singleStepConditionEl,'runner')
        runnerVersion = self.getPluginVersion('run-condition')
        runnerEl.set('class','org.jenkins_ci.plugins.run_condition.BuildStepRunner$Fail')
        runnerEl.set('plugin','run-condition@' + conditionVersion)

        self.configXml = et.tostring(rootEl)
        return True

    def setEmailNotification(self,recipients='',replyTo='',defaultContent='',trigger='always',defaultSubject=''):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        extendedEmailPublisherEl = self.addElementAfterCheck(publishersEl,'hudson.plugins.emailext.ExtendedEmailPublisher')
        emailPluginVersion = self.getPluginVersion('email-ext')
        extendedEmailPublisherEl.set('plugin','email-ext@' + emailPluginVersion)
        recipientListEl = self.addElementAfterCheck(extendedEmailPublisherEl,'recipientList')
        if len(recipients) > 0:
            recipientListEl.text = recipients
        else:
            recipientListEl.text = '$DEFAULT_RECIPIENTS'
        contentTypeEl = self.addElementAfterCheck(extendedEmailPublisherEl,'contentType')
        contentTypeEl.text = 'text/plain'
        defaultSubjectEl = self.addElementAfterCheck(extendedEmailPublisherEl,'defaultSubject')
        if len(defaultSubject) > 0:
            defaultSubjectEl.text = defaultSubject
        else:
            defaultSubjectEl.text = '$DEFAULT_SUBJECT'
        defaultContentEl = self.addElementAfterCheck(extendedEmailPublisherEl,'defaultContent')
        if len(defaultContent) > 0:
            defaultContentEl.text = defaultContent
        else:
            defaultContentEl.text = '$DEFAULT_CONTENT'
        attachmentsPatternEl = self.addElementAfterCheck(extendedEmailPublisherEl,'attachmentsPattern')
        presendScriptEl = self.addElementAfterCheck(extendedEmailPublisherEl,'presendScript')
        presendScriptEl.text = '$DEFAULT_PRESEND_SCRIPT'
        postsendScriptEl = self.addElementAfterCheck(extendedEmailPublisherEl,'postsendScript')
        postsendScriptEl.text = '$DEFAULT_POSTSEND_SCRIPT'
        attachBuildLogEl = self.addElementAfterCheck(extendedEmailPublisherEl,'attachBuildLog')
        attachBuildLogEl.text = 'false'
        compressBuildLogEl = self.addElementAfterCheck(extendedEmailPublisherEl,'compressBuildLog')
        compressBuildLogEl.text = 'false'
        replyToEl = self.addElementAfterCheck(extendedEmailPublisherEl,'replyTo')
        if len(replyTo) > 0:
            replyToEl.text = replyTo
        else:
            replyToEl.text = '$DEFAULT_REPLYTO'
        saveOutputEl = self.addElementAfterCheck(extendedEmailPublisherEl,'saveOutput')
        saveOutputEl.text = 'false'
        disabledEl = self.addElementAfterCheck(extendedEmailPublisherEl,'disabled')
        disabledEl.text = 'false'

        configuredTriggersEl = self.addElementAfterCheck(extendedEmailPublisherEl,'configuredTriggers')
        if trigger == 'always':
            triggerEl = self.addElementAfterCheck(configuredTriggersEl,'hudson.plugins.emailext.plugins.trigger.AlwaysTrigger')
        else:
            triggerEl = self.addElementAfterCheck(configuredTriggersEl,'hudson.plugins.emailext.plugins.trigger.AlwaysTrigger')
        emailEl = self.addElementAfterCheck(triggerEl,'email')
        recipientListSel = self.addElementAfterCheck(emailEl,'recipientList')
        subjectSel = self.addElementAfterCheck(emailEl,'subject')
        subjectSel.text = '$PROJECT_DEFAULT_SUBJECT'
        bodySel = self.addElementAfterCheck(emailEl,'body')
        bodySel.text = '$PROJECT_DEFAULT_CONTENT'
        attachmentsPatternSel = self.addElementAfterCheck(emailEl,'attachmentsPattern')
        attachBuildLogSel = self.addElementAfterCheck(emailEl,'attachBuildLog')
        attachBuildLogSel.text = 'false'
        compressBuildLogSel = self.addElementAfterCheck(emailEl,'compressBuildLog')
        compressBuildLogSel.text = 'false'
        replyToSel = self.addElementAfterCheck(emailEl,'replyTo')
        replyToSel.text = '$PROJECT_DEFAULT_REPLYTO'
        contentTypeSel = self.addElementAfterCheck(emailEl,'contentType')
        contentTypeSel.text = 'project'

        recipientProvidersSel = self.addElementAfterCheck(emailEl,'recipientProviders')
        developerRecipientProviderSel = self.addElementAfterCheck(recipientProvidersSel,'hudson.plugins.emailext.plugins.recipients.DevelopersRecipientProvider')
        listRecipientProviderSel = self.addElementAfterCheck(recipientProvidersSel,'hudson.plugins.emailext.plugins.recipients.ListRecipientProvider')

        self.configXml = et.tostring(rootEl)
        return True

    def setElementBooleanValue(self,parent,name,boolValue):
        element = self.addElementAfterCheck(parent,name)
        if boolValue:
            element.text = 'true'
        else:
            element.text = 'false'
        return element

    def setSlackNotification(self,channel='',url='',startNotification=False,notifySuccess=False,notifyAborted=False,notifyNotBuilt=False,notifyUnstable=False,notifyFailure=False,notifyBackToNormal=False,notifyRepeatedFailure=False):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        slackNotifierEl = self.addElementAfterCheck(publishersEl,'jenkins.plugins.slack.SlackNotifier')
        slackVersion = self.getPluginVersion('slack')
        slackNotifierEl.set('plugin','slack@' + slackVersion)
        teamDomainEl = self.addElementAfterCheck(slackNotifierEl,'teamDomain')
        authTokenEl = self.addElementAfterCheck(slackNotifierEl,'authToken')
        buildServerUrlEl = self.addElementAfterCheck(slackNotifierEl,'buildServerUrl')
        if len(url) > 0:
            buildServerUrlEl.text = url
        roomEl = self.addElementAfterCheck(slackNotifierEl,'room')
        if len(channel) > 0:
            roomEl.text = channel
        startNotificationEl = self.setElementBooleanValue(slackNotifierEl,'startNotification',startNotification)
        notifySuccessEl = self.setElementBooleanValue(slackNotifierEl,'notifySuccess',notifySuccess)
        notifyAbortedEl = self.setElementBooleanValue(slackNotifierEl,'notifyAborted',notifyAborted)
        notifyNotBuiltEl = self.setElementBooleanValue(slackNotifierEl,'notifyNotBuilt',notifyNotBuilt)
        notifyUnstableEl = self.setElementBooleanValue(slackNotifierEl,'notifyUnstable',notifyUnstable)
        notifyFailureEl = self.setElementBooleanValue(slackNotifierEl,'notifyFailure',notifyFailure)
        notifyBackToNormalEl = self.setElementBooleanValue(slackNotifierEl,'notifyBackToNormal',notifyBackToNormal)
        notifyRepeatedFailureEl = self.setElementBooleanValue(slackNotifierEl,'notifyRepeatedFailure',notifyRepeatedFailure)
        includeTestSummaryEl = self.addElementAfterCheck(slackNotifierEl,'includeTestSummary')
        includeTestSummaryEl.text = 'false'
        commitInfoChoiceEl = self.addElementAfterCheck(slackNotifierEl,'commitInfoChoice')
        commitInfoChoiceEl.text = 'NONE'
        includeCustomMessageEl = self.addElementAfterCheck(slackNotifierEl,'includeCustomMessage')
        includeCustomMessageEl.text = 'false'
        customMessageEl = self.addElementAfterCheck(slackNotifierEl,'customMessage')

        self.configXml = et.tostring(rootEl)
        return True

    def setPhaseJob(self,phaseName=None,jobName=None,killPhaseOn='FAILURE',buildOnScmChanges=False,disable=False,abortAllOtherJob=False,currentJobParameters=False,continuationCondition='ALWAYS'):
        if phaseName == None or jobName == None:
            return False

        #Update root from project to com.tikal.jenkins.plugins.multijob.MultiJobProject
        self.configXml = self.configXml.replace('<project>','<com.tikal.jenkins.plugins.multijob.MultiJobProject>')
        self.configXml = self.configXml.replace('</project>','</com.tikal.jenkins.plugins.multijob.MultiJobProject>')
        rootEl = et.fromstring(self.configXml)
        multijobPluginVersion = self.getPluginVersion('jenkins-multijob-plugin')
        rootEl.set('plugin','jenkins-multijob-plugin@' + multijobPluginVersion)
        blockBuildWhenDownstreamBuildingEl = self.setElementBooleanValue(rootEl,'blockBuildWhenDownstreamBuilding',False)
        pollSubjobsEl = self.setElementBooleanValue(rootEl,'pollSubjobs',False)

        buildersEl = self.addElementAfterCheck(rootEl,'builders')
        mulijobBuilderWithPhaseName = buildersEl.find(".//com.tikal.jenkins.plugins.multijob.MultiJobBuilder[phaseName='" + phaseName + "']")
        if mulijobBuilderWithPhaseName == None:
            multiJobBuilderEl = self.addElement(buildersEl,'com.tikal.jenkins.plugins.multijob.MultiJobBuilder')
        else:
            multiJobBuilderEl = mulijobBuilderWithPhaseName
        phaseNameEl = self.addElementAfterCheck(multiJobBuilderEl,'phaseName')
        phaseNameEl.text = phaseName
        phaseJobsEl = self.addElementAfterCheck(multiJobBuilderEl,'phaseJobs')

        phaseJobsConfigEl = self.addElement(phaseJobsEl,'com.tikal.jenkins.plugins.multijob.PhaseJobsConfig')
        jobNameEl = self.addElement(phaseJobsConfigEl,'jobName')
        jobNameEl.text = jobName
        currParamsEl = self.setElementBooleanValue(phaseJobsConfigEl,'currParams',currentJobParameters)
        exposedSCMEl = self.setElementBooleanValue(phaseJobsConfigEl,'exposedSCM',False)
        disableJobEl = self.setElementBooleanValue(phaseJobsConfigEl,'disableJob',disable)
        parsingRulesPathEl = self.addElement(phaseJobsConfigEl,'parsingRulesPath')
        maxRetriesEl = self.addElement(phaseJobsConfigEl,'maxRetries')
        maxRetriesEl.text = '0'
        enableRetryStrategyEl = self.setElementBooleanValue(phaseJobsConfigEl,'enableRetryStrategy',False)
        enableConditionEl = self.setElementBooleanValue(phaseJobsConfigEl,'enableCondition',False)
        abortAllJobEl = self.setElementBooleanValue(phaseJobsConfigEl,'abortAllJob',abortAllOtherJob)
        conditionEl = self.addElement(phaseJobsConfigEl,'condition')
        configsEl = self.addElement(phaseJobsConfigEl,'configs')
        configsEl.set('class','empty-list')
        killPhaseOnJobResultConditionEl = self.addElement(phaseJobsConfigEl,'killPhaseOnJobResultCondition')
        killPhaseOnJobResultConditionEl.text = killPhaseOn
        buildOnlyIfSCMChangesEl = self.setElementBooleanValue(phaseJobsConfigEl,'buildOnlyIfSCMChanges',buildOnScmChanges)
        applyConditionOnlyIfNoSCMChangesEl = self.setElementBooleanValue(phaseJobsConfigEl,'applyConditionOnlyIfNoSCMChanges',False)

        continuationConditionEl = self.addElementAfterCheck(multiJobBuilderEl,'continuationCondition')
        continuationConditionEl.text = continuationCondition

        self.configXml = et.tostring(rootEl)
        return True

    def setWorkspaceCleanup(self,include='',deleteDirs=False,externalDelete=''):
        rootEl = et.fromstring(self.configXml)

        buildWrappersEl = self.addElementAfterCheck(rootEl,'buildWrappers')
        preBuildCleanupEl = self.addElementAfterCheck(buildWrappersEl,'hudson.plugins.ws__cleanup.PreBuildCleanup')
        wsCleanupVersion = self.getPluginVersion('ws-cleanup')
        preBuildCleanupEl.set('plugin','ws-cleanup@' + wsCleanupVersion)

        patternsEl = self.addElementAfterCheck(preBuildCleanupEl,'patterns')
        if len(include) > 0:
            cleanupPatternEl = self.addElementAfterCheck(patternsEl,'hudson.plugins.ws__cleanup.Pattern')
            patternEl = self.addElementAfterCheck(cleanupPatternEl,'pattern')
            patternEl.text = include
            typeEl = self.addElementAfterCheck(cleanupPatternEl,'type')
            typeEl.text = 'INCLUDE'
        deleteDirsEl = self.setElementBooleanValue(preBuildCleanupEl,'deleteDirs',deleteDirs)
        cleanupParameterEl = self.addElementAfterCheck(preBuildCleanupEl,'cleanupParameter')
        if len(externalDelete) > 0:
            externalDeleteEl = self.addElementAfterCheck(preBuildCleanupEl,'externalDelete')
            externalDeleteEl.text = externalDelete
            
        self.configXml = et.tostring(rootEl)
        return True

    def setPostBuildBuildTrigger(self,projects='',trigger='ALWAYS',withoutParameters=False):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        buildTriggerEl = self.addElementAfterCheck(publishersEl,'hudson.plugins.parameterizedtrigger.BuildTrigger')
        buildTriggerVersion = self.getPluginVersion('parameterized-trigger')
        buildTriggerEl.set('plugin','parameterized-trigger@' + buildTriggerVersion)
        configsEl = self.addElementAfterCheck(buildTriggerEl,'configs')
        buildTriggerConfigEl = self.addElementAfterCheck(configsEl,'hudson.plugins.parameterizedtrigger.BuildTriggerConfig')
        configsClassEl = self.addElementAfterCheck(buildTriggerConfigEl,'configs')
        configsClassEl.set('class','empty-list')
        projectsEl = self.addElementAfterCheck(buildTriggerConfigEl,'projects')
        projectsEl.text = projects
        conditionEl = self.addElementAfterCheck(buildTriggerConfigEl,'condition')
        conditionEl.text = trigger
        triggerWithNoParametersEl = self.setElementBooleanValue(buildTriggerConfigEl,'triggerWithNoParameters',withoutParameters)
            
        self.configXml = et.tostring(rootEl)
        return True

    def setPostBuildJunitTestResultReport(self,xmlReportFiles=''):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        jUnitTestResultArchiverEl = self.addElementAfterCheck(publishersEl,'hudson.tasks.junit.JUnitResultArchiver')
        jUnitTestResultVersion = self.getPluginVersion('junit')
        jUnitTestResultArchiverEl.set('plugin','junit@' + jUnitTestResultVersion)
        testResultsEl = self.addElementAfterCheck(jUnitTestResultArchiverEl,'testResults')
        testResultsEl.text = xmlReportFiles
        keepLongStdioEl = self.setElementBooleanValue(jUnitTestResultArchiverEl,'keepLongStdio',False)
        healthScaleFactorEl = self.addElementAfterCheck(jUnitTestResultArchiverEl,'healthScaleFactor')
        healthScaleFactorEl.text = '1.0'
        allowEmptyResultsEl = self.setElementBooleanValue(jUnitTestResultArchiverEl,'allowEmptyResults',False)

        self.configXml = et.tostring(rootEl)
        return True

    def setPostBuildCucumberTestResultReport(self,jsonReportFiles='',ignoreBadSteps=False):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        cucumberTestResultArchiverEl = self.addElementAfterCheck(publishersEl,'org.jenkinsci.plugins.cucumber.jsontestsupport.CucumberTestResultArchiver')
        cucumberTestResultVersion = self.getPluginVersion('cucumber-testresult-plugin')
        cucumberTestResultArchiverEl.set('plugin','cucumber-testresult-plugin@' + cucumberTestResultVersion)
        testResultsEl = self.addElementAfterCheck(cucumberTestResultArchiverEl,'testResults')
        testResultsEl.text = jsonReportFiles
        ignoreBadStepsEl = self.setElementBooleanValue(cucumberTestResultArchiverEl,'ignoreBadSteps',ignoreBadSteps)

        self.configXml = et.tostring(rootEl)
        return True

    def setPostBuildGroovy(self,script=''):
        rootEl = et.fromstring(self.configXml)

        publishersEl = self.addElementAfterCheck(rootEl,'publishers')
        groovyPostbuildRecorderEl = self.addElementAfterCheck(publishersEl,'org.jvnet.hudson.plugins.groovypostbuild.GroovyPostbuildRecorder')
        groovyPostbuildVersion = self.getPluginVersion('groovy-postbuild')
        groovyPostbuildRecorderEl.set('plugin','groovy-postbuild@' + groovyPostbuildVersion)

        scriptSecurityEl = self.addElementAfterCheck(groovyPostbuildRecorderEl,'script')
        scriptSecurityVersion = self.getPluginVersion('script-security')
        scriptSecurityEl.set('plugin','script-security@' + scriptSecurityVersion)

        scriptEl = self.addElementAfterCheck(scriptSecurityEl,'script')
        scriptEl.text = script
        sandboxEl = self.setElementBooleanValue(scriptSecurityEl,'sandbox',False)

        behaviorEl = self.addElementAfterCheck(groovyPostbuildRecorderEl,'behavior')
        behaviorEl.text = '0'
        runFormatrixParentEl = self.setElementBooleanValue(groovyPostbuildRecorderEl,'runFormatrixParent',False)
            
        self.configXml = et.tostring(rootEl)
        return True

    def delImmediateElement(self,parent,searchChildName,name,value):
        findElements = './/' + searchChildName
        elements = parent.findall(findElements)
        if findElements == None or len(findElements) == 0:
            print 'Search child not found'
            return True
        for elem in elements: 
            print et.tostring(elem)
            tagEl = elem.find(name)
            if tagEl is not None and tagEl.text == value:
                print 'Found child...Deleting [%s]' % searchChildName
                parent.remove(elem)
                continue
        return True

    def delTreeElement(self,parent,removeChildName,searchChildName,name,value):
        findRemoveElements = './/' + removeChildName
        removeElements = parent.findall(findRemoveElements)
        if removeElements == None or len(removeElements) == 0:
            print 'Remove child not found'
            return True
        findElements = './/' + searchChildName
        for rElem in removeElements: 
            elements = rElem.findall(findElements)
            if findElements == None or len(findElements) == 0:
                print 'Search child not found'
                continue
            for elem in elements: 
                print et.tostring(elem)
                tagEl = elem.find(name)
                if tagEl is not None and tagEl.text == value:
                    print 'Found child...Deleting [%s]' % removeChildName
                    parent.remove(rElem)
                    continue
        return True

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
        if self.server.job_exists(self.name):
            print self.server.get_job_info(self.name)
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
        if self.server.job_exists(self.name):
            print 'Print Job [%s] Config' % self.name
            print et.tostring(et.fromstring(self.configXml))
        return True

    def printJobs(self):
        if self.server == None:
            return False
        jobs = self.server.get_jobs()
        for job in jobs:
            print 'Job [%s]' % job['name']
        return True

    def cleanLoad(self):
        status = True
        if self.server ==  None:
            return False
        if not self.server.job_exists(self.name):
            if 'multijob_phases' in self.jobJson:
                self.create(jobType='multijob')
            else:
                self.create()
        self.printConfig()

        #Start clean to do proper reload
        self.configXml = jenkins.EMPTY_CONFIG_XML.strip()
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.XML(self.configXml,parser)
        indentedConfigString = etree.tostring(root,pretty_print=True)
        self.configXml = et.tostring(et.fromstring(indentedConfigString))

        if 'description' in self.jobJson:
            self.setDescription(self.jobJson['description'])
        if 'max_builds_keep' in self.jobJson:
            self.setBuildCleanup(self.jobJson['max_builds_keep'])
        if 'parameters' in self.jobJson:
            parameters = self.jobJson['parameters']
            for param in parameters.keys():
                pValue = ''
                if 'value' in parameters[param]:
                    pValue = parameters[param]['value']
                pType = ''
                if 'type' in parameters[param]:
                    pType = parameters[param]['type']
                pDesc = ''
                if 'description' in parameters[param]:
                    pDesc = parameters[param]['description']
                if pType == 'string':
                    self.setParameter(param,pValue,pDesc,string=True)
                elif pType == 'boolean':
                    self.setParameter(param,pValue,pDesc,boolean=True)
                elif pType == 'password':
                    #Obtain value
                    if self.jobCredJson is not None and param in self.jobCredJson:
                        pValue = self.jobCredJson[param]
                    else:
                        print 'Failed to obtain credentials for %s' % (param)
                        exit(1)
                    self.setParameter(param,pValue,pDesc,password=True)
        if 'git' in self.jobJson:
            git = self.jobJson['git']
            cleanBeforeCheckout = ''
            if 'clean_before_checkout' in git:
                cleanBeforeCheckout = git['clean_before_checkout']
            repos = {}
            if 'repos' in git:
                repos = git['repos']
            for repo in repos.keys():
                branch = ''
                if 'branch' in repos[repo]:
                    branch = repos[repo]['branch']
                user = ''
                if 'user' in repos[repo]:
                    user = repos[repo]['user']
                local_branch = False
                if 'local_branch' in repos[repo] and repos[repo]['local_branch'] == 'yes':
                    local_branch = True
                self.setGit(repo,branch,user,local_branch=local_branch)
        if 'environment_passwords' in self.jobJson:
            envPasswords = self.jobJson['environment_passwords']
            if 'parameters' in envPasswords:
                parameters = envPasswords['parameters']
                for param in parameters.keys():
                    pValue = ''
                    #Obtain value
                    if self.jobCredJson is not None and param in self.jobCredJson:
                        pValue = self.jobCredJson[param]
                    else:
                        print 'Failed to obtain credentials for %s' % (param)
                        exit(1)
                    self.setGlobalPasswords(param,pValue)
        if 'execute_groovy' in self.jobJson:
            exeGroovy = self.jobJson['execute_groovy']
            scriptFile = ''
            if 'script_file' in exeGroovy:
                scriptFile = exeGroovy['script_file']
            script = ''
            if 'script' in exeGroovy:
                script = exeGroovy['script']
            self.setExecGroovyScript(scriptFile,script)
        #Order Matters -- starting here
        if 'execute_shell' in self.jobJson:
            self.setExecShellScript(self.jobJson['execute_shell'])
        if 'environment_variables' in self.jobJson:
            envVariables = self.jobJson['environment_variables']
            filePath = ''
            if 'file_path' in envVariables:
                filePath = envVariables['file_path']
            content = ''
            if 'content' in envVariables:
                content = envVariables['content']
            self.setEnvironmentVariables(filePath=filePath,content=content)
        if 'conditional_step' in self.jobJson:
            conditionalStep = self.jobJson['conditional_step']
            fileName = ''
            if 'file_exists' in conditionalStep:
                fileName = conditionalStep['file_exists']
            runProject = ''
            if 'run_project' in conditionalStep:
                runProject = conditionalStep['run_project']
            self.setConditionalStep(fileName,runProject)
        if 'gradle' in self.jobJson:
            gradle = self.jobJson['gradle']
            wrapper = False
            if 'wrapper' in gradle and gradle['wrapper'] == 'yes':
                wrapper = True
            executableGradlew = False
            if 'executable_gradlew' in gradle and gradle['executable_gradlew'] == 'yes':
                executableGradlew = True
            fromRootBuildScriptDir = False
            if 'from_root_build_script_dir' in gradle and gradle['from_root_build_script_dir'] == 'yes':
                fromRootBuildScriptDir = True
            description = ''
            if 'build_step_description' in gradle:
                description = gradle['build_step_description']
            switches = ''
            if 'switches' in gradle:
                switches = gradle['switches']
            tasks = ''
            if 'tasks' in gradle:
                tasks = gradle['tasks']
            rootBuildScript = ''
            if 'root_build_script' in gradle:
                rootBuildScript = gradle['root_build_script']
            buildFile = ''
            if 'build_file' in gradle:
                buildFile = gradle['build_file']
            useWorkspace = False
            if 'use_workspace' in gradle and gradle['use_workspace'] == 'yes':
                useWorkspace = True
            passParamsAsGradleProperties = False
            if 'pass_params_as_gradle_properties' in gradle and gradle['pass_params_as_gradle_properties'] == 'yes':
                passParamsAsGradleProperties = True
            self.setGradleScript(wrapper=wrapper,executableGradlew=executableGradlew,fromRootBuildScriptDir=fromRootBuildScriptDir,description=description,switches=switches,tasks=tasks,rootBuildScript=rootBuildScript,buildFile=buildFile,useWorkspace=useWorkspace,passParamsAsGradleProperties=passParamsAsGradleProperties)
        if 'multijob_phases' in self.jobJson:
            phases = self.jobJson['multijob_phases']
            for phase in phases:
                phaseName = None
                if 'phase_name' in phase:
                    phaseName = phase['phase_name']
                continuationCondition = 'ALWAYS'
                if 'continuation_condition' in phase:
                    continuationCondition = phase['continuation_condition']
                jobs = None
                if 'phase_jobs' in phase:
                    jobs = phase['phase_jobs']
                for job in jobs:
                    name = None
                    if 'job_name' in job:
                        name = job['job_name']
                    killPhaseOn = 'FAILURE'
                    if 'kill_phase_on' in job:
                        killPhaseOn = job['kill_phase_on']
                    buildOnScmChanges = False
                    if 'build_on_scm_changes' in job and job['build_on_scm_changes'] == 'yes':
                        buildOnScmChanges = True
                    disable = False
                    if 'disable' in job and job['disable'] == 'yes':
                        disable = True
                    abortAllOtherJob = False
                    if 'abort_all_other_job' in job and job['abort_all_other_job'] == 'yes':
                        abortAllOtherJob = True
                    currentJobParameters = False
                    if 'current_job_parameters' in job and job['current_job_parameters'] == 'yes':
                        currentJobParameters = True
                    self.setPhaseJob(phaseName=phaseName,jobName=name,killPhaseOn=killPhaseOn,buildOnScmChanges=buildOnScmChanges,disable=disable,abortAllOtherJob=abortAllOtherJob,currentJobParameters=currentJobParameters,continuationCondition=continuationCondition)
        if 'execute_cleanup_shell' in self.jobJson:
            self.setExecShellScript(self.jobJson['execute_cleanup_shell'])
        if 'cleanup_environment_variables' in self.jobJson:
            envVariables = self.jobJson['cleanup_environment_variables']
            filePath = ''
            if 'file_path' in envVariables:
                filePath = envVariables['file_path']
            content = ''
            if 'content' in envVariables:
                content = envVariables['content']
            self.setEnvironmentVariables(filePath=filePath,content=content)
        #Order Matters -- stopping here
        if 'dsl' in self.jobJson:
            dsl = self.jobJson['dsl']
            scriptFile = ''
            if 'scripts' in dsl:
                scripts = dsl['scripts']
            if len(scripts) > 0:
                self.setJobDsl(scripts)
        if 'timestamp' in self.jobJson:
            timestampPattern = self.jobJson['timestamp']
            if len(timestampPattern) > 0:
                self.setTimestamp(timestampPattern)
        if 'periodic_build' in self.jobJson:
            self.setPeriodicBuild(self.jobJson['periodic_build'])
        if 'slave' in self.jobJson:
            self.setSlave(self.jobJson['slave'])
        if 'postbuild_groovy' in self.jobJson:
            postBuildGroovy = self.jobJson['postbuild_groovy']
            script = ''
            if 'script' in postBuildGroovy:
                script = postBuildGroovy['script']
            self.setPostBuildGroovy(script=script)
        if 'email_notification' in self.jobJson:
            emailNotification = self.jobJson['email_notification']
            recipients = ''
            if 'recipients' in emailNotification:
                recipients = emailNotification['recipients']
            replyTo = ''
            if 'reply_to' in emailNotification:
                replyTo = emailNotification['reply_to']
            content = ''
            if 'content' in emailNotification:
                content = emailNotification['content']
            trigger = 'always'
            if 'trigger_always' in emailNotification:
                trigger = 'always'
            subject = ''
            if 'subject' in emailNotification:
                subject = emailNotification['subject']
            self.setEmailNotification(recipients=recipients,replyTo=replyTo,defaultContent=content,trigger=trigger,defaultSubject=subject)
        if 'slack_notification' in self.jobJson:
            slackNotification = self.jobJson['slack_notification']
            channel = ''
            if 'channel' in slackNotification:
                channel = slackNotification['channel']
            url = ''
            if 'url' in slackNotification:
                url = slackNotification['url']
            start = False
            if 'start' in slackNotification and slackNotification['start'] == 'yes':
                start = True
            success = False
            if 'success' in slackNotification and slackNotification['success'] == 'yes':
                success = True
            aborted = False
            if 'aborted' in slackNotification and slackNotification['aborted'] == 'yes':
                aborted = True
            not_built = False
            if 'not_built' in slackNotification and slackNotification['not_built'] == 'yes':
                not_built = True
            unstable = False
            if 'unstable' in slackNotification and slackNotification['unstable'] == 'yes':
                unstable = True
            failure = False
            if 'failure' in slackNotification and slackNotification['failure'] == 'yes':
                failure = True
            back_to_normal = False
            if 'back_to_normal' in slackNotification and slackNotification['back_to_normal'] == 'yes':
                back_to_normal = True
            repeated_failure = False
            if 'repeated_failure' in slackNotification and slackNotification['repeated_failure'] == 'yes':
                repeated_failure = True
            self.setSlackNotification(
                    channel=channel,
                    url=url,
                    startNotification=start,
                    notifySuccess=success,
                    notifyAborted=aborted,
                    notifyNotBuilt=not_built,
                    notifyUnstable=unstable,
                    notifyFailure=failure,
                    notifyBackToNormal=back_to_normal,
                    notifyRepeatedFailure=repeated_failure
                    )
        if 'postbuild_build_trigger' in self.jobJson:
            buildTrigger = self.jobJson['postbuild_build_trigger']
            projects = ''
            if 'projects' in buildTrigger:
                projects = buildTrigger['projects']
            trigger = 'ALWAYS'
            if 'trigger' in buildTrigger:
                trigger = buildTrigger['trigger']
            withoutParameters = False
            if 'without_parameters' in buildTrigger and buildTrigger['without_parameters'] == 'yes':
                withoutParameters = True
            self.setPostBuildBuildTrigger(projects=projects,trigger=trigger,withoutParameters=withoutParameters)
        if 'postbuild_cucumber_test_result_report' in self.jobJson:
            cucumberTestResultReport = self.jobJson['postbuild_cucumber_test_result_report']
            jsonReportFiles = ''
            if 'json_report_files' in cucumberTestResultReport:
                jsonReportFiles = cucumberTestResultReport['json_report_files']
            ignoreBadSteps = False
            if 'ignore_bad_steps' in cucumberTestResultReport and cucumberTestResultReport['ignore_bad_steps'] == 'yes':
                ignoreBadSteps = True
            self.setPostBuildCucumberTestResultReport(jsonReportFiles=jsonReportFiles,ignoreBadSteps=ignoreBadSteps)
        if 'postbuild_junit_test_result_report' in self.jobJson:
            junitTestResultReport = self.jobJson['postbuild_junit_test_result_report']
            xmlReportFiles = ''
            if 'xml_report_files' in junitTestResultReport:
                xmlReportFiles = junitTestResultReport['xml_report_files']
            self.setPostBuildJunitTestResultReport(xmlReportFiles=xmlReportFiles)
        if 'workspace_cleanup' in self.jobJson:
            workspaceCleanup = self.jobJson['workspace_cleanup']
            include = ''
            if 'include' in workspaceCleanup:
                include = workspaceCleanup['include']
            externalDelete = ''
            if 'external_delete' in workspaceCleanup:
                externalDelete = workspaceCleanup['external_delete']
            deleteDirs = False
            if 'delete_directories' in workspaceCleanup and workspaceCleanup['delete_directories'] == 'yes':
                deleteDirs = True
            self.setWorkspaceCleanup(include=include,deleteDirs=deleteDirs,externalDelete=externalDelete)
        if 'views' in self.jobJson:
            views = self.jobJson['views']
            for aView in views:
                jView = cView(aView,connection=self.server)
                jView.create()
                jView.addJob(self.name)
        self.update()
        self.printConfig()

    def action(self,action):
        if action == 'delete':
            self.delete()
        elif action == 'reload':
            self.cleanLoad()
        elif action == 'show':
            self.printConfig()
        elif action == 'build':
            self.build()
        elif action == 'last_successful_build':
            self.lastSuccessfulBuild()
        elif action == 'last_build_status':
            self.lastBuildStatus()
        elif action == 'monitor':
            self.monitor()
        else:
            print 'Invalid Action [%s]' % (action)
