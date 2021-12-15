# coding=utf-8

# import the necessary packages
from imutils.video import VideoStream
from libs.shapedetector import ShapeDetector
from scipy.spatial import distance as dist
from skimage import measure
from imutils import perspective
from imutils import contours
import numpy as np
import argparse
import imutils
import time
import math
import cv2
import zmq

ERROR_MAX = 9

#  Socket to talk to server
#print("Connecting to TCP server…")
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")
print("CONNECTED")

pizzaSizeNum = 0
lastPizzaSizeNum = 0
# initialize the 'pixels per metric' calibration variable
pixelsPerMetric = 6.5
cntNoPizza = 0

def midpoint(ptA, ptB):
    return ((ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5)

def comparePerimeter(dA, dB, c):
    dMed = (dA + dB)/2
    realPerimeter = cv2.arcLength(c, True)
    perfectPerimeter = 2 * math.pi * dMed/2
    percentError = abs(((realPerimeter / perfectPerimeter) * 100) - 100)
    return percentError
    
def compareDiameter(dA, dB):
    dCompA = abs(dA - dB)/dA
    dCompB = abs(dA - dB)/dB
    if(dCompA > dCompB): 
        return dCompA * 100
    else: 
        return dCompB * 100
        
def comparePattern(dA, dB, dS):
    dMed = (dA + dB)/2
    percentError = abs((dMed/dS)-1) * 100
    return percentError

def compareArea(pizzaArea, dS):
    defaultArea = math.pi*(pow(dS,2)/4)
    percentError = abs((pizzaArea/defaultArea)-1) * 100
    return percentError   
    

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-w", "--width", type=float, required=True,
    help="width of the left-most object in the image (in inches)")
ap.add_argument("-p", "--picamera", type=int, default=-1,
    help="whether or not the Raspberry Pi camera should be used")
args = vars(ap.parse_args())

# initialize the video stream and allow the cammera sensor to warmup
vs = VideoStream(usePiCamera=args["picamera"] > 0).start()
time.sleep(5.0)

