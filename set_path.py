#!/usr/bin/python
# -*- coding: utf-8 -*-
import os, sys
from os import listdir
from os.path import join

java_home = "JAVA_HOME"
java_home_path = "C:\Program Files (x86)\Java"

try:
	java = listdir(java_home_path)
	has_java = True
except:
	has_java = False
	
if has_java:
	jv_installed = [j for j in java if j.startswith("jdk")]
	jv_installed = sorted(jv_installed, reverse=True)
	used_jv      = jv_installed[0]
	jv_path      = join(java_home_path, used_jv)
	cmd1 = 'setx %s "%s"'%(java_home, jv_path)
	print cmd1
	os.system(cmd1)
	path_variable = jv_path+"\\jre\\bin\\server;"
	cmd2 = 'setx Path "%%Path%%;%s"'%path_variable
	print cmd2
	os.system(cmd2)
	path_variable = jv_path+"\\bin"
	cmd3 = 'setx Path "%%Path%%;%s"'%path_variable
	print cmd3
	os.system(cmd3)

else:
	print "You don't have java JDK installed. Please download and install it. The version SE JDK 1.8.0 build 66 is good."