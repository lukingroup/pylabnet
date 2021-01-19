"""
This contains a numerical model for stimulated single photon emission from cavity-coupled SiV-
Author: Wenjie Gong
Updated: 12/07/2020
"""
import numpy as np
import matplotlib.pyplot as plt
from qutip import *
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter, find_peaks

def main():
    return 0

def make_fig(xTitle="xTitle",yTitle="yTitle"):
    SMALL_SIZE = 14
    BIGGER_SIZE = 16
    plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
    plt.rc('axes', titlesize=BIGGER_SIZE)     # fontsize of the axes title
    plt.rc('axes', labelsize=BIGGER_SIZE)    # fontsize of the x and y labels
    plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
    plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
    plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
    plt.rc('lines', linewidth = 3)
    plt.rc('figure', figsize= (7, 5))
    fig = plt.figure()
    ax = plt.gca()
    #ax.set_prop_cycle(color=['#002BFF','#A15FFF','#FF0061','#FF8913'])
    ax.set_xlabel(xTitle,labelpad=6)
    ax.set_ylabel(yTitle)
    ax.tick_params(direction='out', length=8, width=2)
    ax.yaxis.offsetText.set_fontsize(10)
    ax.tick_params(axis='both', which='major', labelsize=15)
    return fig, ax

def gaussian(x, amp, mu, sigma):
    '''
    :param x: array of x values
    :param amp: amplitude
    :param mu: mean
    :param sigma: standard deviation
    '''
    return  amp*np.exp(-(1./2.)*((x-mu)/sigma)**2)

def square_pulse(t, amp, rise, fall):
    '''
    param t: times, np array please
    args[amp]: amplitude of square pulse
    args[rise]: time of rising edge
    args[fall]: time of falling edge
    '''
    sig_r = rise/3.
    sig_f = fall/3
    
    index_r = np.where(t > rise)[0][0]
    index_f = np.where(t > t[-1] - fall)[0][0]
    
    t_r = t[0:index_r]
    t_f = t[index_f:]
    t_bod = t[index_r:index_f]
    
    pulse_r = gaussian(t_r, amp, t_r[-1], sig_r)
    pulse_f = gaussian(t_f, amp, t_f[0], sig_f)
    pulse_b = amp*np.ones(shape(t_bod))
    pulse = np.concatenate((pulse_r, pulse_b, pulse_f), axis = 0)
    return pulse

def sqrt_sq_pulse(t, *args):
    '''
    :param args: arguments for square pulse function
    '''
    return np.sqrt(square_pulse(t, *args))

def sqrt_gaussian(t, *args):
    '''
    :param args: arguments for gaussian function
    '''
    return np.sqrt(gaussian(t, *args))

def n_gaussian(times, *params):
    '''
    :param times: array of x values to evaluate 
    :param params: n amplitudes, n mus, and n sigmas for the n gaussians
    (provided times will automatically be split up into even intervals)
    '''
    n = int(len(params)/3)
    amps = params[0:n]
    mus = params[n:2*n]
    sigmas = params[2*n:]
    interv = int(len(times)/n)
    time_t1 = times[:interv]
    time_t2 = times[interv*(n-1):]
    time_t2 = time_t2 - time_t2[0]
    #print(interv)
    
    gaussians = []
    for i in range(n):
        if i < n - 1:
            gaussians.append(gaussian(time_t1, amps[i], mus[i], sigmas[i]))
        else:
            gaussians.append(gaussian(time_t2, amps[i], mus[i], sigmas[i]))
    pulse= np.concatenate(gaussians, axis = 0)
    return pulse

def sqrt_n_gaussian(times, *params):
    '''
    :param params: same paramters as n_gaussian
    '''
    return np.sqrt(n_gaussian(times, *params))




# GLOBAL VARIABLES
zero_zero = tensor(basis(3, 0), basis(2, 0))
zero_one = tensor(basis(3, 0), basis(2, 1))
one_zero = tensor(basis(3, 1), basis(2, 0))
one_one = tensor(basis(3, 1), basis(2, 1))
two_zero = tensor(basis(3, 2), basis(2, 0))
two_one = tensor(basis(3, 2), basis(2, 1))

L1 = zero_zero*zero_one.dag()
L2 = zero_zero*two_zero.dag()
L3 = one_zero*two_zero.dag()

