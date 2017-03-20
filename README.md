<img src="https://github.com/Traecp/OceanDAC/blob/master/OceanDAC_v1.2_monitoring.png">

OceanDAC is a software which communicates with Ocean Optics spectrometer in order to read luminescence spectra of Ruby or Samarium to measure pressure in Diamond Anvil Cell.
The current version is 2.0, last update: 17/03/2017

++ CAUTION: This program is not intended to be used under Linux. For the moment it only supports Windows users, because I don't have a chance to test it on Linux.

INSTALLATION PREREQUISITE:
==========================
+ Java SE JDK (the version 1.8.0_121 is used when writing this software);
+ OceanOptics OmniDriver;
+ Anaconda for Python 2.7
+ PyQt4 (with Anaconda installed: open a command prompt window and type: conda install pyqt=4)
If you use the 32bit version of Python (such as pythonxy), PyQt4 is already installed.
+ lmfit 0.9.5 or higher (conda install lmfit)
+ Pyjnius - the most difficult to install - before installing pyjnius, please set the following environmental variables for windows, otherwise pyjinius cannot be installed properly:

    PYTHON_HOME (python install directory, for example: C:\Users\username\Anaconda2)
    PYTHON_SCRIPTS (%PYTHON_HOME%\Scripts)
    PYTHONPATH (%PYTHON_HOME%; %PYTHON_HOME%\DLLs; %PYTHON_HOME%\Lib; %PYTHON_HOME%\Tools; %PYTHON_SCRIPTS%;)
    JDK_HOME
    JRE_HOME
    JAVA_HOME (=JDK_HOME but make both)

    ADD TO path: %PYTHON_HOME%; %PYTHON_SCRIPTS%; %JAVA_HOME%; %JAVA_HOME%\bin; %JAVA_HOME%\jre\bin\server

INSTALLATION:
==========================
Double click on the binary file OceanDAC_XXbit_setup.exe which is found in the Output folder and follow the instructions.

RUNNING:
==========================
Just double click on the OceanDAC icon on your Desktop (WINDOWS). Remember before running this program, you need to plug the USB port of your spectrometer in. Otherwise after plugging in the spectrometer, you need to scan the device by clicking on the scanning button.