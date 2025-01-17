# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:47:25 2021

@author: Tangui ALADJIDI
"""

import numpy as np
# import time
from RigolInterface import Scope
from RigolInterface import ArbitraryFG

##### SCOPE EXAMPLE #####
rigol = Scope("TCPIP::169.254.63.138::INSTR")
# N_repet = 100
# ts = np.zeros(N_repet)
# for _ in range(N_repet):
#     t0 = time.perf_counter()
#     times, channel = rigol.get_waveform_better(channel=1, plot=False)
#     ts[_] = time.perf_counter()-t0
# print(f"Avg time per read {np.mean(ts)*1e3} +/- {np.std(ts)*1e3} ms")
data = rigol.get_waveform([1, 2], plot=True, ndivs=14)
rigol.close()


##### ARBITRARYFG EXAMPLE #####
rigol = ArbitraryFG('USB0::0x1AB1::0x0641::DG4E221700344::0::INSTR')

rigol.set_impedance(output = 1, load = 'INF')

rigol.dc_offset(output = 1, offset = 5.0)

rigol.turn_off(output = 1)

rigol.close()
