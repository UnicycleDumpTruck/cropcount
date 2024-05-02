from collections import defaultdict
import asyncio
import cv2
import os
import sys, getopt
import signal
import time
import datetime
from edge_impulse_linux.image import ImageImpulseRunner
import justpy as jp

wp = jp.WebPage(delete_flag=False)
clock_div = jp.Span(text='Loading...', classes='text-5xl m-1 p-1 bg-gray-300 font-mono', a=wp)

async def clock_counter():
    while True:
        clock_div.text = time.strftime("%a, %d %b %Y, %H:%M:%S", time.localtime())
        jp.run_task(wp.update())
        await asyncio.sleep(1)

async def clock_init():
    jp.run_task(clock_counter())

async def clock_test():
    return wp

jp.justpy(clock_test, startup=clock_init)

modelfile = '/home/exhibits/cropcounter/modelfile.eim'
# If you have multiple webcams, replace None with the camera port you desire, get_webcams() can help find this
# camera_port = None
camera_port = 0

runner = None
# if you don't want to see a camera preview, set this to False
show_camera = True
if (sys.platform == 'linux' and not os.environ.get('DISPLAY')):
    show_camera = False

def now():
    return round(time.time() * 1000)

def get_webcams():
    port_ids = []
    for port in range(5):
        print("Looking for a camera in port %s:" %port)
        camera = cv2.VideoCapture(port)
        if camera.isOpened():
            ret = camera.read()[0]
            if ret:
                backendName =camera.getBackendName()
                w = camera.get(3)
                h = camera.get(4)
                print("Camera %s (%s x %s) found in port %s " %(backendName,h,w, port))
                port_ids.append(port)
            camera.release()
    return port_ids

def sigint_handler(sig, frame):
    print('Interrupted')
    if (runner):
        runner.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)


print('MODEL: ' + modelfile)



with ImageImpulseRunner(modelfile) as runner:
    try:
        model_info = runner.init()
        print('Loaded runner for "' + model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')
        labels = model_info['model_parameters']['labels']
        if camera_port:
            videoCaptureDeviceId = int(args[1])
        else:
            port_ids = get_webcams()
            if len(port_ids) == 0:
                raise Exception('Cannot find any webcams')
            if len(port_ids)> 1:
                raise Exception("Multiple cameras found. Add the camera port ID as a second argument to use to this script")
            videoCaptureDeviceId = int(port_ids[0])

        camera = cv2.VideoCapture(videoCaptureDeviceId)
        ret = camera.read()[0]
        if ret:
            backendName = camera.getBackendName()
            w = camera.get(3)
            h = camera.get(4)
            print("Camera %s (%s x %s) in port %s selected." %(backendName,h,w, videoCaptureDeviceId))
            camera.release()
        else:
            raise Exception("Couldn't initialize selected camera.")

        next_frame = 0 # limit to ~10 fps here
        
        # Define the top of the image and the number of columns
        TOP_Y = 20 # was 80 # was originially 100
        NUM_COLS = 20
        COL_WIDTH = int(w / NUM_COLS)
        # Define the factor of the width/height which determines the threshold
        # for detection of the object's movement between frames:
        DETECT_FACTOR = 5 # was 1.5

        # Initialize variables
        count = [0] * NUM_COLS
        countsum = 0
        previous_blobs = [[] for _ in range(NUM_COLS)]
        label_counts = defaultdict(int)
        

        for res, img in runner.classifier(videoCaptureDeviceId):
            # Initialize list of current blobs
            current_blobs = [[] for _ in range(NUM_COLS)]
            
            if (next_frame > now()):
                time.sleep((next_frame - now()) / 1000)

            if "bounding_boxes" in res["result"].keys():
                len_bb = len(res["result"]["bounding_boxes"])
                if len_bb:
                    print(f'Found {len_bb} bounding boxes at {datetime.datetime.now()}')
                    # print('Found %d bounding boxes (%d ms.)' % (len_bb, res['timing']['dsp'] + res['timing']['classification']))
                for bb in res["result"]["bounding_boxes"]:
                    print('\t%s (%.2f): x=%d y=%d w=%d h=%d' % (bb['label'], bb['value'], bb['x'], bb['y'], bb['width'], bb['height']))
                    img = cv2.rectangle(img, (bb['x'], bb['y']), (bb['x'] + bb['width'], bb['y'] + bb['height']), (255, 0, 0), 1)

                        # Check which column the blob is in
                    col = int(bb['x'] / COL_WIDTH)
                    # Check if blob is within DETECT_FACTOR*h of a blob detected in the previous frame and treat as the same object
                    for blob in previous_blobs[col]:
                        within_x_of_prev = abs(bb['x'] - blob[0]) < DETECT_FACTOR * (bb['width'] + blob[2])
                        within_y_of_prev = abs(bb['y'] - blob[1]) < DETECT_FACTOR * (bb['height'] + blob[3])
                        passed_y_threshold = blob[1] >= TOP_Y and bb['y'] < TOP_Y
                        print(f"Within x: {within_x_of_prev} /t Within y: {within_y_of_prev} /t Crossed YT: {passed_y_threshold}")
                        if within_x_of_prev and within_y_of_prev and passed_y_threshold:
                                # Increment count for this column
                                if blob[5] > 0.7: # if confident in classification
                                    count[col] += 1
                                    countsum += 1
                                    label_counts[bb['label']] += 1
                                    print(f"{blob[4]} added to count =============================")
                                    print(label_counts)
                                else:
                                    print(f"Insufficient confidence to add {blob[4]}")
                    # Add current blob to list
                    print(bb)
                    current_blobs[col].append((bb['x'], bb['y'], bb['width'], bb['height'], bb['label'], bb['value']))
                
            # Update previous blobs
            previous_blobs = current_blobs

            if (show_camera):
                im2 = cv2.resize(img, dsize=(800,800))
                cv2.putText(im2, f'{label_counts["Sweet Potatos"]} Sweet Potatoes', (15,700), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 2)
                cv2.putText(im2, f'{label_counts["Soybean"]} Soybeans', (15,740), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 2)
                cv2.putText(im2, f'{countsum} Total Identified Items', (15,780), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 2)
                cv2.imshow('edgeimpulse', cv2.cvtColor(im2, cv2.COLOR_RGB2BGR))
                # len_bb = len(res["result"]["bounding_boxes"])
                # if len_bb > 0:
                    # print(f"Found {len_bb} boxes at {time.time()}")
                    # print('Found %d bounding boxes (%d ms.)' % (len(res["result"]["bounding_boxes"]), res['timing']['dsp'] + res['timing']['classification']))

                if cv2.waitKey(1) == ord('r'):
                    countsum = 0
                    label_counts['Soybean'] = 0
                if cv2.waitKey(1) == ord('q'):
                    break

            next_frame = now() + 100
    finally:
        if (runner):
            runner.stop()


