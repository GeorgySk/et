import numpy as np
from pycbc.waveform import get_td_waveform

APPROXIMANT = 'IMRPhenomD'
MASS_1 = 30
MASS_2 = 30
SAMPLE_RATE = 8192
F_LOWER = 10

if __name__ == '__main__':
    hp, _ = get_td_waveform(approximant=APPROXIMANT,
                            mass1=MASS_1,
                            mass2=MASS_2,
                            delta_t=1. / SAMPLE_RATE,
                            f_lower=F_LOWER)
    np.savetxt('template.csv', hp)
