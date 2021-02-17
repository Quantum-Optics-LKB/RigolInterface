import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import scipy.signal as signal
from scipy.ndimage.filters import gaussian_filter1d
from PIL import Image
import time

fringes = np.array(Image.open('fringes.tif'))[:, :, 0]


def get_visibility(fringes):
    fringes_c = fringes
    del fringes
    fringes_c[0:10, :] = 0
    fringes_c[:, 0:10] = 0
    fringes_c[-10:-1, :] = 0
    fringes_c[:, -10:-1] = 0
    max_i, max_j = np.where(fringes_c == np.max(fringes_c))
    max_i = max_i[0]
    max_j = max_j[0]
    fringes_c[max_i, max_j]
    # plt.imshow(fringes_c)
    # plt.scatter(max_j, max_i)
    # plt.show()
    slc = fringes_c[max_i, :]
    slc = gaussian_filter1d(slc, 2)
    # plt.plot(slc)
    min_j, r = signal.find_peaks(-slc)
    closest_j = min_j[np.abs(min_j-max_j) == np.min(np.abs(min_j-max_j))][0]
    visibility = (fringes_c[max_i, max_j] - fringes_c[max_i, closest_j]) / \
                 (fringes_c[max_i, max_j] + fringes_c[max_i, closest_j])
    return visibility


t0 = time.time()
vis = get_visibility(fringes)
t1 = time.time()-t0
print(f"Fringes visibility is {'{:.2%}'.format(vis)}  (took {'{:.4}'.format(t1)} s)")
fig, ax = plt.subplots(1, 2)
xs = list(range(0, 200))
ys = [0] * len(xs)
ax[1].set_ylim((0, 100))
im = ax[0].imshow(fringes, vmin=0, vmax=255)
line, = ax[1].plot(xs, ys)
ax[0].set_title("Camera")
ax[1].set_title("Fringe visibility")
ax[1].set_xlabel("Samples")
ax[1].set_ylabel("Visibility in %")


def animate(i, ys):
    frame = np.random.randint(size=(2048, 2048), low=0, high=256)
    im.set_data(frame)
    vis = get_visibility(frame)

    # Add y to list
    ys.append(100*vis)

    # Limit y list to set number of items
    ys = ys[-len(xs):]

    # Update line with new Y values
    line.set_ydata(ys)

    return im, line,


ani = FuncAnimation(fig,
                    animate,
                    fargs=(ys,),
                    interval=50,
                    blit=True)
plt.show()
