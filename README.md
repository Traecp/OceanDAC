<img src="https://github.com/Traecp/OceanDAC/blob/master/OceanDAC_v1.2_monitoring.png">

OceanDAC is a software which communicates with Ocean Optics spectrometer in order to read luminescence spectra of Ruby or Samarium to measure pressure in Diamond Anvil Cell.
The current version is 1.2, last update: 21/01/2016

++ CAUTION: This program is not intended to be used under Linux. For the moment it only supports Windows users.

INSTALLATION PREREQUISITE:
==========================
+ Java SE JDK 32 bits (the version 1.8.0_66 is used when writing this software);
+ OceanOptics OmniDriver version 32 bits - Use the development package when asked;
+ GTK+ runtime environment - 32 bits;
+ Python (2.7) packages needed:
--- Numpy, Scipy, Matplotlib
--- lmfit 0.8.3
--- pygtk (use the 32 bits all-in-one package)
--- pyjnius

INSTALLATION:
==========================
Double click on the binary file OceanDAC_v1.2_setup.exe which is found in the Binary_setup folder and follow the instructions.

AFTER INSTALLATION:
==========================
Before starting to use this software, please check if the follow environment variables are registered:

+ "JAVA_HOME" = C:\Program Files (x86)\Java\jdkxxx (your java jdk version)
+ "Path": add C:\Program Files (x86)\Java\jdkxxx\jre\bin\server into the Path variable.

To check this: Right click on My Computer >> Properties >> Advanced system settings >> Environment Variables >>

RUNNING:
==========================
Just double click on the OceanDAC icon on your Desktop (WINDOWS). Remember before running this program, you need to plug the USB port of your spectrometer in. Otherwise after plugging in the spectrometer, you need to scan the device by clicking on the scanning button.