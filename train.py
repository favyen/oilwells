import model as model

import json
import numpy
import os, os.path
import random
import skimage.io, skimage.transform
import sys
import tensorflow as tf
import time

Size = 256
MaskSize = 32

all_tiles = {}
for fname in os.listdir('images/'):
	if not fname.endswith('.jpg'):
		continue
	label = fname.split('.jpg')[0]
	parts = label.split('_')
	x = int(parts[0])
	y = int(parts[1])
	im = skimage.io.imread('images/'+label+'.jpg')
	mask = skimage.io.imread('images/'+label+'.png')
	mask = skimage.transform.resize(mask, [MaskSize, MaskSize], order=0, preserve_range=True).astype('uint8')
	all_tiles[(x, y)] = (im, mask)

examples = []
for ((x, y), (im, mask)) in all_tiles.items():
	if numpy.count_nonzero(mask) < 32:
		continue

	ok = True
	big_im = numpy.zeros((3*Size, 3*Size, 3), dtype='uint8')
	big_mask = numpy.zeros((3*MaskSize, 3*MaskSize), dtype='uint8')
	for ox in [-1, 0, 1]:
		for oy in [-1, 0, 1]:
			if (x+ox, y+oy) not in all_tiles:
				ok = False
				continue
			big_im[(oy+1)*Size:(oy+2)*Size, (ox+1)*Size:(ox+2)*Size, :] = all_tiles[(x+ox, y+oy)][0]
			big_mask[(oy+1)*MaskSize:(oy+2)*MaskSize, (ox+1)*MaskSize:(ox+2)*MaskSize] = all_tiles[(x+ox, y+oy)][1]
	if not ok:
		continue
	examples.append((big_im, big_mask, (x, y)))

model_path = 'model/model'

random.shuffle(examples)
val_examples = [example for example in examples if example[2][0] < 29898]
train_examples = [example for example in examples if example[2][0] > 29898]

def prepare(example):
	big_im = example[0]
	big_mask = example[1]
	x = random.randint(MaskSize-MaskSize//4, MaskSize+MaskSize//4)
	y = random.randint(MaskSize-MaskSize//4, MaskSize+MaskSize//4)
	factor = Size//MaskSize
	im = big_im[y*factor:y*factor+Size, x*factor:x*factor+Size, :]
	mask = big_mask[y:y+MaskSize, x:x+MaskSize]

	# random rotation
	rotations = random.randint(0, 3)
	if rotations > 0:
		im = numpy.rot90(im, k=rotations)
		mask = numpy.rot90(mask, k=rotations)

	return im, mask

val_prepared = [prepare(example) for example in val_examples]

# train
m = model.Model(256, 256)
session = tf.Session()
session.run(m.init_op)
batch_size = 32
best_loss = None
for epoch in range(9999):
	start_time = time.time()
	train_losses = []
	for i in range(256):
		batch = [prepare(example) for example in random.sample(examples, batch_size)]
		_, loss = session.run([m.optimizer, m.loss], feed_dict={
			m.inputs: [example[0] for example in batch],
			m.targets: [example[1] for example in batch],
			m.learning_rate: 1e-3,
			m.is_training: True,
		})
		train_losses.append(loss)
	train_loss = numpy.mean(train_losses)
	train_time = time.time()

	val_losses = []
	for i in range(0, len(val_prepared), batch_size):
		batch = val_prepared[i:i+batch_size]
		loss = session.run(m.loss, feed_dict={
			m.inputs: [example[0] for example in batch],
			m.targets: [example[1] for example in batch],
			m.is_training: False,
		})
		val_losses.append(loss)

	val_loss = numpy.mean(val_losses)
	val_time = time.time()

	print(
		'iteration {}: train_time={}, val_time={}, train_loss={}, val_loss={}/{}'.format(
		epoch, int(train_time - start_time), int(val_time - train_time), train_loss, val_loss, best_loss
	))

	if best_loss is None or val_loss < best_loss:
		best_loss = val_loss
		m.saver.save(session, model_path)

def test():
	for i, example in enumerate(val_prepared):
		im = example[0]
		mask = example[1]
		output = session.run(m.outputs, feed_dict={
			m.inputs: [im],
			m.is_training: False,
		})[0, :, :]
		skimage.io.imsave('/home/ubuntu/vis/{}_im.jpg'.format(i), im)
		skimage.io.imsave('/home/ubuntu/vis/{}_mask.png'.format(i), skimage.transform.resize(mask, [Size, Size], order=0, preserve_range=True).astype('uint8'))
		skimage.io.imsave('/home/ubuntu/vis/{}_out.png'.format(i), (skimage.transform.resize(output, [Size, Size], order=0)*255).astype('uint8'))

def apply():
	m = model.Model(2048, 2048)
	session = tf.Session()
	m.saver.restore(session, model_path)
	im = skimage.io.imread('tile.jpg')
	output = numpy.zeros((im.shape[1], im.shape[0]), dtype='uint8')
	for x in range(0, im.shape[1], 2048):
		for y in range(0, im.shape[0], 2048):
			print(x, y)
			cur_output = session.run(m.outputs, feed_dict={
				m.inputs: [im[y:y+2048, x:x+2048, :]],
				m.is_training: False,
			})[0, :, :]
			cur_output *= 255
			cur_output = skimage.transform.resize(cur_output, [2048, 2048], order=0, preserve_range=True)
			output[y:y+2048, x:x+2048] = cur_output.astype('uint8')
	skimage.io.imsave('out.png', cur_output)
