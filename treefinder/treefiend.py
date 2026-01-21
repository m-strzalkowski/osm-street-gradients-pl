import rasterio
import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage
from PIL import Image


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
#The same thing, but fast
def f_fast(im, khalf=1):
    size = 2 * khalf + 1
    return ndimage.uniform_filter(im, size=size, mode='nearest')

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
#Functionally the same thing, but doesn't compute local deviances for each pixel separately, but factors that out
def fm_fast(im, khalf=5):
    size = 2 * khalf + 1

    local_max = ndimage.maximum_filter(im, size=size, mode='nearest')
    local_min = ndimage.minimum_filter(im, size=size, mode='nearest')

    return np.maximum(
        local_max - im,
        im - local_min
    )

def drz(im, a_max=1.0):
    return np.clip(f_fast(fm_fast(im, khalf=1), khalf=1), a_min=0, a_max= 1.0)

def read_tiff(fname):
    f = rasterio.open(fname)
    b = f.read(1)
    return f,b

def save_array_as_geotiff_with_meta_from_other_file(src_path, out_path, data, dtype='float32'):
    with rasterio.open(src_path) as src:
        meta = src.meta.copy()

    meta.update(dtype='float32', count=1, compress='deflate')

    with rasterio.open(out_path, 'w', **meta) as dst:
        dst.write(data.astype('float32'), 1)

def save_aux_pngs(out_path, img, img_bin1, img_bin2):
    from PIL import Image
    im = Image.fromarray((img*255).astype('uint8'))
    im.save(out_path+".png")
    if img_bin1 is not None:
        im = Image.fromarray(((img_bin1)*255).astype('uint8'))
        im.save(out_path+".binarized.png")
    if img_bin2 is not None:
        im = Image.fromarray(((img_bin2)*255).astype('uint8'))
        im.save(out_path+".binarized_morph.png")

def n_erode_dilate(mask, khalf=1, n_iter=2):
    """
    mask   : binary image (0/1 or bool)
    khalf  : half-size of structuring element
    n_iter : how many times to erode then dilate
    """
    mask = mask.astype(bool)

    size = 2 * khalf + 1
    structure = np.ones((size, size), dtype=bool)

    out = mask
    for _ in range(n_iter):
        out = ndimage.binary_erosion(out, structure=structure)

    for _ in range(n_iter):
        out = ndimage.binary_dilation(out, structure=structure)

    return out.astype(np.uint8)

def generate_roughness(in_path , out_path, save_also_png=False, binarize_and_postprocess=True):
    """
    in_path: must be GeoTiff, metadata will be copied
    """
    THRESH = 1.0
    f,img = read_tiff(in_path)
    f.close()
    img_trans = drz(img)
    img_bin = img_trans>=THRESH
    img_bin_morph = n_erode_dilate(img_bin, khalf=1, n_iter=2)

    if binarize_and_postprocess:
        img_out = img_bin_morph.astype(np.uint8)
    else:
        img_out = img_trans
    save_array_as_geotiff_with_meta_from_other_file(in_path, out_path, img_out,
                                    dtype=img_out.dtype)
    if save_also_png:
        save_aux_pngs(out_path, img_trans, img_bin, img_bin_morph)
    return img_out

if __name__ == '__main__':
    help = 'Usage: treefiend.py <input-path.tif> <output-path.tif>'
    import sys, os
    from os.path import join
    if len(sys.argv) == 3:
        generate_roughness(sys.argv[1], sys.argv[2], save_also_png = True)
    elif len(sys.argv) == 2:
        if sys.argv[1] == '--test':
            prefix = os.path.dirname(__file__)
            generate_roughness(join(prefix,'tile_example1.tif'), join(prefix,'tile_example1.doubt.tif'), save_also_png = True)
            generate_roughness(join(prefix, 'zoo.tif'), join(prefix,'zoo.doubt.tif'), save_also_png = True)
    else:
        print(help, file=sys.stderr)
        exit(1)