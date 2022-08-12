from os import listdir, path
import re
import csv

def char_to_num(argument):
    switcher = {
        "A": 0,
        "BA": 1,
        "CA": 2,
        "DA": 3,
        "GA": 4,
        "HA": 5,
        "I": 6,
        "JA": 7,
        "KA": 8,
        "LA": 9,
        "MA": 10,
        "NA": 11,
        "NGA": 12,
        "NYA": 13,
        "PA": 14,
        "RA": 15,
        "SA": 16,
        "TA": 17,
        "U": 18,
        "WA": 19,
        "YA": 20,
        "PANELENG": 21,
        "PANGLAYAR": 22,
        "PANOLONG": 23,
        "PANEULEUNG": 24,
        "PANGHULU": 25,
        "PANYUKU": 26,
        "PATEN": 27
    }
    return switcher.get(argument)

classes_txt = 'list_class_name.txt'
train_image_ext = listdir('train_image')

with open(classes_txt) as file:
    classes_word = [line.rstrip() for line in file]

train_image_ext.sort()
classes_word.sort()

train_annotation_char = [re.sub('_.*', '', annotation_char) for annotation_char in train_image_ext]
train_annotation = [char_to_num(x) for x in train_annotation_char]

print(train_image_ext)
print(train_annotation)

train_annotated_zip = zip(train_image_ext, train_annotation)
train_annotated = [list(a) for a in train_annotated_zip]

print(tuple(train_annotated))

with open('train_labels.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(tuple(train_annotated))