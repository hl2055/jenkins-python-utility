#!/usr/bin/python

import sys
import json
import os
import collections
import datetime
from dateutil.parser import parse
import logging
import argparse

logging.basicConfig(filename='test.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

class cLogAnalysis:
	def __init__(self,directory):
		self.logFiles = []
		self.newLog = ''
		self.startTime = ''
		self.UpdateLine = 0
		path = os.path.dirname(os.path.realpath(__file__))
		filepath = path + '/whiteList.json'
		data = open(filepath).read()
		strJson = json.loads(data,object_pairs_hook=collections.OrderedDict)
		self.whiteList = strJson['false_errors']
		for file in os.listdir(directory):
			if file.endswith("log"):
				logger.debug('The file is %s: ', file)
				logger.debug('The location is %s',directory)
				self.logFiles.append(directory + '/'+file)
				if 'update.log' in file:
					logger.debug('got into update.log')
					for lineNum,line in enumerate(reversed(open(directory + '/' +file).readlines()),1):
						if 'Update has been signalled' in line:
							now = datetime.datetime.now()
							self.startTime = datetime.datetime.strptime(str(now.year) + ' ' + line[:15],"%Y %b %d %H:%M:%S")
							self.UpdateLine = lineNum
							logger.debug('Start time is: %s found at %d' , str(self.startTime),self.UpdateLine)
							break

	def writeLog(self,log,logFileName):
		if os.path.exists(logFileName):	
			self.newLog = open(logFileName,"rw+")
			self.newLog.write(log)
			self.newLog.close()
		else:
			self.newLog = open(logFileName,"w+")
			self.newLog.write(log)
			self.newLog.close()
		return True

	def timeConvert(self,timeStr):
		try:
			return parse(timeStr)
		except ValueError:
			return False

	def findStartLine(self,file):
		if self.startTime == '':
			return False

		logger.info('Time passed in was: %s', self.startTime)
		if type(self.startTime) is not (datetime.datetime):
			try:
				datetime.datetime.strptime(self.startTime,"%b %d %H:%M:%S")
			except ValueError:
				logger.error("ERROR: Incorrect date format",exec_info=True)

		with open(file) as log:
			for lineNum,line in enumerate(log,1):
				logger.debug('Line: %d says %s',lineNum,line)
				logger.debug(line[line.find("[")+1:line.find("]")])
				if line[line.find("[")+1:line.find("]")] == str(self.startTime):
					newLine = line[line.find("[")+1:line.find("]")]
					properDate = self.timeConvert(newLine)
					if properDate is not False:
						logger.debug('Comparison between: %s and %s', str(self.startTime),str(properDate))
						#properDate = datetime.datetime.strptime(properDate,"%b %d %H:%M:%S")
						if  properDate >= self.startTime:
							return lineNum

				elif line.startswith(' Time:'):
					date = line.split(': ')
					logger.debug('Date after split: %s',date)
					brokenDate = date.split(' ')
					properDate = brokenDate[1] + ' ' + brokenDate[2]+ ' ' +brokenDate[3]
					properDate = self.timeConvert(properDate)
					if properDate is not False:
						logger.debug('Comparison between: %s and %s', str(self.startTime),str(properDate))

						if properDate >= self.startTime:
							return lineNum
				else:
					if line[0].isdigit() is True:
						newLine = line.split(' ')
						if len(newLine) > 3:
							logger.debug('Before: ' + str(newLine))
							fullDate = newLine[0]
							newTime = newLine[1]
							if '-' in fullDate:
								fullDate = fullDate.split('-')
								monthAndTime = fullDate[1] + ' ' + fullDate[2]
								newTime = newTime.split('.')
								properDate = monthAndTime + ' ' + newTime[0]
								properDate = self.timeConvert(properDate)
								if properDate is not False:
									logger.debug('After: ' + str(properDate))
									logger.debug('Comparison between: %s and %s', str(self.startTime),str(properDate))

									if properDate >= self.startTime:
										return lineNum

					else:
						newLine = line[:15]
						properDate = self.timeConvert(newLine)
						if properDate is not False:
							#properDate = datetime.datetime.strptime(properDate,"%b %d %H:%M:%S")
							logger.debug(properDate)
							logger.debug('Comparison between: %s and %s', str(self.startTime),str(properDate))
							if properDate >= self.startTime:
								return lineNum


		return False

	def getLogFromLine(self,file,line):
		if 'update.log' in file:
			with open(file) as logFile:
				lines = logFile.readlines()
				length = len(lines)
				logger.debug('Length of file is %d',length)
				startLine = length - self.UpdateLine
				logger.debug('start line is at %d',startLine)
				log = lines[startLine:]
				logger.debug('Length of the remaining log is %d',len(log))
				return log
		
		else:

			with open(file) as logFile:
				if line is not False:
					log = logFile.readlines()[line:]
				else:
					log = logFile.readlines()
				return log

		return False

	def getErrors(self,file):

		startLine = self.findStartLine(file)
		logger.debug('Start Line returns ' + str(startLine))
		newLog = ''
		log = self.getLogFromLine(file,startLine)
		if log is not False:
			errorCount = 0
			warningCount = 0
			for line in log:
				if ("error" in line.lower()) or ("critical" in line.lower()) or ("fatal" in line.lower()) or (" failure " in line.lower()) or ("failed" in line.lower()):
					false_positive = False
					logger.debug('In the if statement')
					logger.debug('json dump: %s',self.whiteList)
					logger.debug('File is: %s', file)
					filename = file.split('/')[-1]
					filename = filename.strip()
					logger.debug('Filename is: %s',filename) 
					for fileCheck in self.whiteList:
						if fileCheck in filename:
							logger.debug('In the next if statement')
							whitelist = self.whiteList[fileCheck]
							logger.debug(type(whitelist))
							if type(whitelist) is list:
								for case in whitelist:
									logger.debug('case is: %s',case)
									if case.lower() in line.lower():
										logger.debug('False Positive line is: %s',line)
										false_positive = True
										break
									else:
										false_positive = False
					if false_positive is False:
						logger.debug('Error line is: %s',line)
						newLog = newLog + 'ERROR -- ' + line
						errorCount = errorCount + 1
				elif "warning" in line.lower() or "warn" in line.lower():
					logger.debug('Warning line is: %s',line)
					newLog = newLog + 'WARNING -- ' + line
					warningCount = warningCount + 1
				else:
					newLog = newLog + line

			newLog = newLog + '\n' + 'Errors in Log: ' + str(errorCount) + '\n' + 'Warnings in Log: ' + str(warningCount) + '\n'
			newLog = str('		===================== Start of '+ file +' =====================		') + '\n' + newLog + '\n'
			newLog = newLog +  str('		===================== End of ' + file + ' =======================		') + '\n\n\n'
			return newLog,errorCount
		else:
			return False

	def combineLogs(self,newLogFile):

		errors = 0
		if self.logFiles is not []:
			for file in self.logFiles:
				tempLog, tempErrors = self.getErrors(file)

				if tempLog is not False:
					errors = errors + tempErrors
					self.newLog = self.newLog + tempLog
				else:
					return False
			self.newLog = self.newLog + 'ERRORS: ' + str(errors) + '\n'
			check = self.writeLog(self.newLog,newLogFile)
			if check is True:
				if errors == 0:
					return True
				else:
					return False

			else:
				return False


def LogAnalyzer(directory,file,newLogFileName,action):

	if directory is None and file is None:
		print 'ERROR: No directory provided'

	if newLogFileName is None:
		print 'ERROR: New log file name must be provided'

	if file is not None and directory is None:
		directory = os.path.dirname(os.path.realpath(file))
		analyzer = cLogAnalysis(directory)
		if action == 'get_errors':
			log = analyzer.getErrors(file,startTime)
			if log is not False:
				check = self.writeLog(log,newLogFileName)
				if check is False:
					print 'FAILED'
				else:
					print 'SUCCESS'
		elif action == 'get_start_line':
			line = analyzer(file,startTime)
			if line is not False:
				print line
	else:	
		logAnalysis = cLogAnalysis(directory)
		check = logAnalysis.combineLogs(newLogFileName) 
		if check is not False:
			print 'SUCCESS'
		else:
			print 'FAILED'

if __name__ == '__main__':
	
	parser = argparse.ArgumentParser(description='Log Analysis Utility Control')

	parser.add_argument('-d','--directory',nargs=1,type=str,help='directory containing the log files to be analyzed')
	parser.add_argument('-f','--file',nargs=1,type=str,help='log file to be analyzed')
	parser.add_argument('-n','--newfile',nargs=1,type=str,help='Name of the new log file to be created')
	
	parser.add_argument('-a','--action',nargs=1,type=str,help='The action to be performed on a single file')

	args = parser.parse_args()
	aDir = None
	aFile = None
	aNewFile = None

	aAction = None

	if args.file is not None:
		aFile = args.file[0]
	if args.directory is not None:
		aDir = args.directory[0]
	if args.newfile is not None:
		aNewFile = args.newfile[0]
	if args.action is not None:
		aAction = args.action[0]

	LogAnalyzer(aDir,aFile,aNewFile,aAction)





