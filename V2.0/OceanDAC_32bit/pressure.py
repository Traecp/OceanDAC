#!/usr/bin/python
# -*- coding: utf-8 -*-
import numpy as np
from lmfit import Parameters, minimize
from pylab import *
import operator, csv
import peak

def Lorentzian(x0,w,x):
	""" normalised area lorentzian (integral = 1)"""
	return (1./2.0/np.pi)*(w/((x-x0)**2+w**2/4.0))
	
def gauss(x0,w,x):
	""" normalised area gaussian"""
	return np.sqrt(4.*np.log(2)/np.pi)*(1./w)*np.exp(-((4.*np.log(2))/(w**2))*(x-x0)**2)
	
def pseudo_Voigt(x0,w,mu,x):
	return mu*gauss(x0,w,x) + (1-mu)*Lorentzian(x0,w,x)

def calibration_coefficients(pixel, true_wavelength):
	"""Calculation of calibration coefficients of the spectrometer using Neon spectrum - third order polynomial regression ==> [C3, C2, C1, I]
	    pixel: list of pixel corresponding to the neon peaks
		true_wavelength: the theoretical wavelength
	"""
	coeff = np.polyfit(pixel, true_wavelength, 3)#This returns highest power coefficient first. I want lowest power first
	return coeff[::-1]
	
def objective(pars,y,x,model):
	#we will minimize this function
	if model=="ruby":
		err =  y - ruby_model(pars,x)
	elif model=="neon":
		err =  y - neon_model(pars,x)
	elif model=="samarium":
		err =  y - samarium_model(pars,x)
	return err
	
def neon_model(params, x):
	BG = params["BG"].value
	n  = len(params.keys()) -1
	n  = n/4#Number of peaks
	A_variables = []
	X_variables = []
	W_variables = []
	MU_variables = []
	for i in range(n):
		A_variables.append("A%d"%i)
		X_variables.append("X%d"%i)
		W_variables.append("W%d"%i)
		MU_variables.append("MU%d"%i)
	
	m  = BG
	for i in range(n):
		ampl = params[A_variables[i]].value
		center = params[X_variables[i]].value
		width  = params[W_variables[i]].value
		mu     = params[MU_variables[i]].value
		# m = m + ampl * Lorentzian(center, width, x)
		m = m + ampl * pseudo_Voigt(center, width, mu, x)
	return m
	
def neon_init(x_list, y_list):
	""" Initialize parameters for neon peaks 
	x_list: list of x peaks 
	y_list: list of y peaks
	returns: params 
	"""
	params = Parameters()
	BG     = 100.
	params.add("BG", value = BG)
	n      = len(x_list)
	A_variables = []
	X_variables = []
	W_variables = []
	MU_variables = []
	for i in range(n):
		A_variables.append("A%d"%i)
		X_variables.append("X%d"%i)
		W_variables.append("W%d"%i)
		MU_variables.append("MU%d"%i)
	W  = np.ones(n)
	MU = W*0.5
	for i in range(n):
		params.add(X_variables[i], value = x_list[i], min = x_list[i]-2., max = x_list[i]+2.)
		params.add(A_variables[i], value = y_list[i])
		params.add(W_variables[i], value = W[i])
		params.add(MU_variables[i], value = MU[i])
	print "number of params: %d"%len(params.keys())
	return params
		
def neon_fit(x,y,threshold):
	ind     = peak.indexes(y, thres=threshold, min_dist=30)
	x_peaks = peak.interpolate(x,y,ind, width=15, func = peak.lorentzian_fit)
	new_ind = peak.get_index_from_values(x, x_peaks)
	y_peaks = y[new_ind]
	param_init = neon_init(x_peaks, y_peaks)
	result = minimize(objective, param_init, args=(y,x, "neon"))
	y = neon_model(result.params, x)
	return result.params, y

