import requests
from dotenv import load_dotenv, set_key, find_dotenv
import os
import pandas as pd
import smtplib, ssl
from datetime import datetime, timedelta
from sqlalchemy import create_engine

DOTENV_FILE = find_dotenv()
load_dotenv(DOTENV_FILE)
IP = os.environ.get("VENSTAR_IP")
SENSOR_URL = 'http://' + IP + '/query/sensors'
DB_STRING = os.environ.get('DB_STRING')

def send_battery_notification(level):
    last_notification = datetime.strptime(os.environ.get('VENSTAR_LOW_BATT_EMAIL'), '%Y-%m-%d').date()
    if last_notification != datetime.today().date():
        port = 465  # For SSL
        password = os.environ.get("GMAIL_PASSWORD")

        # Create a secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
            
            server.login("kiowalabs@gmail.com", password)
            sender_email = "kiowalabs@gmail.com"
            receiver_email = "sailcali@gmail.com"

            message = f"""Subject: Sensor Low
                Remote sensor battery is at {level}%.
                This message is sent from Python."""

            server.sendmail(sender_email, receiver_email, message)
            
            os.environ["VENSTAR_LOW_BATT_EMAIL"] = f"{datetime.today().date()}"
            set_key(DOTENV_FILE, "VENSTAR_LOW_BATT_EMAIL", os.environ["VENSTAR_LOW_BATT_EMAIL"])

sensors = requests.get(SENSOR_URL)

sensor_data = sensors.json()
if sensor_data['sensors'][2]['battery'] < 60:
    send_battery_notification(sensor_data['sensors'][2]['battery'])
print(sensor_data)
db = create_engine(DB_STRING)
data = {'time': [datetime.today(),], 'local_temp': [sensor_data['sensors'][0]['temp'],], 'remote_temp': [sensor_data['sensors'][2]['temp'],]}
df = pd.DataFrame(data)
df.set_index(['time'], inplace=True)
df.to_sql('temp_history', db, if_exists='append')
