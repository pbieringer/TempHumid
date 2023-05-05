##############################################################################################
#
# Script TempHumid.py
#
# The script uses the functions from ???? to read the DHT22 sensor connect to a raspberry pi
#
# The script waits for the start of a full 10 minutes intervall and then reads out the sensor every minute (constant INTERVAL).
# A meanvalue ist build from 10 values and added to a FIFO buffer for displaying as a graph. The meanvalues are also written to
# a CSV File.
#
###############################################################################################

# !/usr/bin/python3

from configparser import ConfigParser
import time
import datetime

import pigpio

import DHT22

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import csv

# For sending data to a ThingSpeak server
# import httplib2, urllib.parse
import requests


def send_data(count, t, f):
    #    print (count)
    parameter = '/update.json?api_key=' + ACCESS_KEY
    for x in range(count):
        #       print (x)
        parameter = parameter + field[x][0] + str(t[x]) + field[x][1] + str(f[x])

    try:
        r = requests.get(SERVER_URL + parameter)
#        print(r.status_code)

    except:
        print("connection failed")


if __name__ == "__main__":

    config_parser = ConfigParser()
    config_parser.read('TempHumid.cfg')
#    for key in ['general', 'ThingSpeak', 'csv', 'sensor1']:
#        print('{:<12}: {}'.format(key, config_parser.has_section(key)))

    # Intervals of about 2 seconds or less will eventually hang the DHT22.
    # INTERVAL = 6 # für Entwicklung
    # INTERVAL = 60 # Messung jede Minute
    INTERVAL = config_parser.getint('general', 'intervall')
    # How many measuring point should be displayed - size of the FIFO-Buffer
    DISPLAY_COUNT = 15
    # How many values to generate a meanvalue
    # MEAN_COUNT = 2 # für Entwicklung
    # MEAN_COUNT = 2 # 10 min Mittelwert
    MEAN_COUNT = config_parser.getint('general', 'mittelwert')
    SENSOR_COUNT = config_parser.getint('general', 'sensor_count')
    SERVER_URL = config_parser.get('ThingSpeak', 'url')
    ACCESS_KEY = config_parser.get('ThingSpeak', 'write_key')

#    print(config_parser.getboolean('general', 'csv'))
#    print(config_parser.getboolean('general', 'plot'))
#    print(config_parser.getboolean('general', 'thingspeak'))
    CSV = config_parser.getboolean('general', 'csv')  # soll ein CSV File geschrieben werden
    PLOT = config_parser.getboolean('general', 'plot')  # sollen die Daten auf einem lokale Bildschirm geplottet werden
    THINGSPEAK = config_parser.getboolean('general', 'thingspeak')

    pi = pigpio.pi()

    s = []
    pin = []

    if config_parser.has_section('sensor1'):
        pin.append(config_parser.getint('sensor1', 'pin'))
    if config_parser.has_section('sensor2'):
        pin.append(config_parser.getint('sensor2', 'pin'))

    if config_parser.has_section('sensor3'):
        pin.append(config_parser.getint('sensor3', 'pin'))
    if config_parser.has_section('sensor4'):
        pin.append(config_parser.getint('sensor4', 'pin'))

    for k in range(SENSOR_COUNT):
        s.append(DHT22.sensor(pi, pin[k], LED=16, power=8))

    # Für Plot
    r = 0
    feuchte = [[]]
    temp = [[]]
    Zeit = []

    # Für CSV Ausgabe
    row = [0, 0, 0, 0, 0, 0, 0, 0, 0]

    # Für Thingspeak
    t = [0.0, 0.0, 0.0, 0.0]
    h = [0.0, 0.0, 0.0, 0.0]

    field = [["&field1=", "&field2="], ["&field3=", "&field4="], ["&field5=", "&field6="], ["&field7=", "&field8="]]
    # print (field)

    next_reading = int(time.time())

    while next_reading % (MEAN_COUNT * INTERVAL) != 0:  # volles Intervall
        next_reading = int(time.time())
        # print( next_reading % 60)

    start = next_reading

    #   plt.ion()

    #   figure, ax = plt.subplots(figsize=(10,6))

    while True:

        m_h = [0.0, 0.0, 0.0, 0.0]
        m_t = [0.0, 0.0, 0.0, 0.0]

        ### Buffer for computing the meanvalue
        while r < MEAN_COUNT:
            r += 1
            
            for i in range(SENSOR_COUNT):
                
                s[i].trigger()

                time.sleep(0.2)
#                print(s[0].humidity(), s[0].temperature())
#                print(s[1].humidity(), s[1].temperature())
                m_h[i] += s[i].humidity()
#                print(m_h[i])
                m_t[i] += s[i].temperature()

                s[i].sensor_resets()

            next_reading += INTERVAL
            time.sleep(next_reading - time.time())  # Overall INTERVAL second polling.
            tt = time.strftime("%d.%m.%Y %H:%M:00", time.localtime())

        #### FIFO Buffer for the Display
        #      if len(Zeit) == DISPLAY_COUNT:
        #        feuchte.pop(0)
        #        temp.pop(0)
        #        Zeit.pop(0)
        #
        #        feuchte.append(m_h/r)
        #        temp.append(m_t/r)
        #        Zeit.append(tt)

        #      else:
        #        feuchte.append(m_h/r)
        #        temp.append(m_t/r)
        #        Zeit.append(tt)
        #      print ( feuchte, temp )

#        print(" {} {} {:3.2f} {:3.2f} ".format(
#           r, tt, m_h[0] / r, m_t[0] / r
#        ))

        row[0] = tt

        for j in range(SENSOR_COUNT):
            row[j + j + 1] = m_h[j] / r
            row[j + j + 2] = m_t[j] / r
            t[j] = m_t[j] / r
#            print(t[j])
            h[j] = m_h[j] / r
#            print(h[j])

        print('Thingspeak : ')
        print(t, h)
        send_data(SENSOR_COUNT, t, h)

    # opening csv file
    # fn = time.strftime("%d_%m_%Y", time.localtime())+".csv"
        fn = config_parser.get('csv', 'filename')

        if CSV:
            file = open(fn, 'a')
            with file:
                writer = csv.writer(file, delimiter=';')
                writer.writerow(row)
            file.close()
            r = 0

        if PLOT:
        ###### Plot

            plt.ion()

#            figure, ax = plt.subplots(figsize=(10, 6))

#            line1, = ax.plot(Zeit, temp, 'r-')
#            line2, = ax.plot(Zeit, feuchte, 'b-')

#            plt.title("Temperatur und Feuchte dynamisch " + time.strftime("%d.%m.%Y ", time.localtime()), fontsize=20)

#            plt.xlabel("Zeit [sec]", fontsize=18)
#            plt.ylabel("Temperatur und Feuchte", fontsize=18)
#            for label in ax.get_xticklabels():
#                label.set_rotation(40)
#                label.set_horizontalalignment('right')

#            line1.set_xdata(Zeit)
#            line2.set_xdata(Zeit)
#            line1.set_ydata(temp)
#            line2.set_ydata(feuchte)

#            figure.canvas.draw()

#            figure.canvas.flush_events()
#            time.sleep(0.1)

#   s.cancel()
    pi.stop()
