# Program to calculate temperature, then use AWS MQTT client to publish
# to topic held on AWS IoT Core.
# Author: Thomas Fensome

# Import python modules.
import sys
import time as t
import json
from datetime import datetime
from sense_hat import SenseHat

# Import AWS connection modules.
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder

# Declare AWS connection variables and assign secure key values
# to enable connection to AWS IoT Core.
ENDPOINT = "a2csf1frpsnqc7-ats.iot.eu-west-1.amazonaws.com"
CLIENT_ID = "cm4702Pi"
PATH_TO_CERT = "/home/pi/certs/device.pem.crt"
PATH_TO_KEY = "/home/pi/certs/private.pem.key"
PATH_TO_ROOT = "/home/pi/certs/Amazon-root-CA-1.pem"
TOPIC = "device/WHHTS1/data"


# Generate the connection to AWS IoT Core using MQTT.
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6
            )

# Print connection information to terminal.
print("Connecting to {} with client ID '{}'...".format(
        ENDPOINT, CLIENT_ID))
# Make the connection.
connect_future = mqtt_connection.connect()
connect_future.result()
# If connection successful, print success message to terminal.
print("Connected!")

# CPU class to obtain cpu temp.
class CPUTemp:
    def __init__(self, tempfilename = "/sys/class/thermal/thermal_zone0/temp"):
        self.tempfilename = tempfilename

    def __enter__(self):
        self.open()
        return self

    def open(self):
        self.tempfile = open(self.tempfilename, "r")
    
    def read(self):
        self.tempfile.seek(0)
        return self.tempfile.read().rstrip()

    def get_temperature(self):
        return self.get_temperature_in_c()

    def get_temperature_in_c(self):
        tempraw = self.read()
        return float(tempraw[:-3] + "." + tempraw[-3:])

    def get_temperature_in_f(self):
        return self.convert_c_to_f(self.get_temperature_in_c())
    
    def convert_c_to_f(self, c):
        return c * 9.0 / 5.0 + 32.0

    def __exit__(self, type, value, traceback):
        self.close()
            
    def close(self):
        self.tempfile.close()

# Declare an instance of SenseHat.
sense = SenseHat()
# Print message to terminal to confirm publishing.  
print('Begin Publish')
# try ensures that program continues to publish messages until stopped.    
try:
  while True:
    with CPUTemp() as cpu_temp:
      global c
# Get CPU temperature and print to terminal.
      c = cpu_temp.get_temperature()
      print("cpu temp %d"%c)
# Var used to calculate Room temperature.  
    factor = 3
# Calculate Room temperature.
    p = sense.get_temperature_from_pressure()
    h = sense.get_temperature_from_humidity()
    temp_calc = ((p+h)/2) - (c/factor)
    actualTemp = int(temp_calc)
# Obtain the current time.
    date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
# Structure the message to be sent.    
    message = {"temperature" : actualTemp,
                "date": date
              } 
# Publish message to AWS IoT core using MQTT.
    mqtt_connection.publish(topic=TOPIC, payload=json.dumps(message), qos=mqtt.QoS.AT_LEAST_ONCE)
# Print published message to the terminal.    
    print("Published: '" + json.dumps(message) + "' to the topic: " + "device/WHHTS1/data")
# Sleep added to ensure that program only publishes message once a minute.    
    t.sleep(60)

# Check for Keyboard entry to stop program running.
except KeyboardInterrupt:
# Print to terminal to confirm that publishing has stopped.    
  print('Publish End')
# Terminate the connection to AWS IoT  
  disconnect_future = mqtt_connection.disconnect()
  disconnect_future.result()