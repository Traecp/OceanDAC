#!/usr/bin/python
# -*- coding: utf-8 -*-
import numpy as np
import sys, os
from os import listdir
from os.path import isfile,join
import pressure
import peak
from matplotlib.ticker import FormatStrFormatter
from matplotlib import rcParams
from matplotlib.figure import Figure
import jnius_config
import time, datetime

def JVM_setup():
	# jnius_config.add_options('-Xmx512m')
	OceanDir = "C:\Program Files\Ocean Optics\OmniDriver\OOI_HOME"
	lsj      = [i for i in listdir(OceanDir) if isfile(join(OceanDir,i)) and i.endswith(".jar")]
	for j in lsj:
		jnius_config.add_classpath(join(OceanDir,j))
if not jnius_config.vm_running:
	JVM_setup()
	
from jnius import autoclass
Wrapper= autoclass("com.oceanoptics.omnidriver.api.wrapper.Wrapper")

_author__="Tra NGUYEN THANH"
__email__ = "thanhtra0104@gmail.com"
__version__ = "2.1"
__date__="31/03/2017"

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Tahoma']
rcParams['font.size'] = 14
rcParams['axes.labelsize'] = 'medium'
rcParams['legend.fancybox'] = True
rcParams['legend.handletextpad'] = 0.5
rcParams['legend.fontsize'] = 'medium'
rcParams['figure.subplot.bottom'] = 0.13
rcParams['figure.subplot.top'] = 0.93
rcParams['figure.subplot.left'] = 0.14
rcParams['figure.subplot.right'] = 0.915
rcParams['grid.linestyle'] = ":"
rcParams['image.cmap'] = 'jet'
rcParams['savefig.dpi'] = 300

__NEON_PEAKS__ = np.loadtxt("NEON_LINES.dat")#Neon emission peaks (nm) - data from Pierre Bouvier CNRS designer of the camera

from PyQt4.uic import loadUiType
from PyQt4 import QtGui, QtCore
from matplotlib.backends.backend_qt4agg import (FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar)

Ui_MainWindow, QMainWindow = loadUiType('mainWindow.ui')
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
        
