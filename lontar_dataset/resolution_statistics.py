import os
import numpy as np
from PIL import Image

directory_train = 'train_image'
img_width_train = []
img_height_train = []

for filename in os.listdir(directory_train):
    file = os.path.join(directory_train, filename)
    im = Image.open(file)
    if os.path.isfile(file):
        img_width_train.append(im.width)
        img_height_train.append(im.height)

avg_train = (np.round(np.average(img_width_train), 1), np.round(np.average(img_height_train), 1))
stdev_train = ((np.round(np.std(img_width_train), 1), np.round(np.std(img_height_train), 1)))
min_train = ((np.round(np.amin(img_width_train), 1), np.round(np.amin(img_height_train), 1)))
max_train = ((np.round(np.amax(img_width_train), 1), np.round(np.amax(img_height_train), 1)))

directory_test = 'test_image'
img_width_test = []
img_height_test = []

for subdirectory in os.listdir(directory_test):
    for filename in os.listdir(os.path.join(directory_test, subdirectory)):
        file = os.path.join(directory_test, os.path.join(subdirectory, filename))
        im = Image.open(file)
        if os.path.isfile(file):
            img_width_test.append(im.width)
            img_height_test.append(im.height)

avg_test = (np.round(np.average(img_width_test), 1), np.round(np.average(img_height_test), 1))
stdev_test = ((np.round(np.std(img_width_test), 1), np.round(np.std(img_height_test), 1)))
min_test = ((np.round(np.amin(img_width_test), 1), np.round(np.amin(img_height_test), 1)))
max_test = ((np.round(np.amax(img_width_test), 1), np.round(np.amax(img_height_test), 1)))


print("train_image")
print("Avg \t", avg_train)
print("Stdev \t", stdev_train)
print("Min \t", min_train)
print("Max \t", max_train)

print("test_image")
print("Avg \t", avg_test)
print("Stdev \t", stdev_test)
print("Min \t", min_test)
print("Max \t", max_test)