import lal
from lal import MSUN_SI as Msun
from lalsimulation import SimIMRPhenomDChirpTime
import pandas as pd
from gwpy.timeseries import TimeSeries
# Choose the top few signals to plot
Nplot = 1
signals = pd.read_csv('list_etmdc1_snr.txt', sep=' ')
top_sigs = signals.iloc[:Nplot]

def read_without_warnings(cachefile, channel, **kwargs):
    """Reads cache file while suppressing spurious LAL warnings.
    Wraps gwpy.timeseries.TimeSeries.read

    Args:
        cachefile (str): path to cache file
        channel (str): Channel name
        **kwargs: additional arguments passed to TimeSeries.read
    """
    prev_level = lal.GetDebugLevel()
    lal.ClobberDebugLevel(0)
    result = TimeSeries.read(cachefile, channel, **kwargs)
    lal.ClobberDebugLevel(prev_level)
    return result

def get_strain(tc, t_before = 4, t_after = 1):
    start_time = tc - t_before
    end_time = tc + t_after
    h = read_without_warnings('caches/E1-local.lcf','E1:STRAIN',start=start_time, end=end_time)
    return h

def plot_specgram2(h):
    specgram = h.spectrogram2(fftlength=1/10,overlap=1/50)**(1/2)
    return specgram


def main():
    for idx, pars in top_sigs.iterrows():
        tc =pars['tc']
        m1 = pars['m1']
        m2 = pars['m2']
        f_min = 10
        chirplen = SimIMRPhenomDChirpTime(pars['m1']*Msun, pars['m2']*Msun, pars['s1z'], pars['s2z'], f_min )
        print(f'Inj {int(pars["#"])}, tc {pars["tc"]}, Masses: {pars["m1"],pars["m2"]}, chirp length {chirplen} s, SNR {pars["SNR"]}')
        h = get_strain(tc, t_before=max(4,min(30,chirplen)))
        sg = h.spectrogram2(fftlength=1/10)**(1/2)
        plot = sg.plot(norm='log', yscale='log',
                       title=f'$t_c={tc}$, ($m_1$,$m_2$) = ({pars["m1"]:.1f},{pars["m2"]:.1f}) $M_\odot$, SNR={pars["SNR"]}',
                       ylim=(10,1000))
        ax = plot.gca()
        ax.colorbar(
            label=r'Gravitational-wave amplitude [strain/$\sqrt{\mathrm{Hz}}$]')
        h.plot()
    plt.show()