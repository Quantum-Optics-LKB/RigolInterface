# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:47:25 2021

@author: Tangui ALADJIDI
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os
from ScopeInterface import USBScope

rigol = USBScope()
rigol.get_waveform(channels=[1, 2, 3, 4], plot=True)
rigol.close()