# loop over the frames from the video stream
while True:
    # grab the frame from the threaded video stream and resize it
    # to have a maximum width of 400 pixels
    frame = vs.read()
    image = frame
    # load the image, convert it to grayscale, and blur it slightly
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (7, 7), 0)

    # perform edge detection, then perform a dilation + erosion to
    # close gaps in between object edges
    edged = cv2.Canny(gray, 50, 100)
    edged = cv2.dilate(edged, None, iterations=1)
    edged = cv2.erode(edged, None, iterations=1)

    sd = ShapeDetector()
    
    # find contours in the edge map
    cnts = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # sort the contours from left-to-right    
    if(cnts):
        (cnts, _) = contours.sort_contours(cnts)
    
    orig = image.copy()
    
    # Send to socket there is no pizza on image
    if(len(cnts) <= 2):
        if(cntNoPizza >= 700):
            cntNoPizza = 0
            pizzaSizeNum = 4
            if(lastPizzaSizeNum != pizzaSizeNum):
                socket.send_string(str(pizzaSizeNum))
                socket.recv()
                print("Send request: %s" % pizzaSizeNum)
                lastPizzaSizeNum = pizzaSizeNum
        else:
            cntNoPizza = cntNoPizza + 1
    else:
        cntNoPizza = 0

    # loop over the contours individually
    for c in cnts:

        # if the contour is not sufficiently large, ignore it
        
        if cv2.contourArea(c) < 100:
            continue
        
        # compute the shape of object
        shape = sd.detect(c)
        
        # compute the rotated bounding box of the contour
        orig = image.copy()
        box = cv2.minAreaRect(c)
        box = cv2.cv.BoxPoints(box) if imutils.is_cv2() else cv2.boxPoints(box)
        box = np.array(box, dtype="int")
        
        # order the points in the contour such that they appear
        # in top-left, top-right, bottom-right, and bottom-left
        # order, then draw the outline of the rotated bounding
        # box:     box.astype("int")
        box = perspective.order_points(box)
        cv2.drawContours(orig, [c], -1, (0, 255, 0), 2)
        
        
        # loop over the original points and draw them
        #for (x, y) in box:
            #cv2.circle(orig, (int(x), int(y)), 5, (0, 0, 255), -1)
            
        # unpack the ordered bounding box, then compute the midpoint
        # between the top-left and top-right coordinates, followed by
        # the midpoint between bottom-left and bottom-right coordinates
        (tl, tr, br, bl) = box
        (tltrX, tltrY) = midpoint(tl, tr)
        (blbrX, blbrY) = midpoint(bl, br)
        
        # compute the midpoint between the top-left and top-right points,
        # followed by the midpoint between the top-righ and bottom-right
        (tlblX, tlblY) = midpoint(tl, bl)
        (trbrX, trbrY) = midpoint(tr, br)
        
        # draw the midpoints on the image
        #cv2.circle(orig, (int(tltrX), int(tltrY)), 5, (255, 0, 0), -1)
        #cv2.circle(orig, (int(blbrX), int(blbrY)), 5, (255, 0, 0), -1)
        #cv2.circle(orig, (int(tlblX), int(tlblY)), 5, (255, 0, 0), -1)
        #cv2.circle(orig, (int(trbrX), int(trbrY)), 5, (255, 0, 0), -1)
        
        # draw lines between the midpoints
        cv2.line(orig, (int(tltrX), int(tltrY)), (int(blbrX), int(blbrY)),
            (255, 0, 255), 2)
        cv2.line(orig, (int(tlblX), int(tlblY)), (int(trbrX), int(trbrY)),
            (255, 0, 255), 2)
            
        # compute the Euclidean distance between the midpoints
        #dA = dist.euclidean((tltrX, tltrY), (blbrX, blbrY))
        #dB = dist.euclidean((tlblX, tlblY), (trbrX, trbrY))
        
        dA = dist.euclidean(tl,tr)
        dB = dist.euclidean(tl,bl)
        
        # if the pixels per metric has not been initialized, then
        # compute it as the ratio of pixels to supplied metric
        # (in this case, inches)
        #if pixelsPerMetric is None:
        #    pixelsPerMetric = dB / args["width"]
                    
        # compute the size of the object
        dimA = dA / pixelsPerMetric
        dimB = dB / pixelsPerMetric
        
        
        #moment = cv2.moments(c)
        #cx = int(moment['m10']/moment['m00'])
        #cy = int(moment['m01']/moment['m00'])
        #refCircle = cv2.circle(orig, [cx, cy], int(dMed/2), (255, 0, 0), 2).ravel()
        #compShapes = cv2.matchShapes(c, refCircle, 1, 0.0)
        
        # get and compute the area of the object
        pixelsArea = cv2.contourArea(c)
        pizzaArea = pixelsArea / pow(pixelsPerMetric, 2)
        
        tamanho = 1
        
        if shape == "Arredondado":  #Trocar de circular para Arredondado
            # compare diameters for prevent a oval shape
            if int(compareDiameter(dA, dB)) <= ERROR_MAX:
                # find avg diameter and perimeter of equivalent circle from contour and compare    
                if int(comparePerimeter(dA, dB, c)) <= ERROR_MAX:
                    if (comparePattern(dimA, dimB, 18) <= ERROR_MAX): # Diametro Pizza Pequena 16
                        if (compareArea(pizzaArea, 18) <= ERROR_MAX):
                            tamanho = 18
                            pizza = "Pequena"
                            pizzaSizeNum = 1
                        else: 
                            pizza = "Descartar"
                            pizzaSizeNum = 0
                    elif (comparePattern(dimA, dimB, 22) <= ERROR_MAX): # Diametro Pizza Média 19.5
                        if(compareArea(pizzaArea, 22) <= ERROR_MAX):
                            tamanho = 22
                            pizza = "Media"
                            pizzaSizeNum = 2
                        else: 
                            pizza = "Descartar"
                            pizzaSizeNum = 0
                    elif (comparePattern(dimA, dimB, 30) <= ERROR_MAX): # Diametro Pizza Grande 26
                        if (compareArea(pizzaArea, 30) <= ERROR_MAX):
                            tamanho = 30
                            pizza = "Grande"
                            pizzaSizeNum = 3
                        else: 
                            pizza = "Descartar"
                            pizzaSizeNum = 0
                    else: 
                        pizza = "Descartar"
                        pizzaSizeNum = 0
                else: 
                    pizza = "Descartar"
                    pizzaSizeNum = 0
            #else:
                #pizza = "Descartar"
                #pizzaSizeNum = 0
        #else:
            #pizza = "Descartar"
            #pizzaSizeNum = 0
            

        #  Send reply back to client
        if(lastPizzaSizeNum != pizzaSizeNum):
            socket.send_string(str(pizzaSizeNum))
            socket.recv()
            print("Send request: %s" % pizzaSizeNum)
            lastPizzaSizeNum = pizzaSizeNum
        
        
        
        # draw the object sizes on the image
        cv2.putText(orig, "{:.1f}cm".format(dimA),
            (int(tltrX - 15), int(tltrY - 10)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2)
        cv2.putText(orig, "{:.1f}cm".format(dimB),
            (int(trbrX + 10), int(trbrY)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2)
        # write size off pizza
        cv2.putText(orig, pizza,
            (int(trbrX - 50), int(trbrY + 150)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 0, 255), 2)
        cv2.putText(orig, "PER: " + str(comparePerimeter(dA, dB, c)),
            (int(trbrX - 200), int(trbrY + 170)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2)
        cv2.putText(orig, "AR: " + str(compareArea(pizzaArea, tamanho)),
            (int(trbrX - 200), int(trbrY + 200)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2)
        cv2.putText(orig, "DIM: " + str(comparePattern(dimA, dimB, tamanho)),
            (int(trbrX - 200), int(trbrY + 230)), cv2.FONT_HERSHEY_SIMPLEX,
            0.65, (255, 255, 255), 2)

        
        
    # show the output image
    cv2.imshow("Image", orig)
    key = cv2.waitKey(1) & 0xFF
    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()
 
