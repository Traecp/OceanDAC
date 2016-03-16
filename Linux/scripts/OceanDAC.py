#!/usr/bin/python
# -*- coding: utf-8 -*-
import pygtk
pygtk.require("2.0")
import gobject
import gtk
gobject.threads_init()
import numpy as np
import sys, os
from os import listdir
from os.path import isfile,join
from OceanDAC import pressure, peak

from matplotlib.ticker import FormatStrFormatter
from matplotlib import rcParams
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.backends.backend_gtkagg import NavigationToolbar2GTKAgg as NavigationToolbar
import jnius_config
import time, datetime

def JVM_setup():
	# jnius_config.add_options('-Xmx512m')
	OceanDir = "C:\Program Files (x86)\Ocean Optics\OmniDriver\OOI_HOME"
	lsj      = [i for i in listdir(OceanDir) if isfile(join(OceanDir,i)) and i.endswith(".jar")]
	for j in lsj:
		jnius_config.add_classpath(join(OceanDir,j))
if not jnius_config.vm_running:
	JVM_setup()
	
from jnius import autoclass
Wrapper= autoclass("com.oceanoptics.omnidriver.api.wrapper.Wrapper")

_author__="Tra NGUYEN THANH"
__email__ = "thanhtra0104@gmail.com"
__version__ = "1.2"
__date__="21/01/2016"

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
# #rcParams['image.cmap'] = jet
# rcParams['savefig.dpi'] = 300

__NEON_PEAKS__ = np.loadtxt("NEON_LINES.dat")#Neon emission peaks (nm) - data from Pierre Bouvier CNRS designer of the camera

