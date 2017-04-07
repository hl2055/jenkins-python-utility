#!/usr/bin/python

import json
import collections
import sys
import os
import requests
import urllib2

class cRestfulCall:
	def __init__(self):

		self.apiBase = 'http://jenkins.bluecatnetworks.corp/buildapi/v1/' 


	def baseCall(self,release,product,prop,name,returnType):

		if release is None or product is None or prop is None or name is None:
			return False

		call = self.apiBase + product + '/' + release + '/' + prop +'/' + name
		check = self.testConnection(call)
		
		if check is False:
			return False
		else:
			req = requests.get(call)

			if returnType is 'json':
				return req.json
			elif returnType is 'text':
				return req.text
			elif returnType is 'raw':
				return req.raw
			else:
				return False

	def testConnection(self,address):

		resp = urllib2.urlopen(address,timeout=1)
		if resp.getcode() == 200:
			return True
		else:
			return False

	def deliveryTypeCall(self,release):
		call = self.apiBase + '/' + release + '/delivery_type'

		check = self.testConnection(call)

		if check is False:
			return False

		response = requests.get(call)

		return response.text


	def pathCall(self,release,product):

		response = self.baseCall(release,product,'storage_path','all','text')

		if response is False:
			return False

		paths = response.split('\n')

		return paths[0]

	def ftpServerCall(self,release,product):

		response = self.baseCall(release,product,'storage_server','all','text')

		if response is False:
			return False

		server = response.split('\n')

		return server[0]

	def ftpDownloadUserCall(self,release,product):

		response = self.baseCall(release,product,'storage_download_user','all','text')

		if response is False:
			return False

		download_user = response.split('\n')

		return download_user[0]

	
if __name__ == '__main__':
	
	rest = cRestfulCall()
	print rest.deliveryTypeCall('8.1.1')
	print rest.pathCall('8.1.1','bam')
	print rest.ftpServerCall('8.1.1','bam')
	print rest.ftpDownloadUserCall('8.1.1','bam')
	print rest.baseCall('8.1.1','bam','fullname','upgrade','text')