def ruby_model(parameters,x):
	BG = parameters['BG'].value
	x0 = parameters['x0'].value
	x1 = parameters['x1'].value
	A  = parameters['A'].value
	w0  = parameters['w0'].value
	w1  = parameters['w1'].value
	ratio = parameters["ratio"].value
	mu0 = parameters["mu0"].value
	mu1 = parameters["mu1"].value
	# model = BG + A*Lorentzian(x0,w0,x) + A*ratio*Lorentzian(x1,w1,x)
	model = BG + A*pseudo_Voigt(x0,w0,mu0,x) + A*ratio*pseudo_Voigt(x1,w1,mu1,x)
	#Maximum peak = x0
	return model
	
def ruby_init(data_x,data_y):
	param = Parameters()
	A  = data_y.max()
	BG = 200
	x0 = data_x[np.argmax(data_y)]
	x1 = x0 - 2.0
	w0  = 0.5
	w1  = 0.5
	ratio = 0.606
	mu0 = 0.5 
	mu1 = 0.5 
	A = w0*A 
	param.add('BG', value=BG, vary=True)
	param.add('x0', value=x0, vary=True)
	param.add('x1', value=x1, vary=True)
	param.add('A', value=A, vary=True)
	param.add('w0', value=w0, vary=True)
	param.add('w1', value=w1, vary=True)
	param.add('mu0', value=mu0, vary=True, min=0, max=1)
	param.add('mu1', value=mu1, vary=True, min=0, max=1)
	param.add('ratio', value=ratio, vary=True, min=0.1, max=1.)
	return param

def ruby_fit(data_x, data_y):
	""" return: fitted data y, fitted parameters """
	param_init = ruby_init(data_x,data_y)
	result = minimize(objective, param_init, args=(data_y,data_x, "ruby"))
	y = ruby_model(result.params,data_x)

	return result.params, y

def samarium_model(params, x):
	BG = params['BG'].value
	x0 = params['x0'].value
	A  = params['A'].value
	w0  = params['w0'].value
	mu0 = params["mu0"].value
	model = BG + A*pseudo_Voigt(x0,w0,mu0,x)
	return model
	
def samarium_init(data_x, data_y):
	param = Parameters()
	A  = data_y.max()
	BG = 100
	x0 = data_x[np.argmax(data_y)]
	w0  = 1
	mu0 = 0.5
	A = w0*A 
	param.add('BG', value=BG, vary=True)
	param.add('x0', value=x0, vary=True)
	param.add('A', value=A, vary=True)
	param.add('w0', value=w0, vary=True)
	param.add('mu0', value=mu0, vary=True, min=0, max=1)
	return param
	
def samarium_fit(data_x, data_y):
	param_init = samarium_init(data_x,data_y)
	result = minimize(objective, param_init, args=(data_y,data_x, "samarium"))
	y = samarium_model(result.params,data_x)
	return result.params, y
	
def temperature_correction(w0, w, T):
	#Temperature correction using equations in Datchi et al. High Pressure Research - vol. 27 (2007) 447-463
	# w0 = 694.24 #nm, at 298 K 
	# dw = w-w0
	dT = T - 298.0
	if 296.0<=T<=900.0:
		dw = 0.00746*dT - 3.01e-6*dT**2 + 8.76e-9*dT**3
	elif T<50.0:
		dw = -0.887
	elif 50.0 <= T <296.0:
		dw = 0.00664*dT + 6.76e-6*dT**2 - 2.33e-8*dT**3
		
	w_corr = w - dw
	return w_corr
	
def pressure_Datchi_Dorogokupets(w0, w, T):
	#Dorogokupets et al. PRB 75 (2007) 024115
	# w0 = 694.24 #nm, at 298 K 
	w_corr = temperature_correction(w0, w,T)
	dw = w_corr - w0
	P = 1884*(dw/w0)*(1+5.5*(dw/w0))
	return P
	
def pressure_Datchi_Dewaele(w0, w, T):
	#Calculate the pressure (GPa) knowing the wavelength w(nm)
	#T : temperature in Kelvin, to be corrected the R1 line
	#Temperature correction using equations in Datchi et al. High Pressure Research - vol. 27 (2007) 447-463
	#Pressure scale according to Dewaele et al. PRB 78 (2008) 104102
	A  = 1920. #GPa
	B  = 9.61
	# w0 = 694.24 #nm, at 296 K 
	w_corr = temperature_correction(w0, w,T)
	P = A/B * ((w_corr/w0)**B -1)
	return P 
	