class MyMainWindow(gtk.Window):

	def __init__(self):
		super(MyMainWindow, self).__init__()
		self.set_title("Ocean Optics Spectrometer - version %s - Last update: %s"%(__version__, __date__))
		self.set_size_request(1250, 750)
		#self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(6400, 6400, 6440))
		self.set_position(gtk.WIN_POS_CENTER)
		self.set_border_width(5)
		# *********************************************************************************
		# ******************* TOOL BAR ****************************************************
		
		self.toolbar = gtk.Toolbar()
		self.toolbar.set_style(gtk.TOOLBAR_ICONS)
		self.reference_btn = gtk.ToolButton(gtk.STOCK_INFO)
		self.continuous_mode_btn = gtk.ToolButton(gtk.STOCK_MEDIA_RECORD)
		self.about  = gtk.ToolButton(gtk.STOCK_DIALOG_WARNING)
		self.zoom_fit_btn = gtk.ToolButton(gtk.STOCK_ZOOM_FIT)
		self.export_main_graph_btn = gtk.ToolButton(gtk.STOCK_GO_DOWN)
		self.detect_spectro_btn = gtk.ToolButton(gtk.STOCK_REFRESH)
		
		self.toolbar.insert(self.detect_spectro_btn, 0)
		self.toolbar.insert(self.continuous_mode_btn, 1)
		self.toolbar.insert(self.reference_btn, 2)
		self.toolbar.insert(self.zoom_fit_btn, 3)
		self.toolbar.insert(self.export_main_graph_btn, 4)
		self.toolbar.insert(self.about, 5)
		
		self.tooltips = gtk.Tooltips()
		self.tooltips.set_tip(self.reference_btn,"Take a background noise reference - Please use the same acquistion parameters (integration time, cycles,...) as for measurment.")
		self.tooltips.set_tip(self.continuous_mode_btn,"Start/Stop continuous spectrum acquisition mode")
		self.tooltips.set_tip(self.about,"About this program")
		self.tooltips.set_tip(self.zoom_fit_btn,"Auto zoom graph")
		self.tooltips.set_tip(self.export_main_graph_btn,"Export graphs data")
		self.tooltips.set_tip(self.detect_spectro_btn,"Scan for spectrometers ...")
		
		self.reference_btn.connect("clicked", self.take_reference)
		self.continuous_mode_btn.connect("clicked", self.permanent_acquisition)
		self.about.connect("clicked",self.about_this_program)
		self.zoom_fit_btn.connect("clicked",self.zoom_fit_graph)
		self.export_main_graph_btn.connect("clicked",self.export_graph_data)
		self.detect_spectro_btn.connect("clicked",self.detection_spectro)
		
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
		#************************* BOXES ************************************************
		vbox = gtk.VBox()
		# vbox.pack_start(self.toolbar,False,False,0)
		hbox=gtk.HBox()
		self.current_folder = os.getcwd()
		#************************* CONTROL PANELS ********************************************
		#Left panel is a notebook, containing 2 control panels: acquisition and calibration
		self.control_panel = gtk.Notebook()
		self.control_acquisition_panel = gtk.VBox()
		self.control_calibration_panel = gtk.VBox()
		
		self.control_panel.append_page(self.control_acquisition_panel, gtk.Label("Acquisition"))
		self.control_panel.append_page(self.control_calibration_panel, gtk.Label("Calibration"))
		hbox.pack_start(self.control_panel, False, False, 0)
		
		#************************* ACQUISITION PANEL ************************************
		self.acq_table = gtk.Table(7,2, False)
			
		self.acq_int_time_txt = gtk.Label("Integration time (ms)")
		self.acq_int_time_txt.set_alignment(0,0.5)
		time_adj = gtk.Adjustment(100,0,999999,5,100,0)
		self.acq_int_time_btn = gtk.SpinButton(time_adj, 0,0)
		self.acq_int_time_btn.set_numeric(True)
		self.acq_int_time_btn.set_update_policy(gtk.UPDATE_IF_VALID)
		self.acq_int_time_btn.set_size_request(50,-1)
		self.acq_int_time_btn.connect('value-changed',self.set_integration_time)
		
		self.acq_avg_scan_txt = gtk.Label("Scans to average")
		self.acq_avg_scan_txt.set_alignment(0,0.5)
		avg_adj = gtk.Adjustment(1,1,1000,1,10,0)
		self.acq_avg_scan_btn = gtk.SpinButton(avg_adj, 0,0)
		self.acq_avg_scan_btn.set_numeric(True)
		self.acq_avg_scan_btn.set_update_policy(gtk.UPDATE_IF_VALID)
		self.acq_avg_scan_btn.set_size_request(50,-1)
		self.acq_avg_scan_btn.connect('value-changed',self.set_average_scan)
		
		self.acq_boxcar_txt = gtk.Label("Boxcar pixels")
		self.acq_boxcar_txt.set_alignment(0,0.5)
		boxcar_adj = gtk.Adjustment(0,0,100,1,10,0)
		self.acq_boxcar_btn = gtk.SpinButton(boxcar_adj, 0,0)
		self.acq_boxcar_btn.set_numeric(True)
		self.acq_boxcar_btn.set_update_policy(gtk.UPDATE_IF_VALID)
		self.acq_boxcar_btn.set_size_request(50,-1)
		self.acq_boxcar_btn.connect('value-changed',self.set_boxcar)
		
		self.acq_darkcorr_txt = gtk.Label("Dark current correction")
		self.acq_darkcorr_txt.set_alignment(0,0.5)
		self.acq_darkcorr_btn = gtk.CheckButton()
		self.acq_darkcorr_btn.connect("toggled", self.set_dark_correction)
		# self.acq_darkcorr_btn.set_active(True)
		
		self.acq_nonlinear_txt = gtk.Label("Non-linearity correction")
		self.acq_nonlinear_txt.set_alignment(0,0.5)
		self.acq_nonlinear_btn = gtk.CheckButton()
		self.acq_nonlinear_btn.connect("toggled", self.set_nonlinear_correction)
		# self.acq_nonlinear_btn.set_active(True)
		
		self.acq_strobeLamp_txt = gtk.Label("Enable strobe/lamp")
		self.acq_strobeLamp_txt.set_alignment(0,0.5)
		self.acq_strobeLamp_btn = gtk.CheckButton()
		self.acq_strobeLamp_btn.connect("toggled", self.set_strobe_lamp)
		
		self.acquisition_btn = gtk.Button("Capture spectrum")
		self.acquisition_btn.connect("clicked",self.acquisition)
		self.acquisition_btn.set_size_request(100,30)
		self.tooltips.set_tip(self.acquisition_btn,"Capture single ruby spectrum and calculate the pressure.")
		
		self.acq_table.attach(self.acq_int_time_txt, 0,1,0,1)
		self.acq_table.attach(self.acq_int_time_btn, 1,2,0,1)
		self.acq_table.attach(self.acq_avg_scan_txt, 0,1,1,2)
		self.acq_table.attach(self.acq_avg_scan_btn, 1,2,1,2)
		self.acq_table.attach(self.acq_boxcar_txt, 0,1,2,3)
		self.acq_table.attach(self.acq_boxcar_btn, 1,2,2,3)
		self.acq_table.attach(self.acq_darkcorr_txt, 0,1,3,4)
		self.acq_table.attach(self.acq_darkcorr_btn, 1,2,3,4)
		self.acq_table.attach(self.acq_nonlinear_txt, 0,1,4,5)
		self.acq_table.attach(self.acq_nonlinear_btn, 1,2,4,5)
		self.acq_table.attach(self.acq_strobeLamp_txt, 0,1,5,6)
		self.acq_table.attach(self.acq_strobeLamp_btn, 1,2,5,6)
		self.acq_table.attach(self.acquisition_btn, 0,2,6,7)
		
		self.acq_table.set_row_spacings(5)
		self.control_acquisition_panel.pack_start(self.acq_table, False, False, 5)
		
		#************************* CALIBRATION PANEL ************************************
		self.calib_table = gtk.Table(5,2, False)
		self.calib_export_calib_btn = gtk.Button("Export current calibration")
		self.calib_import_calib_btn = gtk.Button("Import calibration")
		self.threshold_txt = gtk.Label("Peaks detection threshold")
		self.threshold_txt.set_alignment(0,0.5)
		self.calib_threshold_entry = gtk.Entry()
		self.calib_threshold_entry.set_text("0.30")
		self.calib_threshold_entry.set_size_request(30,25)
		self.calib_fit_btn = gtk.Button("Capture Neon spectrum")
		self.calib_action_btn = gtk.Button("Calibrate")
		
		self.tooltips.set_tip(self.calib_threshold_entry,"Ratio Peak_Min/Peak_Max, value between 0 & 1")
		self.tooltips.set_tip(self.threshold_txt,"Ratio Peak_Min/Peak_Max, value between 0 & 1")
		self.tooltips.set_tip(self.calib_fit_btn,"Capture and fit Neon spectrum - Change the threshold until you are satisfied with the fitting.")
		self.calib_action_btn.connect("clicked", self.do_calibration)
		self.calib_fit_btn.connect("clicked", self.do_fit_neon)
		self.calib_import_calib_btn.connect("clicked", self.do_import_calib)
		self.calib_export_calib_btn.connect("clicked", self.do_export_current_calib)
		
		self.calib_table.attach(self.calib_export_calib_btn, 0,2,0,1)
		self.calib_table.attach(self.calib_import_calib_btn, 0,2,1,2)
		self.calib_table.attach(self.threshold_txt, 0,1,2,3)
		self.calib_table.attach(self.calib_threshold_entry, 1,2,2,3)
		self.calib_table.attach(self.calib_fit_btn, 0,2,3,4)
		self.calib_table.attach(self.calib_action_btn, 0,2,4,5)
		
		self.calib_table.set_row_spacings(5)
		self.calib_table.set_col_spacings(5)
		self.control_calibration_panel.pack_start(self.calib_table, False, False, 5)
		#************************* SPECTRUM PLOT ****************************************
		
		fig_box = gtk.VBox()
		fig_box.pack_start(self.toolbar,False,False,0)
		self.fig=Figure(dpi=100)
		self.ax  = self.fig.add_subplot(111)
		self.MAIN_XLABEL = "Wavelength (nm)"
		self.MAIN_YLABEL = "Intensity (counts)"
		self.fig.subplots_adjust(left=0.13, right = 0.95, bottom=0.13, top=0.95)
		self.ax.set_xlabel(self.MAIN_XLABEL, fontsize=15)
		self.ax.set_ylabel(self.MAIN_YLABEL, fontsize=15)
		
		self.ax.grid(True)
		
		self.canvas  = FigureCanvas(self.fig)
		# self.cursor = Cursor(self.ax, color='k', linewidth=1, useblit=True)		
		self.figure_navigation_toolbar = NavigationToolbar(self.canvas, self)
		fig_box.pack_start(self.canvas, True,True, 0)
		fig_box.pack_start(self.figure_navigation_toolbar, False, False, 0)
		
		#### Results of fitted curves
		
		self.fit_results_table = gtk.Table(6,2, True)
		title = gtk.Label()
		title.set_use_markup(gtk.TRUE)
		title.set_markup("<span color= 'red'><b>Fitted results (Ruby peak R1) </b></span>")
		y0 = gtk.Label("BG:")
		xc = gtk.Label("x0:")
		A = gtk.Label("A:")
		w = gtk.Label("FWHM:")
		mu = gtk.Label("mu:")
		y0.set_alignment(0,0.5)
		xc.set_alignment(0,0.5)
		A.set_alignment(0,0.5)
		w.set_alignment(0,0.5)
		mu.set_alignment(0,0.5)

		self.fitted_y0 = gtk.Label()
		self.fitted_xc = gtk.Label()
		self.fitted_A = gtk.Label()
		self.fitted_w = gtk.Label()
		self.fitted_mu = gtk.Label()

		self.fit_results_table.attach(title,0,2,0,1, xpadding=10)
		self.fit_results_table.attach(y0,0,1,1,2)
		self.fit_results_table.attach(xc,0,1,2,3)
		self.fit_results_table.attach(A,0,1,3,4)
		self.fit_results_table.attach(w,0,1,4,5)
		self.fit_results_table.attach(mu,0,1,5,6)

		self.fit_results_table.attach(self.fitted_y0,1,2,1,2)
		self.fit_results_table.attach(self.fitted_xc,1,2,2,3)
		self.fit_results_table.attach(self.fitted_A,1,2,3,4)
		self.fit_results_table.attach(self.fitted_w,1,2,4,5)
		self.fit_results_table.attach(self.fitted_mu,1,2,5,6)
		
		self.fit_results_table.set_row_spacings(5)
		
		hbox.pack_start(fig_box, True,True, 0)
		
		#************************ RIGHT PANEL ****************************************
		right_panel = gtk.VBox()
		#************************* CHOICE OF GAUGE ***********************************
		self.gauge_selection_window = gtk.Notebook()
		self.ruby_gauge = gtk.VBox()
		self.Samarium_gauge = gtk.VBox()
		
		self.gauge_selection_window.append_page(self.ruby_gauge, gtk.Label("Ruby Cr:Al2O3"))
		self.gauge_selection_window.append_page(self.Samarium_gauge, gtk.Label("Samarium Sm:SrB4O7"))
		
		right_panel.pack_start(self.gauge_selection_window, False, False, 0)
		# ***********************************************************************************
		# **** Page for Ruby:
		self.ruby_calib_table = gtk.Table(1,2,False)
		self.ruby_hydro_btn = gtk.RadioButton(None, "Hydrostatic (Dewaele 2008)")
		self.ruby_hydro_btn.set_active(True)
		self.ruby_non_hydro_btn = gtk.RadioButton(self.ruby_hydro_btn, "Non-hydrostatic (Mao 1986)")
		
		self.ruby_calib_table.attach(self.ruby_hydro_btn, 0,1,0,1)
		self.ruby_calib_table.attach(self.ruby_non_hydro_btn, 1,2,0,1)
		
		self.ruby_gauge.pack_start(self.ruby_calib_table, False, False, 5)
		self.ruby_gauge.pack_start(self.fit_results_table, False, False, 5)
		hseparator = gtk.HSeparator()
		# self.ruby_gauge.pack_start(hseparator, False, False, 20)
		self.pressure_table = gtk.Table(3,2,False)
		ruby_lambda0_txt = gtk.Label(u"\u03BB 0 (nm):")
		ruby_lambda0_txt.set_alignment(0,0.5)
		self.ruby_lambda0_btn = gtk.Entry()
		self.ruby_lambda0_btn.set_text("694.24")
		
		temp_txt = gtk.Label(u"T (K):")
		temp_txt.set_alignment(0,0.5)
		self.temperature_entry = gtk.Entry()
		temp_spin_adj         = gtk.Adjustment(298, 0, 1000, 0.5, 10.0, 0.0)
		self.temp_spin_btn    = gtk.SpinButton(temp_spin_adj,1,1)
		self.temp_spin_btn.set_numeric(True)
		self.temp_spin_btn.set_update_policy(gtk.UPDATE_IF_VALID)
		self.temp_spin_btn.set_size_request(50,-1)
		self.temp_spin_btn.connect('value-changed',self.pressure_calculation)
				
		self.pressure_table.attach(ruby_lambda0_txt, 0,1,0,1)
		self.pressure_table.attach(self.ruby_lambda0_btn, 1,2,0,1)
		self.pressure_table.attach(temp_txt, 0,1,1,2)
		self.pressure_table.attach(self.temp_spin_btn, 1,2,1,2)
		
		self.pressure_table.set_row_spacings(10)
		self.ruby_gauge.pack_start(self.pressure_table, False, False, 5)
		
		# ************ Samarium page
		# *** Fitted results
		self.sum_fit_results_table = gtk.Table(6,2, True)
		title2 = gtk.Label()
		title2.set_use_markup(gtk.TRUE)
		title2.set_markup("<span color= 'red'><b>Fitted results (Samarium peak) </b></span>")
		y0_s = gtk.Label("BG:")
		xc_s = gtk.Label("x0:")
		A_s = gtk.Label("A:")
		w_s = gtk.Label("FWHM:")
		mu_s = gtk.Label("mu:")
		y0_s.set_alignment(0,0.5)
		xc_s.set_alignment(0,0.5)
		A_s.set_alignment(0,0.5)
		w_s.set_alignment(0,0.5)
		mu_s.set_alignment(0,0.5)

		self.sum_fitted_y0 = gtk.Label()
		self.sum_fitted_xc = gtk.Label()
		self.sum_fitted_A = gtk.Label()
		self.sum_fitted_w = gtk.Label()
		self.sum_fitted_mu = gtk.Label()

		self.sum_fit_results_table.attach(title2,0,2,0,1)
		self.sum_fit_results_table.attach(y0_s,0,1,1,2)
		self.sum_fit_results_table.attach(xc_s,0,1,2,3)
		self.sum_fit_results_table.attach(A_s,0,1,3,4)
		self.sum_fit_results_table.attach(w_s,0,1,4,5)
		self.sum_fit_results_table.attach(mu_s,0,1,5,6)

		self.sum_fit_results_table.attach(self.sum_fitted_y0,1,2,1,2)
		self.sum_fit_results_table.attach(self.sum_fitted_xc,1,2,2,3)
		self.sum_fit_results_table.attach(self.sum_fitted_A,1,2,3,4)
		self.sum_fit_results_table.attach(self.sum_fitted_w,1,2,4,5)
		self.sum_fit_results_table.attach(self.sum_fitted_mu,1,2,5,6)
		
		self.sum_fit_results_table.set_row_spacings(5)
		
		# ****************** Calibration modes
		self.Samarium_calib_table = gtk.Table(1,2,False)
		self.Samarium_hydro_btn = gtk.RadioButton(None, "Hydrostatic (Rashchenko 2015)")
		self.Samarium_hydro_btn.set_active(True)
		self.Samarium_non_hydro_btn = gtk.RadioButton(self.Samarium_hydro_btn, "Non-hydrostatic (Jing 2013)")
		
		self.Samarium_calib_table.attach(self.Samarium_hydro_btn, 0,1,0,1)
		self.Samarium_calib_table.attach(self.Samarium_non_hydro_btn, 1,2,0,1)
		
		self.Samarium_pressure_table = gtk.Table(1,2,False)
		Samarium_lambda0_txt = gtk.Label(u"\u03BB 0 (nm):")
		Samarium_lambda0_txt.set_alignment(0,0.5)
		self.Samarium_lambda0_btn = gtk.Entry()
		self.Samarium_lambda0_btn.set_text("685.51")
				
		self.Samarium_pressure_table.attach(Samarium_lambda0_txt, 0,1,0,1)
		self.Samarium_pressure_table.attach(self.Samarium_lambda0_btn, 1,2,0,1)
				
		self.Samarium_gauge.pack_start(self.Samarium_calib_table, False, False, 5)
		self.Samarium_gauge.pack_start(self.sum_fit_results_table, False, False, 5)
		self.Samarium_gauge.pack_start(self.Samarium_pressure_table, False, False, 0)
		
		# *********** DISPLAYING THE PRESSURE ***************************************
		self.pressure_txt = gtk.Label()
		self.pressure_txt.set_use_markup(gtk.TRUE)
		self.pressure_txt.set_markup("<span color='red'><b>P = </b></span>")
		self.pressure_txt.set_alignment(0,0.5)
		
		right_panel.pack_start(self.pressure_txt, False, False, 5)
		# ********************** CONTINUOUS PRESSURE MONITOR *************************
		self.pressure_monitor_fig=Figure(dpi=100)
		self.pressure_monitor_ax  = self.pressure_monitor_fig.add_subplot(111)
		self.PRESSURE_MAIN_XLABEL = "Time (timestamp)"
		self.PRESSURE_MAIN_YLABEL = "Pressure (GPa)"
		self.pressure_monitor_fig.subplots_adjust(left=0.20,bottom=0.20, top=0.90, right =0.95)
		self.pressure_monitor_fig.suptitle("Pressure monitor", fontsize=14)
		self.pressure_monitor_ax.set_xlabel(self.PRESSURE_MAIN_XLABEL, fontsize=12)
		self.pressure_monitor_ax.set_ylabel(self.PRESSURE_MAIN_YLABEL, fontsize=12)
		majorFormatter = FormatStrFormatter('%.1f')
		self.pressure_monitor_ax.yaxis.set_major_formatter(majorFormatter)
		self.pressure_monitor_ax.tick_params(axis='both', which='major', labelsize=10)
		# self.pressure_monitor_plot, = self.pressure_monitor_ax.plot(self.wavelength, self.intensity, "r-")#Attention - there is a comma
		self.pressure_monitor_ax.grid(True)
		
		self.pressure_monitor_canvas  = FigureCanvas(self.pressure_monitor_fig)
		self.pressure_monitor_canvas.set_size_request(400,150)
		self.pressure_monitor_navigation_toolbar = NavigationToolbar(self.pressure_monitor_canvas, self)
		
		hseparator2 = gtk.HSeparator()
		# right_panel.pack_start(hseparator2, False, False, 5)
		# button_monitor_table = gtk.Table(1,1,False)
		self.monitor_pressure_btn = gtk.ToggleButton("Start pressure monitoring")
		self.monitor_pressure_btn.connect("toggled", self.monitoring_pressure)
		self.monitor_pressure_btn.set_size_request(100,30)
		# button_monitor_table.attach(self.monitor_pressure_btn, 0,1,0,1)
		self.enable_pressure_monitoring = False #Flag to handle pressure monitoring event
		# right_panel.pack_start(button_monitor_table, False, False, 0)
		right_panel.pack_start(self.monitor_pressure_btn, False, False, 10)
		right_panel.pack_start(self.pressure_monitor_canvas, True, True, 0)
		right_panel.pack_start(self.pressure_monitor_navigation_toolbar, False, False, 0)
		self.export_pressure_btn = gtk.ToggleButton("Export pressure profile")
		self.export_pressure_btn.connect("toggled", self.export_pressure)
		self.export_pressure_btn.set_size_request(100,30)
		right_panel.pack_start(self.export_pressure_btn, False, False, 10)
		
		
		# ********************** STATUS BAR ******************************************
		
		self.status_bar = gtk.Table(1, 1, False)
		self.status_label = gtk.Label()
		self.status_label.set_alignment(0,0.5)
		self.status_bar.attach(self.status_label, 0,1,0,1)
				
		#*********************** PACK ALL ********************************************
		hbox.pack_start(right_panel, False, False, 5)
		vbox.pack_start(hbox,True, True, 0)
		vbox.pack_end(self.status_bar, False, False, 5)
		self.add(vbox)
		self.connect("destroy", self.destroy_app)
		self.show_all()
		#************************ START PERMANENT ACQUISITION BY DEFAULT ************
		self.Spectrometer = Wrapper()
		self.do_detection_spectro()
		#*****************************************************************************
	
	def destroy_app(self, w):
		self.Spectrometer.closeAllSpectrometers()
		gtk.main_quit()
	
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
			self.acq_darkcorr_btn.set_active(True)
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
		self.status_label.set_text(status_label)
		
	def about_this_program(self, w):
		txt  = "This program reads Ruby fluorescence spectra from Ocean Optics spectrometer, fits the spectrum, and calculates the pressure.\n"
		txt += "The pressure can be monitored in real time.\n"
		txt += "The wavelength can be calibrated using a Neon lamp.\n"
		txt += "The temperature correction is taken into account, using the formula established by Datchi et al. High Pressure Research - vol. 27 (2007) 447-463.\n"
		txt += "The pressure is calculated assuming that the Ruby R1 line shift by temperature and pressure are independent. \n"
		txt += "The pressure is calculated using the formula established by Dewaele et al. PRB 78 (2008) 104102, which is considered more reliable than the formula established by Mao et al. 1986. \n"
		txt += "The pressure calibrated by Mao et al. 1986 is not used because it was underestimated.\n"
		
		txt += "\n\nIf you discover any bug, please inform me: Tra NGUYEN <thanhtra0104@gmail.com>. \nThank you."
		self.popup_info("info",txt)
		
		
	def set_integration_time(self, widget):
		self.integration_time = self.acq_int_time_btn.get_value()
		self.integration_time = float(self.integration_time)
		self.Spectrometer.setIntegrationTime(self.currentSpectroIndex, self.integration_time*1000)
		if self.enable_reference == True:
			self.reference_spectrum = self.background_cps * self.integration_time
		
	def set_average_scan(self, widget):
		self.avg_scan_num = self.acq_avg_scan_btn.get_value()
		self.avg_scan_num = int(self.avg_scan_num)
		self.Spectrometer.setScansToAverage(self.currentSpectroIndex, self.avg_scan_num)
		# self.enable_reference = False
		
	def set_boxcar(self, widget):
		self.box_num = self.acq_boxcar_btn.get_value()
		self.box_num = int(self.box_num)
		self.Spectrometer.setBoxcarWidth(self.currentSpectroIndex, self.box_num)
		# self.enable_reference = False
				
	def set_dark_correction(self, widget):
		darkcorr = 1 if self.acq_darkcorr_btn.get_active()==True else 0
		self.Spectrometer.setCorrectForElectricalDark(self.currentSpectroIndex, darkcorr)
		if darkcorr == 0:
			self.acq_nonlinear_btn.set_active(False)
			self.Spectrometer.setCorrectForDetectorNonlinearity(self.currentSpectroIndex, False)
		# self.enable_reference = False
		
	def set_nonlinear_correction(self, widget):
		nonlinear_corr = 1 if self.acq_nonlinear_btn.get_active()==True else 0
		self.Spectrometer.setCorrectForDetectorNonlinearity(self.currentSpectroIndex, nonlinear_corr)
		# self.enable_reference = False
		
	def set_strobe_lamp(self, widget):
		enable_strobe_lamp = self.acq_strobeLamp_btn.get_active()
		self.Spectrometer.setStrobeEnable(self.currentSpectroIndex, enable_strobe_lamp)
		# self.enable_reference = False
		
	def acquisition(self, widget):
		self.do_acquisition()
		
	def take_reference(self, widget):
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
			
	def permanent_acquisition(self, widget):
		self.enable_permanent_mode = not self.enable_permanent_mode
		self.do_permanent_acq()
			
	def do_permanent_acq(self):
		if self.fit_plot is not None:
			self.ax.lines.remove(self.fit_plot_[0])
			self.fit_plot = None
		task = self.run_forever()
		gobject.idle_add(task.next)
		
	def run_forever(self):
		while self.enable_permanent_mode:
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
			yield True
		yield False
			
					
	def plot_spectrum(self):
		self.spectrum_plot.set_ydata(self.intensity)
		self.canvas.draw()
		
	def zoom_fit_graph(self, widget):
		self.ax.relim()
		self.ax.autoscale()
		self.canvas.draw()
		
	def pressure_calculation(self,w):
		self.calc_pressure()
		
	def calc_pressure(self):
		fit_x = self.wavelength
		fit_y = self.intensity
		self.pressure_gauge = self.gauge_selection_window.get_current_page()
		# Ruby: 0, Samarium: 1
		if self.pressure_gauge == 0:
			self.lambda0 = self.ruby_lambda0_btn.get_text()
			self.lambda0 = float(self.lambda0)
			self.fit_param,self.fit_data = pressure.ruby_fit(fit_x, fit_y)
			self.R1_peak = self.fit_param["x0"].value
			self.temperature = self.temp_spin_btn.get_value()
			if self.ruby_hydro_btn.get_active():
				self.pressure    = pressure.pressure_Datchi_Dewaele(self.lambda0, self.R1_peak, self.temperature)
			elif self.ruby_non_hydro_btn.get_active():
				self.pressure    = pressure.pressure_Mao_NH(self.lambda0, self.R1_peak, self.temperature)
		elif self.pressure_gauge == 1:
			self.lambda0 = self.Samarium_lambda0_btn.get_text()
			self.lambda0 = float(self.lambda0)
			self.fit_param,self.fit_data = pressure.Samarium_fit(fit_x, fit_y)
			self.Samarium_peak = self.fit_param["x0"].value
			if self.Samarium_hydro_btn.get_active():
				self.pressure    = pressure.pressure_Rashchenko_H(self.lambda0, self.Samarium_peak)
			elif self.Samarium_non_hydro_btn.get_active():
				self.pressure    = pressure.pressure_Jing_NH(self.lambda0, self.Samarium_peak)
				
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
			self.fitted_y0.set_text("%6.4f"%(self.fit_param["BG"].value))
			self.fitted_xc.set_text("%6.4f"%(self.fit_param["x0"].value))
			self.fitted_A.set_text("%6.4f"%(self.fit_param["A"].value))
			self.fitted_mu.set_text("%6.4f"%(self.fit_param["mu0"].value))
			self.fitted_w.set_text("%6.4f"%(self.fit_param["w0"].value))
		elif self.pressure_gauge == 1:
			self.sum_fitted_y0.set_text("%6.4f"%(self.fit_param["BG"].value))
			self.sum_fitted_xc.set_text("%6.4f"%(self.fit_param["x0"].value))
			self.sum_fitted_A.set_text("%6.4f"%(self.fit_param["A"].value))
			self.sum_fitted_mu.set_text("%6.4f"%(self.fit_param["mu0"].value))
			self.sum_fitted_w.set_text("%6.4f"%(self.fit_param["w0"].value))
		
		p = "P = %.2f GPa"%self.pressure
		self.pressure_txt.set_markup("<span color='red'><b>%s</b></span>"%p)
		
	def monitoring_pressure(self, widget):
		self.enable_pressure_monitoring = self.monitor_pressure_btn.get_active()
		
		if self.enable_pressure_monitoring:
			self.monitor_pressure_btn.set_label("Stop pressure monitoring")
			self.pressure_list = []
			self.pressure_time_list = []
			if self.enable_permanent_mode == False:
				self.enable_permanent_mode=True
				self.do_permanent_acq()
		else:
			self.monitor_pressure_btn.set_label("Start pressure monitoring")
			self.enable_permanent_mode = False
	
	def export_pressure(self, widget):
		dialog = gtk.FileChooserDialog(title="Export pressure profile", action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_current_folder(self.current_folder)
		response = dialog.run()
		if response==gtk.RESPONSE_OK:
			filename=dialog.get_filename().decode('utf8')
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
		dialog.destroy()
	
	
	def do_fit_neon(self, widget):
		self.peak_threshold = self.calib_threshold_entry.get_text()
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
	
	def do_calibration(self, widget):
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
			self.warning("warning", "New calibration coefficients are successfully set!")
			
		
	def do_export_current_calib(self, widget):
		self.current_calib_coefficients = self.Spectrometer.getCalibrationCoefficientsFromEEProm(self.currentSpectroIndex)
		dialog = gtk.FileChooserDialog(title="Export current calibration coefficients", action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_current_folder(self.current_folder)
		dialog.set_current_name("*.calib")
		response = dialog.run()
		if response==gtk.RESPONSE_OK:
			filename=dialog.get_filename().decode('utf8')
			folder = os.path.dirname(filename)
			self.current_folder = folder
			coeff = self.current_calib_coefficients.getWlCoefficients()
			np.savetxt(filename, coeff)
		dialog.destroy()
		
	def do_import_calib(self, widget):
		dialog = gtk.FileChooserDialog(title="Import calibration coefficients", action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_current_folder(self.current_folder)
		response = dialog.run()
		if response==gtk.RESPONSE_OK:
			filename=dialog.get_filename().decode('utf8')
			folder = os.path.dirname(filename)
			self.current_folder = folder
			self.calibrated_coefficients = np.loadtxt(filename)
			self.calibration()
		dialog.destroy()
		
	def export_graph_data(self, widget):
		dialog = gtk.FileChooserDialog(title="Export current graphs data", action=gtk.FILE_CHOOSER_ACTION_SAVE, buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_current_folder(self.current_folder)
		dialog.set_current_name("*.dat")
		response = dialog.run()
		if response==gtk.RESPONSE_OK:
			filename=dialog.get_filename().decode('utf8')
			folder = os.path.dirname(filename)
			self.current_folder = folder
			data = np.vstack([self.wavelength, self.intensity])
			header = ""
			header += "Integration time (ms): %d"%self.integration_time
			header += "\nScans to average: %d"%self.avg_scan_num
			header += "\nBoxcar smoothing width (pixels): %d"%self.box_num
			header += "\n>>> Data start here <<<"
			header += "\nWavelength (nm) \t Intensity"
			if self.fit_plot is not None:
				data = np.vstack([data, self.fit_data])
				header += " \t Fitted intensity"
			data = data.T
			np.savetxt(filename, data, header=str(header))
		dialog.destroy()
		
		
	def popup_info(self,info_type,text):
		""" info_type = WARNING, INFO, QUESTION, ERROR """
		if info_type.upper() == "WARNING":
			mess_type = gtk.MESSAGE_WARNING
		elif info_type.upper() == "INFO":
			mess_type = gtk.MESSAGE_INFO
		elif info_type.upper() == "ERROR":
			mess_type = gtk.MESSAGE_ERROR
		elif info_type.upper() == "QUESTION":
			mess_type = gtk.MESSAGE_QUESTION

		self.warning=gtk.MessageDialog(self, gtk.DIALOG_DESTROY_WITH_PARENT, mess_type, gtk.BUTTONS_CLOSE,text)
		self.warning.run()
		self.warning.destroy()
	
	def main(self):
		gtk.main()
		
if __name__ == "__main__":
	
	app = MyMainWindow()
	gtk.threads_enter()
	app.main()
	gtk.threads_leave()