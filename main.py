#!/usr/bin/venstar-tracking/venv/bin/python3

import requests
from dotenv import load_dotenv, set_key, find_dotenv
import os
import pandas as pd
import smtplib, ssl
from datetime import datetime
from sqlalchemy import create_engine
from adafruit_bme280 import basic as adafruit_bme280
from board import D4
import board

# Set globals
DOTENV_FILE = find_dotenv()
load_dotenv(DOTENV_FILE)
IP = os.environ.get("VENSTAR_IP")
SENSOR_URL = 'http://' + IP + '/query/sensors'
RUNTIMES_URL = 'http://' + IP + '/query/runtimes'
DB_STRING = os.environ.get('DB_STRING')

i2c = board.I2C()
BME280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)

def get_pi_details():
    """Access the onboard sensor and return temp and humidity"""
    farenheight = BME280.temperature * (9 / 5) + 32
    hum = BME280.humidity
    return farenheight, hum

def send_battery_notification(level):
    """If battery is below 50%, send an email to myself to replace"""

    # Check when the last noticiation email was sent
    last_notification = datetime.strptime(os.environ.get('VENSTAR_LOW_BATT_EMAIL'), '%Y-%m-%d').date()
    if last_notification != datetime.today().date():  # Only send if it hasn't been sent today
        port = 465  # For SSL
        smtp_server = "smtp.sendgrid.net"
        sender_email = "apikey"
        receiver_email = "sailcali@gmail.com"
        message = f"""From: kiowalabs@gmail.com\nSubject:
            Remote sensor battery is at {level}%.
            This message is sent from Python."""
        password = os.environ.get("EMAIL_PASSWORD")

        # Create a secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            # Used WITH to ensure it is closed on completion
            server.login(sender_email, password)
            # Send email data
            server.sendmail(sender_email, receiver_email, message)
            
            # Change the date in the environment variable to todays date
            os.environ["VENSTAR_LOW_BATT_EMAIL"] = f"{datetime.today().date()}"
            set_key(DOTENV_FILE, "VENSTAR_LOW_BATT_EMAIL", os.environ["VENSTAR_LOW_BATT_EMAIL"])

def create_dataframe():
    """Esablish data to add to database"""
    data = {'time': [datetime.today(),]}
    if pi_temp != None:
        data['pi_temp'] = pi_temp
    if humidity != None:
        data['humidity'] = humidity
    for sensor in sensor_data['sensors']:
        if sensor['name'] == 'Remote':
            data['remote_temp'] = [sensor['temp'],]
        elif sensor['name'] == 'Thermostat':
            data['local_temp'] = [sensor['temp'],]
    data['cool_runtime'] = runtimes_data['runtimes'][-1]['cool1']
    data['heat_runtime'] = runtimes_data['runtimes'][-1]['heat1']
    df = pd.DataFrame(data)
    df.set_index(['time'], inplace=True)
    return df


if __name__ == '__main__':
    # Get sensor data from thermostat API
    sensors = requests.get(SENSOR_URL)
    sensor_data = sensors.json()
    
    # Get runtimes data from thermostat API
    runtimes = requests.get(RUNTIMES_URL)
    runtimes_data = runtimes.json()

    # Check the battery level and send email if its low
    if sensor_data['sensors'][2]['battery'] < 40:
        send_battery_notification(sensor_data['sensors'][2]['battery'])

    # Get the temp and humidity from the pi
    pi_temp, humidity = get_pi_details()

    # Open database engine
    db = create_engine(DB_STRING)

    # Create dataframe from sensor data
    df = create_dataframe()

    # Send new data to database
    df.to_sql('temp_history', db, if_exists='append')