def pressure_Mao_H(w0, w,T):
	A  = 1904. #GPa
	B  = 7.665
	# w0 = 694.24 #nm, at 298 K 
	w_corr = temperature_correction(w0, w,T)
	P = A/B * ((w_corr/w0)**B -1)
	return P 
	
def pressure_Mao_NH(w0, w,T):
	A  = 1904. #GPa
	B  = 5.
	# w0 = 694.24 #nm, at 298 K 
	w_corr = temperature_correction(w0, w,T)
	P = A/B * ((w_corr/w0)**B -1)
	return P 
	
def pressure_Rashchenko_H(w0, w):
	# Rashchenko et al. JAP 117 - 145902 (2015) - up to 120 GPa, using Sm:SrB4O7
	delta_w = w - w0
	P = 4.20 * delta_w * (1.0 + 0.020*delta_w)/(1.0 + 0.036*delta_w)
	return P
	
def pressure_Jing_NH(w0, w):
	# Jing et al. JAP 113 - 023507 (2013) - Non hydrostatic - up to 127 GPa, using samarium Sm:SrB4O7
	delta_w = w - w0
	P = 3.953*delta_w * (1.0 + 0.0044*delta_w)/(1.0 + 0.0120*delta_w)
	return P

def read_ascii_data(datafile):
	data = np.loadtxt(datafile)
	wavelength = data[:,0]
	intensity = data[:,1]
	return (wavelength, intensity)
	
def read_csv_file(datafile):
	data=[]
	with open(datafile,'rb') as csvfile:
		cv=csv.reader(csvfile)
		cv.next()
		for row in cv:
			r=row[0].split(";")
			data.append([float(r[1]), float(r[2].split("'")[0])])
	data = np.array(data)
	return (data[:,0], data[:,1])
	
if __name__=="__main__":
	
	datafile_ref = "NEON_LINES.dat"
	datafile = "Neon.dat"
	data = np.loadtxt(datafile)
	ref  = np.loadtxt(datafile_ref)
	wavelength, intensity = data[:,0], data[:,1]
	WL = ref
	intensity = intensity/intensity.max()
	# wavelength,intensity = read_csv_file(datafile)
	# if model =="ruby":
		# fit_param,fit_data = ruby_fit(wavelength,intensity)
	# elif model=="neon":
		# fit_param,fit_data = neon_fit(wavelength,intensity, 0.13)
	fit_param,fit_data = neon_fit(wavelength,intensity, 0.055)
	# f=figure()
	# ax=f.add_subplot(111)
	# ax.plot(wavelength, intensity, "ko")
	# ax.plot(wavelength, fit_data, "r-")
	# ax.bar(WL, INT, width=0.3, color="b")
	# show()
	nbr_peaks = len(fit_param.keys()) -1 
	nbr_peaks = nbr_peaks/4 
	fitted_wl = []
	fitted_in = []
	for i in range(nbr_peaks):
		wl = fit_param["X%d"%i].value
		inten = neon_model(fit_param, wl)
		fitted_wl.append(wl)
		fitted_in.append(inten)
	fitted_wl = np.array(fitted_wl)
	fitted_in = np.array(fitted_in)
	f2=figure()
	ax2=f2.add_subplot(111)
	ax2.plot(wavelength, intensity, "k-")
	# ax2.bar(fitted_wl, fitted_in, width=0.2, color="red")
	ax2.plot(wavelength, fit_data, "r-")
	for i in range(len(WL)):
		ax2.axvline(WL[i],color="g")
	true_ind = peak.get_index_from_values(WL, fitted_wl)
	true_wl  = WL[true_ind]
	for i in range(len(true_wl)):
		ax2.text(fitted_wl[i], 0.2, str(round(true_wl[i],3)))
	show()