# define parameters of cavity-coupled SiV- system
class cSIV:

    def __init__(self, g, kappa, gamma, gammaf, nu = 406706*np.pi, omega12 = 406706*np.pi, omegaC = 406706*np.pi):
        '''
        :param nu: frequency of applied EM field
        :param omega12: transition from |1> to |2>
        :param omegaC: transition between |0> and cavity
        :param g: g for cavity
        :param kappa: kappa for cavity
        :param gamma: rate of spontaneous emission from |2> to |0>
        :param gammaf: rate of spontaneous emission from |2> to |1>
        '''
        self.g = g
        self.kappa = kappa
        self.gamma = gamma
        self.gammaf = gammaf
        self.nu = nu
        self.omega12 = omega12
        self.omegaC = omegaC
        self.Delta1 = nu - omega12
        self.deltaAC = omega12-omegaC

    def make_ham_spline(self, times, pulse):
        '''
        :param times: time axis of pulse (Omega)
        :param pulse: y data for applied pulse
        :type times: numpy array
        :type pulse: numpy array
        '''
        #Hamiltonian
        H0 = self.Delta1*two_zero*two_zero.dag() + (self.Delta1 - self.deltaAC)*zero_one*zero_one.dag() \
        + self.g*zero_one*two_zero.dag() + np.conj(self.g)*two_zero*zero_one.dag()

        H1 = two_zero*one_zero.dag()
        H2 = one_zero*two_zero.dag()
        
        S = Cubic_Spline(times[0], times[-1], pulse)
        S_conj = Cubic_Spline(times[0], times[-1], np.conj(pulse))
        
        H = [H0, [H1, S], [H2, S_conj]]
        return H

    def solve_me(self, H, psi_0, times):
        '''
        :param H: hamiltonian to simulate
        :param psi_0: initial state of system
        :param times: times to simulate
        :type H: hamiltonian returned from make_ham_spline
        :type psi_0: QuTiP quantum object
        :type times: numpy array
        '''
        kappa = self.kappa
        gamma = self.gamma
        gammaf = self.gammaf

        c_ops = [np.sqrt(kappa)*L1, np.sqrt(gamma)*L2, np.sqrt(gammaf)*L3]
        
        zero_zero_pop = zero_zero*zero_zero.dag()
        one_zero_pop = one_zero*one_zero.dag()
        two_zero_pop = two_zero*two_zero.dag()
        zero_one_pop = zero_one*zero_one.dag()
        photon_pop = zero_one*two_zero.dag()
        
        m_ops = [zero_zero_pop, one_zero_pop, two_zero_pop, zero_one_pop, photon_pop]
        solutions = mesolve(H, psi_0, times, c_ops, m_ops)
        return solutions.expect

    def sim(self, times, *args):
        psi_0 = one_zero
        if self.fit_print:
            print(args)
        pulse = self.pulse_func(times, *args)
        H = self.make_ham_spline(times, pulse)
        soln = self.solve_me(H, psi_0, times)
        return abs(self.kappa*soln[3])/max(abs(self.kappa*soln[3]))

    def fit_data(self, pulse_func, x, y, p0, bounds, fit_print = False, **kwargs):
        self.pulse_func = pulse_func
        self.fit_print = fit_print
        popt, pcov = curve_fit(self.sim, x, y, p0=p0, bounds= bounds, **kwargs)
        plt.figure()
        plt.plot(x, y, label = "data")
        plt.plot(x, self.sim(x, *popt), label = "sim fit")
        plt.xlabel("Times (ns)")
        plt.ylabel("Photon Count")
        plt.legend()
        plt.show()
        return popt, pcov

    def retro_n_gauss(self, times, photon, sigmas, means = None, fit_print = False):
        '''
        :param times: np array of the times
        :param photon: np array of the photon shape (n gaussians)
        :param sigmas: array of the n sigmas of the n gaussians
        '''
        n = len(sigmas)
        if not means:
            time_mean = np.take(times, find_peaks(photon)[0])
            interv = int(len(times)/n)
            t_interv = times[interv-1]
            
            means = []
            for i in range(len(time_mean)):
                time_bef = i*t_interv
                means.append(time_mean[i] - time_bef)

        print(means)

        photon = photon/max(photon)
        p0amp = np.linspace(0, 0.7, n)
        p0 = np.array([*p0amp, *means, *sigmas])
        lower_bound = [0]*(3*n)
        upper_bound = [*[5]*n, *[max(means)+1]*n, *[max(sigmas)+1]*n]
        
        popt, pcov = self.fit_data(sqrt_n_gaussian, times, photon, p0, bounds=(lower_bound, upper_bound),\
                                 fit_print = fit_print, method = 'trf', diff_step = 0.1)
        amps_an = popt[:n]
        means_an = popt[n:2*n]
        sigmas_an = popt[2*n:]
        
        return {"amps": amps_an, "means": means_an, "sigmas": sigmas_an}, popt, pcov