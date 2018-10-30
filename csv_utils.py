
import csv

with open('data/ADE-negative.txt') as f:
	for line in f:
		myFile = open('data/ADE.csv', 'a')
		with myFile:
			writer = csv.writer(myFile, delimiter=',')
			writer.writerow(['0',  line])
