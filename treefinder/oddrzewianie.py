# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %%
import rasterio
import numpy as np
import matplotlib.pyplot as plt

# %%
f = rasterio.open('../tiles/tile_example1.tif')

# %%
b = f.read(1)

# %%
br = np.rot90(b)
print(br.shape)
def sv(img, name):
    plt.figure(figsize=(8,4))
    plt.imshow(img, interpolation='None')
    plt.colorbar()
    plt.savefig(name)
sv(br[1100:1600, 500:1400], 'drzewa1.png')


# %%
#Just convolution with kernel with each elem = 1/(khalf*2+1)**2
def f(im, khalf=1):
    imo = np.zeros(im.shape)
    for y in range(im.shape[0]):
        for x in range(im.shape[1]):
            ly, hy = max(0, y-khalf), min(im.shape[0], y+khalf)
            lx, hx = max(0, x-khalf), min(im.shape[1], x+khalf)
            kern = im[ly:hy+khalf, lx:hx+khalf]
            imo[y,x] = np.average(kern)#/(kern.shape[0]*kern.shape[1])
    return imo



# %%
from scipy import ndimage
def f_fast(im, khalf=1):
    size = 2 * khalf + 1
    return ndimage.uniform_filter(im, size=size, mode='nearest')


# %%
sv(f_fast(br[1100:1600, 500:1400], khalf=1), 'drzewa2_rozmyte.png')

# %%
sv(f_fast(br[1100:1600, 500:1400], khalf=2), 'drzewa2_rozmyte2.png')


# %%
def fm1(im, khalf=5):
    imo = np.zeros(im.shape)
    for y in range(im.shape[0]):
        for x in range(im.shape[1]):
            ly, hy = max(0, y-khalf), min(im.shape[0], y+khalf)
            lx, hx = max(0, x-khalf), min(im.shape[1], x+khalf)
            kern = im[ly:hy+khalf, lx:hx+khalf]
            kern = kern - im[y,x]
            imo[y,x] = np.max(kern)#/(kern.shape[0]*kern.shape[1])
    return imo
sv(fm1(br[1100:1600, 500:1400], khalf=1), 'drzewa3_max.png')


# %%
#Look at differences between the pixel and surroundings, take max difference
def fm(im, khalf=5):
    imo = np.zeros(im.shape)
    for y in range(im.shape[0]):
        for x in range(im.shape[1]):
            ly, hy = max(0, y-khalf), min(im.shape[0], y+khalf)
            lx, hx = max(0, x-khalf), min(im.shape[1], x+khalf)
            kern = im[ly:hy+khalf, lx:hx+khalf]
            kern = np.abs(kern - im[y,x])
            imo[y,x] = np.max(kern)#/(kern.shape[0]*kern.shape[1])
    return imo
sv(fm(br[1100:1600, 500:1400], khalf=1), 'drzewa3_max_abs.png')

# %%
from scipy import ndimage

def fm_fast(im, khalf=5):
    size = 2 * khalf + 1

    local_max = ndimage.maximum_filter(im, size=size, mode='nearest')
    local_min = ndimage.minimum_filter(im, size=size, mode='nearest')

    return np.maximum(
        local_max - im,
        im - local_min
    )



# %%
sv(fm_fast(br, khalf=1)[1100:1600, 500:1400], 'drzewa3_max_abs_fast.png')

# %%
sv(fm_fast(br[1100:1600, 500:1400], khalf=2), 'drzewa3_max_2m.png')

# %%
sv(f_fast(fm_fast(br[1100:1600, 500:1400], khalf=2), khalf=1), 'drzewa3_max_2m_rozmyte1.png')


# %%
def drz1(im):
    return np.clip(f_fast(fm1(im, khalf=2), khalf=1), a_min=0, a_max= 1.0)
sv(drz1(br[1100:1600, 500:1400]), 'drzewa3_max_2m_rozmyte1_clip_noabs.png')
def drz(im, a_max=1.0):
    return np.clip(f_fast(fm_fast(im, khalf=2), khalf=1), a_min=0, a_max= 1.0)
sv(drz(br[1100:1600, 500:1400]), 'drzewa3_max_2m_rozmyte1_clip.png')

# %%
sv(dbr:=drz(br), 'wszechoddrzewianie.png')

# %%
from PIL import Image
im = Image.fromarray((dbr*255).astype('uint8'))
im.save("wszechoddrzewianie_duze.png")

# %%
from PIL import Image
im = Image.fromarray(((dbr>=1)*255).astype('uint8'))
im.save("wszechoddrzewianie_duze_max.png")

# %% [markdown]
# ## Test: jaką wartość osiąga funkcja na podjeździe 25%?

# %%
podjazd = np.zeros((10, 100))
y=-1; x=-1;
while y<podjazd.shape[0]-1:
    y+=1
    while x<podjazd.shape[1]-1:
        x+=1
        podjazd[:,x] = x*0.25

# %%
plt.imshow(podjazd)
#plt.colorbar()

# %%
plt.imshow(drz(podjazd))
plt.colorbar()

# %%
