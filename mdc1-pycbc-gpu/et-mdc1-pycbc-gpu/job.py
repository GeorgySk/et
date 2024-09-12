import lal
import numpy as np
import pandas as pd
from gwpy.timeseries import TimeSeries
from pycbc.psd import interpolate, inverse_spectrum_truncation
from pycbc.filter import resample_to_delta_t, highpass, matched_filter
from pycbc.types import TimeSeries as PyCBCTimeSeries
from pycbc.waveform import get_td_waveform

from urllib.parse import urlencode

METADATA_PATH = '/bmk/build/et/list_etmdc1_snr.txt'
MDC_PATH = "/bmk/build/et/data"
DATASETS = ['E0','E1','E2','E3','C1','C2']
CHANNELS = {n : f'{n}:STRAIN' for n in DATASETS}
INDEX = 0


def get_strain(tc, t_before=4, t_after=1):
    start_time = tc - t_before
    end_time = tc + t_after
    return read_without_warnings('/bmk/build/et/caches/E1-local.lcf',
                                 'E1:STRAIN',
                                 start=start_time,
                                 end=end_time)


def read_without_warnings(cachefile, channel, **kwargs):
    prev_level = lal.GetDebugLevel()
    lal.ClobberDebugLevel(0)
    result = TimeSeries.read(cachefile,
                             channel,
                             **kwargs)
    lal.ClobberDebugLevel(prev_level)
    return result


def main():
    signals = pd.read_csv(METADATA_PATH, sep=' ')
    tc = signals['tc'][INDEX]
    h = get_strain(tc,
                   t_before=16,
                   t_after=16)

    fs = 8192
    time_step = 1 / fs
    start_time = tc - 16
    strain = PyCBCTimeSeries(np.array(h),
                             delta_t=time_step,
                             epoch=start_time)
    strain = highpass(strain, 15.0)
    strain = resample_to_delta_t(strain, 1.0 / 2048)
    conditioned = strain.crop(2, 2)

    psd = conditioned.psd(4)
    psd = interpolate(psd, conditioned.delta_f)
    psd = inverse_spectrum_truncation(psd,
                                      int(4 * conditioned.sample_rate),
                                      low_frequency_cutoff=15)
    m = 24  # Solar masses
    hp, hc = get_td_waveform(approximant='IMRPhenomD',
                             mass1=m,
                             mass2=m,
                             delta_t=conditioned.delta_t,
                             f_lower=20)
    hp.resize(len(conditioned))
    template = hp.cyclic_time_shift(hp.start_time)
    snr = matched_filter(template,
                         conditioned,
                         psd=psd,
                         low_frequency_cutoff=20)
    snr = snr.crop(4 + 4, 4)
    peak = abs(snr).numpy().argmax()
    snrp = snr[peak]
    time = snr.sample_times[peak]



if __name__ == '__main__':
    main()
