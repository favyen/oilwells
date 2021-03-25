import numpy
import skimage.io

sx = 29767
sy = 54637
ex = sx+32
ey = sy+32

im = numpy.zeros((8192, 8192, 3), dtype='uint8')
for x in range(sx, ex):
    for y in range(sy, ey):
        ox = x-sx
        oy = y-sy
        im[oy*256:(oy+1)*256, ox*256:(ox+1)*256, :] = skimage.io.imread('images2/{}_{}.jpg'.format(x, y))
skimage.io.imsave('tile.jpg', im)
