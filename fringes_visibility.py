import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
from scipy.ndimage.filters import gaussian_filter1d
from PIL import Image
import time

fringes = np.array(Image.open('fringes.tif'))[:, :, 0]


def get_visibility(fringes):
    fringes[0:10, :] = 0
    fringes[:, 0:10] = 0
    fringes[-10:-1, :] = 0
    fringes[:, -10:-1] = 0
    max_i, max_j = np.where(fringes == np.max(fringes))
    max_i = max_i[0]
    max_j = max_j[0]
    fringes[max_i, max_j]
    # plt.imshow(fringes)
    # plt.scatter(max_j, max_i)
    # plt.show()
    slc = fringes[max_i, :]
    slc = gaussian_filter1d(slc, 2)
    # plt.plot(slc)
    min_j, r = signal.find_peaks(-slc)
    closest_j = min_j[np.abs(min_j-max_j) == np.min(np.abs(min_j-max_j))][0]
    visibility = (fringes[max_i, max_j] - fringes[max_i, closest_j]) / \
                 (fringes[max_i, max_j] + fringes[max_i, closest_j])
    return visibility


t0 = time.time()
vis = get_visibility(fringes)
t1 = time.time()-t0
print(f"Fringes visibility is {'{:.2%}'.format(vis)}  (took {'{:.4}'.format(t1)} s)")
