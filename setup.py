#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Tra NGUYEN THANH <thanh-tra.nguyen@esrf.fr>'
__version__ = '1.2'
__adv__ = 'setup.py'


import os, sys, glob
#sys.argv.append('bdist_wininst')
from distutils.core import setup
from distutils.command.install_data import install_data
from set_path import main as post_install

class after_installation(install_data):
	def run(self):
		install_data.run(self)
		post_install()

if __name__=="__main__":
	# Package name
	name = 'OceanDAC'

	# Packages (subdirectories in lib/)
	packages = [name]
	data_files = [(name, ["NEON_LINES.dat", "OceanDAC.ico"])]
	# Scripts (in scripts/)
	scripts = ['OceanDAC.py']

	command_options = {}


	setup(name=name,
		  version = __version__,
		  description='OceanDAC software for high pressure measurement in Diamond Anvil Cell experiment using Ruby/Samarium luminescence. This software is used with Ocean Optics spectrometer.',
		  author='Tra NGUYEN THANH',
		  author_email='thanh-tra.nguyen@esrf.fr',
		  maintainer="Tra NGUYEN",
		  maintainer_email='thanh-tra.nguyen@esrf.fr',
		  url='http://www.esrf.fr/',
		  license="GNU General Public FREE SOFTWARE LICENSE",
		  packages=packages,
		  data_files = data_files,
		  scripts=['scripts/'+script for script in scripts],
		  zip_safe = False,
		  cmdclass = {"install": after_installation},
		  command_options=command_options
		  )
