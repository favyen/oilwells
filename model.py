import numpy
import tensorflow as tf
import os
import os.path
import random
import math
import time

class Model:
	def __init__(self, width, height):
		tf.reset_default_graph()
		self.inputs = tf.placeholder(tf.uint8, [None, height, width, 3])
		self.targets = tf.placeholder(tf.uint8, [None, height//8, width//8])
		self.learning_rate = tf.placeholder(tf.float32)
		self.is_training = tf.placeholder(tf.bool)

		cur = tf.cast(self.inputs, tf.float32)/255.0
		for features in [32, 64, 128, 256, 256]:
			cur = tf.keras.layers.Conv2D(
				features, (4, 4),
				strides=2, activation='relu', padding='same'
			)(cur)
		cur = tf.keras.layers.Conv2D(
			256, (4, 4),
			activation='relu', padding='same'
		)(cur)
		for features in [256, 256]:
			cur = tf.keras.layers.Conv2DTranspose(
				features, (4, 4),
				strides=2, activation='relu', padding='same'
			)(cur)
		self.pre_outputs = tf.keras.layers.Conv2D(
			1, (4, 4),
			padding='same'
		)(cur)[:, :, :, 0]
		self.outputs = tf.nn.sigmoid(self.pre_outputs)

		targets = tf.cast(self.targets > 128, tf.float32)
		self.loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=targets, logits=self.pre_outputs))

		with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
			self.optimizer = tf.train.AdamOptimizer(learning_rate=self.learning_rate).minimize(self.loss)

		self.init_op = tf.global_variables_initializer()
		self.saver = tf.train.Saver(max_to_keep=None)
