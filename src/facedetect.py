#!/usr/bin/python

# face_detect.py

# Face Detection using OpenCV. Based on sample code from:
# http://python.pastebin.com/m76db1d6b

# Usage: python face_detect.py <image_file>

import sys, os
#from opencv.cv import *
import opencv.cv as cv
from opencv.highgui import *

PATH = os.path.join('..','frontalface.xml') #/usr/share/opencv/haarcascades/haarcascade_frontalface_default.xml'

def detectObjects(image):
    """Converts an image to grayscale and prints the locations of any
    faces found"""
    size = cv.cvSize(image.width, image.height)
    grayscale =  cv.cvCreateImage(size, 8, 1)
    cv.cvCvtColor(image, grayscale,  cv.CV_BGR2GRAY)
    


    storage =  cv.cvCreateMemStorage(0)         
    cv.cvClearMemStorage(storage)              
    cv.cvEqualizeHist(grayscale, grayscale)    
    cascade = cv.cvLoadHaarClassifierCascade(PATH, cv.cvSize(1,1))     
    faces = cv.cvHaarDetectObjects(grayscale, cascade, storage, 1.2, 2, cv.CV_HAAR_DO_CANNY_PRUNING, cv.cvSize(30,30))

    if faces:
        for f in faces:
            print("[(%d,%d) -> (%d,%d)]" % (f.x, f.y, f.x+f.width, f.y+f.height))

def main():
    image = cvLoadImage(sys.argv[1]);
    detectObjects(image)

if __name__ == "__main__":
    main()