class Main(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)

        self.setWindowTitle("Ocean Optics Spectrometer - version %s - Last update: %s"%(__version__, __date__))
        # ****************** Toolbar actions settings ***********************************
        self.actionRefresh.triggered.connect(self.detection_spectro)
        self.actionRecord.triggered.connect(self.permanent_acquisition)
        self.actionDark.triggered.connect(self.take_reference)
        self.actionZoom.triggered.connect(self.zoom_fit_graph)
        self.actionSave.triggered.connect(self.export_graph_data)
        self.actionAbout.triggered.connect(self.about_this_program)
        self.actionQuit.triggered.connect(self.close)#close is a method within QWidget
        # *********************** VARIABLES *********************************************
        self.reference_spectrum    = None
        self.enable_reference      = False
        self.fit_plot              = None
        self.pressure_list         = []
        self.pressure_time_list    = []
        self.enable_permanent_mode = True
        self.NoOfSpectrometers     = 0
        self.currentSpectroIndex   = 0
        self.integration_time      = 100
        self.avg_scan_num          = 1
        self.box_num               = 0
        self.background_cps        = None
        self.current_folder        = os.getcwd()
        self.enable_pressure_monitoring = False #Flag to handle pressure monitoring event
        self.redIcon = QtGui.QIcon()
        self.redIcon.addPixmap(QtGui.QPixmap(_fromUtf8("icons/Button-Blank-Red-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.greenIcon = QtGui.QIcon()
        self.greenIcon.addPixmap(QtGui.QPixmap(_fromUtf8("icons/Button-Blank-Green-icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        
        #************************* ACQUISITION PANEL ************************************
        self.acq_int_time_btn.valueChanged.connect(self.set_integration_time)
        self.acq_avg_scan_btn.valueChanged.connect(self.set_average_scan)
        self.acq_boxcar_btn.valueChanged.connect(self.set_boxcar)
        self.acq_darkcorr_btn.toggled.connect(self.set_dark_correction)
        self.acq_nonlinear_btn.toggled.connect(self.set_nonlinear_correction)
        self.acq_strobeLamp_btn.toggled.connect(self.set_strobe_lamp)
        self.acquisition_btn.clicked.connect(self.acquisition)
        #************************* CALIBRATION PANEL ************************************
        self.calib_action_btn.clicked.connect(self.do_calibration)
        self.calib_fit_btn.clicked.connect(self.do_fit_neon)
        self.calib_import_calib_btn.clicked.connect(self.do_import_calib)
        self.calib_export_calib_btn.clicked.connect(self.do_export_current_calib)
        
        #************************* SPECTRUM PLOT ****************************************
        self.fig=Figure(dpi=100)
        self.ax  = self.fig.add_subplot(111)
        self.MAIN_XLABEL = "Wavelength (nm)"
        self.MAIN_YLABEL = "Intensity (counts)"
        self.fig.subplots_adjust(left=0.15, right = 0.95, bottom=0.13, top=0.95)
        self.ax.set_xlabel(self.MAIN_XLABEL, fontsize=15)
        self.ax.set_ylabel(self.MAIN_YLABEL, fontsize=15)
        
        self.ax.grid(True)
        
        self.canvas  = FigureCanvas(self.fig)
        self.figure_navigation_toolbar = NavigationToolbar(self.canvas, self.fig_box, coordinates=True)
        self.fig_box_layout.addWidget(self.canvas)
        self.fig_box_layout.addWidget(self.figure_navigation_toolbar)
        
        #************************ RIGHT PANEL ****************************************
        #************************* CHOICE OF GAUGE ***********************************
        # **** Page for Ruby:
        self.temp_spin_btn.valueChanged.connect(self.pressure_calculation)
        
        # ************ Samarium page: no action connection
        # ********************** CONTINUOUS PRESSURE MONITOR *************************
        self.pressure_monitor_fig=Figure(dpi=100)
        self.pressure_monitor_ax  = self.pressure_monitor_fig.add_subplot(111)
        self.PRESSURE_MAIN_XLABEL = "Time (timestamp)"
        self.PRESSURE_MAIN_YLABEL = "Pressure (GPa)"
        self.pressure_monitor_fig.subplots_adjust(left=0.20,bottom=0.20, top=0.90, right =0.95)
        self.pressure_monitor_fig.suptitle("Pressure monitor", fontsize=14)
        self.pressure_monitor_ax.set_xlabel(self.PRESSURE_MAIN_XLABEL, fontsize=12)
        self.pressure_monitor_ax.set_ylabel(self.PRESSURE_MAIN_YLABEL, fontsize=12)
        self.majorFormatter = FormatStrFormatter('%.1f')
        self.pressure_monitor_ax.yaxis.set_major_formatter(self.majorFormatter)
        self.pressure_monitor_ax.tick_params(axis='both', which='major', labelsize=10)
        # self.pressure_monitor_plot, = self.pressure_monitor_ax.plot(self.wavelength, self.intensity, "r-")#Attention - there is a comma
        self.pressure_monitor_ax.grid(True)
        
        self.pressure_monitor_canvas  = FigureCanvas(self.pressure_monitor_fig)
        self.pressure_monitor_navigation_toolbar = NavigationToolbar(self.pressure_monitor_canvas, self.pressure_monitor, coordinates=True)
        self.pressure_monitor_layout.addWidget(self.pressure_monitor_canvas)
        self.pressure_monitor_layout.addWidget(self.pressure_monitor_navigation_toolbar)
        
        self.monitor_pressure_btn.toggled.connect(self.monitoring_pressure)
        self.export_pressure_btn.clicked.connect(self.export_pressure)
        
        # ************** Status bar information *************************************
        self.status_label = QtGui.QLabel()
        self.statusbar.addPermanentWidget(self.status_label)
        #************************ START PERMANENT ACQUISITION BY DEFAULT ************
        self.Spectrometer = Wrapper()
        self.do_detection_spectro()
        #*****************************************************************************
        
    def about_this_program(self):
        txt  = "This program reads Ruby fluorescence spectra from Ocean Optics spectrometer, fits the spectrum, and calculates the pressure.\n"
        txt += "The pressure can be monitored in real time.\n"
        txt += "The wavelength can be calibrated using a Neon lamp.\n"
        txt += "The temperature correction is taken into account, using the formula established by Datchi et al. High Pressure Research - vol. 27 (2007) 447-463.\n"
        txt += "The pressure is calculated assuming that the Ruby R1 line shift by temperature and pressure are independent. \n"
        txt += "The pressure is calculated using the formula established by Dewaele et al. PRB 78 (2008) 104102, which is considered more reliable than the formula established by Mao et al. 1986. \n"
        txt += "The pressure calibrated by Mao et al. 1986 is not used because it was underestimated.\n"
        
        txt += "\n\nIf you discover any bug, please inform me: Tra NGUYEN <thanhtra0104@gmail.com>. \nThank you."
        self.popup_info("info",txt)
        
    def closeEvent(self, event):
        # When user clicks on the Quit button on the toolbar or the red X button of the window
        self.Spectrometer.closeAllSpectrometers()
        self.enable_permanent_mode = False
        event.accept()
        
    def image_init(self):
        self.ax.cla()
        self.ax.set_xlabel(self.MAIN_XLABEL, fontsize=15)
        self.ax.set_ylabel(self.MAIN_YLABEL, fontsize=15)
        self.ax.grid(True)
        
    def detection_spectro(self, widget):
        self.do_detection_spectro()
        
    def do_detection_spectro(self):
        try:
            self.NoOfSpectrometers = self.Spectrometer.openAllSpectrometers()
        except:
            self.NoOfSpectrometers = 0
            pass
        if self.NoOfSpectrometers>0:
            self.acq_darkcorr_btn.setChecked(True)
            self.currentSpectroSerial= self.Spectrometer.getSerialNumber(self.currentSpectroIndex)
            self.currentSpectroName  = self.Spectrometer.getName(self.currentSpectroIndex)
            self.Spectrometer.setAutoToggleStrobeLampEnable(self.currentSpectroIndex, True)
            # self.Spectrometer.setStrobeEnable(self.currentSpectroIndex, False)
            self.Spectrometer.setIntegrationTime(self.currentSpectroIndex, self.integration_time*1000)
            self.Spectrometer.setScansToAverage(self.currentSpectroIndex, self.avg_scan_num)
            self.Spectrometer.setBoxcarWidth(self.currentSpectroIndex, self.box_num)
            self.Spectrometer.setCorrectForDetectorNonlinearity(self.currentSpectroIndex, False)
            # self.Spectrometer.setCorrectForElectricalDark(self.currentSpectroIndex, True)
            self.wavelength = self.Spectrometer.getWavelengths(self.currentSpectroIndex)
            self.wavelength = np.array(self.wavelength)
            self.intensity  = self.Spectrometer.getSpectrum(self.currentSpectroIndex)
            self.intensity  = np.array(self.intensity)
            print "Detected %d spectrometers. Current spectro: ID = %s, Serial = %s"%(self.NoOfSpectrometers, self.currentSpectroName,\
                                                                     self.currentSpectroSerial)
            self.image_init()
            self.spectrum_plot, = self.ax.plot(self.wavelength, self.intensity, "r-")#Attention - there is a comma
            self.do_permanent_acq()
            
        else:
            self.wavelength, self.intensity = np.arange(3648), np.zeros(3648)
            self.popup_info("error", "No spectrometer found. Please check if you plugged them in. Press the 'Scan for spectrometers ...' button once a spectrometer is plugged in.")
            self.spectrum_plot, = self.ax.plot(self.wavelength, self.intensity, "r-")#Attention - there is a comma
        if self.NoOfSpectrometers>0:
            status_label = "%d spectrometer detected. Current spectrometer : %s - S/N: %s"%(self.NoOfSpectrometers, self.currentSpectroName, self.currentSpectroSerial)
            
        else:
            status_label = "No spectrometers detected. Please check if you have plugged them in."
        self.status_label.setText(status_label)
    
    def set_integration_time(self):
        self.integration_time = self.acq_int_time_btn.value()
        self.integration_time = float(self.integration_time)
        self.Spectrometer.setIntegrationTime(self.currentSpectroIndex, self.integration_time*1000)
        if self.enable_reference == True:
            self.reference_spectrum = self.background_cps * self.integration_time
            
    def set_average_scan(self):
        self.avg_scan_num = self.acq_avg_scan_btn.value()
        self.avg_scan_num = int(self.avg_scan_num)
        self.Spectrometer.setScansToAverage(self.currentSpectroIndex, self.avg_scan_num)
        # self.enable_reference = False
        
    def set_boxcar(self):
        self.box_num = self.acq_boxcar_btn.value()
        self.box_num = int(self.box_num)
        self.Spectrometer.setBoxcarWidth(self.currentSpectroIndex, self.box_num)
        # self.enable_reference = False
                
    def set_dark_correction(self):
        darkcorr = 1 if self.acq_darkcorr_btn.isChecked()==True else 0
        self.Spectrometer.setCorrectForElectricalDark(self.currentSpectroIndex, darkcorr)
        if darkcorr == 0:
            self.acq_nonlinear_btn.setChecked(False)
            self.Spectrometer.setCorrectForDetectorNonlinearity(self.currentSpectroIndex, False)
        # self.enable_reference = False
        
    def set_nonlinear_correction(self):
        nonlinear_corr = 1 if self.acq_nonlinear_btn.isChecked()==True else 0
        self.Spectrometer.setCorrectForDetectorNonlinearity(self.currentSpectroIndex, nonlinear_corr)
        # self.enable_reference = False
        
    def set_strobe_lamp(self):
        enable_strobe_lamp = self.acq_strobeLamp_btn.isChecked()
        self.Spectrometer.setStrobeEnable(self.currentSpectroIndex, enable_strobe_lamp)
        # self.enable_reference = False
        
    def acquisition(self):
        self.do_acquisition()
    
    def take_reference(self):
        # self.enable_permanent_mode = False
        self.reference_spectrum  = self.Spectrometer.getSpectrum(self.currentSpectroIndex)
        self.reference_spectrum  = np.array(self.reference_spectrum)
        self.intensity = self.reference_spectrum.copy()
        self.enable_reference = True
        self.background_cps   = self.reference_spectrum / self.integration_time
        self.plot_spectrum()
        
    def do_acquisition(self):
        self.enable_permanent_mode = False
        self.intensity  = self.Spectrometer.getSpectrum(self.currentSpectroIndex)
        self.intensity  = np.array(self.intensity)
        if self.enable_reference==True:
            self.intensity = self.intensity - self.reference_spectrum
        self.plot_spectrum()
        self.calc_pressure()
            
    def permanent_acquisition(self):
        self.enable_permanent_mode = not self.enable_permanent_mode
        self.do_permanent_acq()
            
    def do_permanent_acq(self):
        if self.enable_permanent_mode:
            self.actionRecord.setIcon(self.redIcon)
        else:
            self.actionRecord.setIcon(self.greenIcon)
            
        if self.fit_plot is not None:
            self.ax.lines.remove(self.fit_plot_[0])
            self.fit_plot = None
        if self.enable_permanent_mode:
            QtCore.QTimer.singleShot(0, self.run_forever)
        
    def run_forever(self):
        while self.enable_permanent_mode:
            time.sleep(0.05)
            self.intensity = self.Spectrometer.getSpectrum(self.currentSpectroIndex)
            self.intensity = np.array(self.intensity)
            if self.enable_reference == True:
                self.intensity = self.intensity - self.reference_spectrum
            self.plot_spectrum()
            if self.enable_pressure_monitoring:
                self.calc_pressure()
                self.pressure_monitor_ax.cla()
                self.pressure_monitor_ax.set_xlabel(self.PRESSURE_MAIN_XLABEL, fontsize=12)
                self.pressure_monitor_ax.set_ylabel(self.PRESSURE_MAIN_YLABEL, fontsize=12)
                majorFormatter = FormatStrFormatter('%.1f')
                self.pressure_monitor_ax.yaxis.set_major_formatter(majorFormatter)
                self.pressure_monitor_ax.plot(self.pressure_list, "b-")
                self.pressure_monitor_ax.tick_params(axis='both', which='major', labelsize=10)
                self.pressure_monitor_ax.grid(True)
                self.pressure_monitor_canvas.draw()
            QtGui.qApp.processEvents()
            if self.enable_permanent_mode==False:
                break
            
    def plot_spectrum(self):
        self.spectrum_plot.set_ydata(self.intensity)
        self.canvas.draw()
        
    def zoom_fit_graph(self):
        self.ax.relim()
        self.ax.autoscale()
        self.canvas.draw()
        
    def pressure_calculation(self):
        self.calc_pressure()
        
    def calc_pressure(self):
        fit_x = self.wavelength
        fit_y = self.intensity
        self.pressure_gauge = self.gauge_selection_window.currentIndex()
        # Ruby: 0, Samarium: 1
        if self.pressure_gauge == 0:
            self.lambda0 = self.ruby_lambda0_btn.text()
            self.lambda0 = float(self.lambda0)
            self.fit_param,self.fit_data = pressure.ruby_fit(fit_x, fit_y)
            self.R1_peak = self.fit_param["x0"].value
            self.fluorescence_peak = self.R1_peak
            self.temperature = self.temp_spin_btn.value()
            if self.ruby_hydro_btn.isChecked():
                self.pressure    = pressure.pressure_Datchi_Dewaele(self.lambda0, self.R1_peak, self.temperature)
                self.pressure_formula = "Hydrostatic Dewaele 2008"
            elif self.ruby_non_hydro_btn.isChecked():
                self.pressure    = pressure.pressure_Mao_NH(self.lambda0, self.R1_peak, self.temperature)
                self.pressure_formula = "Non-hydrostatic Mao 1986"
        elif self.pressure_gauge == 1:
            self.lambda0 = self.Samarium_lambda0_btn.text()
            self.lambda0 = float(self.lambda0)
            self.fit_param,self.fit_data = pressure.samarium_fit(fit_x, fit_y)
            self.Samarium_peak = self.fit_param["x0"].value
            self.fluorescence_peak = self.Samarium_peak
            if self.Samarium_hydro_btn.isChecked():
                self.pressure    = pressure.pressure_Rashchenko_H(self.lambda0, self.Samarium_peak)
                self.pressure_formula = "Hydrostatic Rashchenko 2015"
            elif self.Samarium_non_hydro_btn.isChecked():
                self.pressure    = pressure.pressure_Jing_NH(self.lambda0, self.Samarium_peak)
                self.pressure_formula = "Non-hydrostatic Jing 2013"
                
        self.pressure_list.append(self.pressure)
        timestamp = time.time()
        self.pressure_time_list.append(timestamp)
        
        if self.fit_plot is not None:
            self.ax.lines.remove(self.fit_plot_[0])
        self.fit_plot_ = self.ax.plot(fit_x, self.fit_data, "b-", lw=1.5)
        
        self.fit_plot = 1
        self.canvas.draw()
        self.display_fit_results()
        
    def display_fit_results(self):
        if self.pressure_gauge == 0:
            self.fitted_y0.setText("%6.4f"%(self.fit_param["BG"].value))
            self.fitted_xc.setText("%6.4f"%(self.fit_param["x0"].value))
            self.fitted_A.setText("%6.4f"%(self.fit_param["A"].value))
            self.fitted_mu.setText("%6.4f"%(self.fit_param["mu0"].value))
            self.fitted_w.setText("%6.4f"%(self.fit_param["w0"].value))
        elif self.pressure_gauge == 1:
            self.sum_fitted_y0.setText("%6.4f"%(self.fit_param["BG"].value))
            self.sum_fitted_xc.setText("%6.4f"%(self.fit_param["x0"].value))
            self.sum_fitted_A.setText("%6.4f"%(self.fit_param["A"].value))
            self.sum_fitted_mu.setText("%6.4f"%(self.fit_param["mu0"].value))
            self.sum_fitted_w.setText("%6.4f"%(self.fit_param["w0"].value))
        
        p = "<html><p><span style='color:#ff0000;'>P = %.2f GPa</span></p></html>"%self.pressure
        self.pressure_txt.setText(p)
        
    def monitoring_pressure(self):
        self.enable_pressure_monitoring = self.monitor_pressure_btn.isChecked()
        
        if self.enable_pressure_monitoring:
            self.monitor_pressure_btn.setText("Stop pressure monitoring")
            self.pressure_list = []
            self.pressure_time_list = []
            if self.enable_permanent_mode == False:
                self.enable_permanent_mode=True
                # self.do_permanent_acq()
        else:
            self.monitor_pressure_btn.setText("Start pressure monitoring")
            # self.enable_permanent_mode = False
        self.do_permanent_acq()
    
    def export_pressure(self):
        fname = QtGui.QFileDialog.getSaveFileName(self, 'Save data to file', self.current_folder)
        filename=fname.decode('utf8')
        folder = os.path.dirname(filename)
        self.current_folder = folder
        if len(self.pressure_monitor_ax.get_lines())>0:
            # data = self.pressure_monitor_ax.get_lines()[0].get_xydata()
            pressure = np.array(self.pressure_list)
            timestamp= np.array(self.pressure_time_list)
            data = np.vstack([timestamp, pressure])
            data = data.T
            header = str("Timestamp \t Pressure (GPa) - To convert to date format using Python: import datetime >> datetime.datetime.fromtimestamp(timestamp) - or do it with Microsoft Excel :)")
            np.savetxt(filename, data, header=header)
    
    def do_fit_neon(self):
        self.peak_threshold = self.calib_threshold_entry.value()
        self.peak_threshold = float(self.peak_threshold)
        self.do_acquisition()
        self.neon_fit_param, self.neon_fit_data = pressure.neon_fit(self.wavelength,self.intensity, self.peak_threshold)
        if self.fit_plot is not None:
            self.ax.lines.remove(self.fit_plot_[0])
        self.fit_plot_ = self.ax.plot(self.wavelength, self.neon_fit_data, "b-", lw=1.5)
        self.fit_plot = 1
        self.canvas.draw()
        #Getting the fitted peaks positions
        n = len(self.neon_fit_param.keys())-1
        n = n/4#Number of peaks
        self.neon_peaks_positions = []#fitted positions in wavelength
        for i in range(n):
            x = self.neon_fit_param["X%d"%i].value
            self.neon_peaks_positions.append(x)
        self.neon_peaks_positions = sorted(self.neon_peaks_positions)
        
        self.true_neon_wl_index = peak.get_index_from_values(__NEON_PEAKS__, self.neon_peaks_positions)
        self.neon_true_wavelength = __NEON_PEAKS__[self.true_neon_wl_index]
        
        self.measured_wl_pixel = peak.get_index_from_values(self.wavelength, self.neon_peaks_positions)
        self.calibrated_coefficients = pressure.calibration_coefficients(self.measured_wl_pixel, self.neon_true_wavelength)

    def do_calibration(self):
        self.calibration()
        
    def calibration(self):
        self.current_calib_coefficients = self.Spectrometer.getCalibrationCoefficientsFromEEProm(self.currentSpectroIndex)
        if (self.current_calib_coefficients != None):
            self.current_calib_coefficients.setWlIntercept(self.calibrated_coefficients[0])
            self.current_calib_coefficients.setWlFirst(self.calibrated_coefficients[1])
            self.current_calib_coefficients.setWlSecond(self.calibrated_coefficients[2])
            self.current_calib_coefficients.setWlThird(self.calibrated_coefficients[3])
            self.Spectrometer.insertKey("Mat429sky")# enable writes to sensitive areas, SO BE CAREFUL!
            success = self.Spectrometer.setCalibrationCoefficientsIntoEEProm(self.currentSpectroIndex, self.current_calib_coefficients, True, False, False)
            self.Spectrometer.removeKey()# prevent any further updating of our calibration buffer area
            self.wavelength = self.Spectrometer.getWavelengths(self.currentSpectroIndex)#Updating new wavelength
            self.popup_info("warning", "New calibration coefficients are successfully set!")
            
    def do_export_current_calib(self):
        self.current_calib_coefficients = self.Spectrometer.getCalibrationCoefficientsFromEEProm(self.currentSpectroIndex)
        fname = QtGui.QFileDialog.getSaveFileName(self, "Export current calibration coefficients", self.current_folder, "Calib files (*.calib)")
        filename=fname.decode('utf8')
        folder = os.path.dirname(filename)
        self.current_folder = folder
        coeff = self.current_calib_coefficients.getWlCoefficients()
        np.savetxt(filename, coeff)
        
    def do_import_calib(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, "Import calibration coefficients", self.current_folder, "Calib files (*.calib)")
        filename=fname.decode('utf8')
        folder = os.path.dirname(filename)
        self.current_folder = folder
        self.calibrated_coefficients = np.loadtxt(filename)
        self.calibration()
        
    def export_graph_data(self):
        fname = QtGui.QFileDialog.getSaveFileName(self, "Export current graphs data", self.current_folder, "Data files (*.dat)")
        filename=fname.decode('utf8')
        folder = os.path.dirname(filename)
        self.current_folder = folder
        data = np.vstack([self.wavelength, self.intensity])
        scale ={0:"Ruby", 1:"Samarium"}
        header = ""
        header += "Integration time (ms): %d"%self.integration_time
        header += "\nScans to average: %d"%self.avg_scan_num
        header += "\nBoxcar smoothing width (pixels): %d"%self.box_num
        if self.fit_plot is not None:
            header += "\nPressure: %4.4f GPa | Wavelength: %6.4f | Lambda_0: %6.4f | Temperature: %4.2f | Pressure scale: %s | %s"%(self.pressure, self.fluorescence_peak, self.lambda0, self.temperature, scale[self.pressure_gauge], self.pressure_formula)
        header += "\n>>> Data start here <<<"
        header += "\nWavelength (nm) \t Intensity"
        if self.fit_plot is not None:
            data = np.vstack([data, self.fit_data])
            header += " \t Fitted intensity"
        data = data.T
        np.savetxt(filename, data, header=str(header))
        
    def popup_info(self,info_type,text):
        """ info_type = WARNING, INFO, QUESTION, ERROR """
        self.msgbox = QtGui.QMessageBox()
        
        if info_type.upper() == "WARNING":
            self.msgbox.setIcon(QtGui.QMessageBox.Warning)
            self.msgbox.setText("Warning!")
        elif info_type.upper() == "INFO":
            self.msgbox.setText("Information:")
            self.msgbox.setIcon(QtGui.QMessageBox.Information)
        elif info_type.upper() == "ERROR":
            self.msgbox.setText("Attention!")
            self.msgbox.setIcon(QtGui.QMessageBox.Critical)
        elif info_type.upper() == "QUESTION":
            self.msgbox.setText("Sorry?")
            self.msgbox.setIcon(QtGui.QMessageBox.Question)
        
        self.msgbox.setInformativeText(text)
        self.msgbox.setStandardButtons(QtGui.QMessageBox.Ok)
        self.msgbox.exec_()

if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())
