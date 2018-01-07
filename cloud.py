import requests
import socket
import threading
import logging
import time,RPi.GPIO as GPIO
import RPi.GPIO as GPIO
import Adafruit_DHT as dht
import sys
import httplib, urllib
import json
deviceId = "DQ8wOuBk"
deviceKey = "5T46Y4o1mmXvK6Vo"
GPIO.setmode(GPIO.BCM)

# change
DEVICE_INFO = {
        'device_id' : 'DQ8wOuBk',
        'device_key' : '5T46Y4o1mmXvK6Vo'
}
# change 'INFO' to 'WARNING' to filter info messages
logging.basicConfig(level='INFO')

heartBeatTask = None

def post_to_mcs(payload):
        headers = {"Content-type": "application/json", "deviceKey": deviceKey}
        not_connected = 1
        while (not_connected):
                try:
                        conn = httplib.HTTPConnection("api.mediatek.com:80")
                        conn.connect()
                        not_connected = 0
                except (httplib.HTTPException, socket.error) as ex:
                        print "Error: %s" % extime.sleep(5)
        conn.request("POST", "/mcs/v2/devices/" + deviceId + "/datapoints", json.dumps(payload), headers)
        response = conn.getresponse()
        print( response.status, response.reason, json.dumps(payload), time.strftime("%c"))
        data = response.read()
        conn.close()

def establishCommandChannel():
    # Query command server's IP & port
    connectionAPI = 'https://api.mediatek.com/mcs/v2/devices/%(device_id)s/connections.csv'
    r = requests.get(connectionAPI % DEVICE_INFO,
                 headers = {'deviceKey' : DEVICE_INFO['device_key'],
                            'Content-Type' : 'text/csv'})
    logging.info("Command Channel IP,port=" + r.text)
    (ip, port) = r.text.split(',')

    # Connect to command server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, int(port)))
    s.settimeout(None)
    # Heartbeat for command server to keep the channel alive
    def sendHeartBeat(commandChannel):
        keepAliveMessage = '%(device_id)s,%(device_key)s,0' % DEVICE_INFO
        commandChannel.sendall(keepAliveMessage)
        logging.info("beat:%s" % keepAliveMessage)

    def heartBeat(commandChannel):
        sendHeartBeat(commandChannel)
        # Re-start the timer periodically
        global heartBeatTask
        heartBeatTask = threading.Timer(10, heartBeat, [commandChannel]).start()

    heartBeat(s)
    return s

def waitAndExecuteCommand(commandChannel):
    while True:
        command = commandChannel.recv(1024)
        logging.info("recv:" + command)
        # command can be a response of heart beat or an update of the LED_control,
        # so we split by ',' and drop device id and device key and check length
        fields = command.split(',')[2:]

        h0, t0 = dht.read_retry(dht.DHT11,4)
        if h0 is not None and t0 is not None:
                print('Temp={0:0.1f}* Humidity={1:0.1f}%'.format(t0,h0))
                payload = {"datapoints":[{"dataChnId":"Humidity","values":{"value":h0}},{"dataChnId":"Temperature","values":{"value":t0}}]}
                post_to_mcs(payload)
                time.sleep(1)
        else:
                print('Failed to get reading.Try again!')

        if len(fields) > 1:
            timeStamp, dataChannelId, commandString = fields
            if dataChannelId == 'LED_control':
                # check the value - it's either 0 or 1
                commandValue = int(commandString)
                logging.info("led :%d" % commandValue)
                setLED(commandValue)

def setupLED():
    global pin
    # on LinkIt Smart 7699, pin 44 is the Wi-Fi LED.
    GPIO.setup(22, GPIO.OUT)

def setLED(state):
    # Note the LED is "reversed" to the pin's GPIO status.
    # So we reverse it here.
    if state:
        GPIO.output(22,1)
    else:
        GPIO.output(22,0)

if __name__ == '__main__':
    setupLED()
    channel = establishCommandChannel()
    waitAndExecuteCommand(channel)
