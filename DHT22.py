#!/usr/bin/env python

# 2014-07-11 DHT22.py

import time
import atexit

import pigpio

class sensor:
   """
   A class to read relative humidity and temperature from the
   DHT22 sensor.  The sensor is also known as the AM2302.

   The sensor can be powered from the Pi 3V3 or the Pi 5V rail.

   Powering from the 3V3 rail is simpler and safer.  You may need
   to power from 5V if the sensor is connected via a long cable.

   For 3V3 operation connect pin 1 to 3V3 and pin 4 to ground.

   Connect pin 2 to a gpio.

   For 5V operation connect pin 1 to 5V and pin 4 to ground.

   The following pin 2 connection works for me.  Use at YOUR OWN RISK.

   5V--5K_resistor--+--10K_resistor--Ground
                    |
   DHT22 pin 2 -----+
                    |
   gpio ------------+
   """

   def __init__(self, pi, gpio, LED=None, power=None):
      """
      Instantiate with the Pi and gpio to which the DHT22 output
      pin is connected.

      Optionally a LED may be specified.  This will be blinked for
      each successful reading.

      Optionally a gpio used to power the sensor may be specified.
      This gpio will be set high to power the sensor.  If the sensor
      locks it will be power cycled to restart the readings.

      Taking readings more often than about once every two seconds will
      eventually cause the DHT22 to hang.  A 3 second interval seems OK.
      """

      self.pi = pi
      self.gpio = gpio
      self.LED = LED
      self.power = power

      if power is not None:
         pi.write(power, 1)  # Switch sensor on.
         time.sleep(2)

      self.powered = True

      self.cb = None

      atexit.register(self.cancel)

      self.bad_CS = 0  # Bad checksum count.
      self.bad_SM = 0  # Short message count.
      self.bad_MM = 0  # Missing message count.
      self.bad_SR = 0  # Sensor reset count.

      # Power cycle if timeout > MAX_TIMEOUTS.
      self.no_response = 0
      self.MAX_NO_RESPONSE = 2

      self.rhum = -999
      self.temp = -999

      self.tov = None

      self.high_tick = 0
      self.bit = 40

      pi.set_pull_up_down(gpio, pigpio.PUD_OFF)

      pi.set_watchdog(gpio, 0)  # Kill any watchdogs.

      self.cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cb)

   def _cb(self, gpio, level, tick):
      """
      Accumulate the 40 data bits.  Format into 5 bytes, humidity high,
      humidity low, temperature high, temperature low, checksum.
      """
      diff = pigpio.tickDiff(self.high_tick, tick)

      if level == 0:

         # Edge length determines if bit is 1 or 0.

         if diff >= 50:
            val = 1
            if diff >= 200:   # Bad bit?
               self.CS = 256  # Force bad checksum.
         else:
            val = 0

         if self.bit >= 40:  # Message complete.
            self.bit = 40

         elif self.bit >= 32:  # In checksum byte.
            self.CS  = (self.CS << 1)  + val

            if self.bit == 39:

               # 40th bit received.

               self.pi.set_watchdog(self.gpio, 0)

               self.no_response = 0

               total = self.hH + self.hL + self.tH + self.tL

               if (total & 255) == self.CS:  # Is checksum ok?

                  self.rhum = ((self.hH << 8) + self.hL) * 0.1

                  if self.tH & 128:  # Negative temperature.
                     mult = -0.1
                     self.tH = self.tH & 127
                  else:
                     mult = 0.1

                  self.temp = ((self.tH << 8) + self.tL) * mult

                  self.tov = time.time()

                  if self.LED is not None:
                     self.pi.write(self.LED, 0)

               else:

                  self.bad_CS += 1

         elif self.bit >= 24:  # in temp low byte
            self.tL = (self.tL << 1) + val

         elif self.bit >= 16:  # in temp high byte
            self.tH = (self.tH << 1) + val

         elif self.bit >= 8:  # in humidity low byte
            self.hL = (self.hL << 1) + val

         elif self.bit >= 0:  # in humidity high byte
            self.hH = (self.hH << 1) + val

         else:               # header bits
            pass

         self.bit += 1

      elif level == 1:
         self.high_tick = tick
         if diff > 250000:
            self.bit = -2
            self.hH = 0
            self.hL = 0
            self.tH = 0
            self.tL = 0
            self.CS = 0

      else:  # level == pigpio.TIMEOUT:
         self.pi.set_watchdog(self.gpio, 0)
         if self.bit < 8:       # Too few data bits received.
            self.bad_MM += 1    # Bump missing message count.
            self.no_response += 1
            if self.no_response > self.MAX_NO_RESPONSE:
               self.no_response = 0
               self.bad_SR += 1  # Bump sensor reset count.
               if self.power is not None:
                  self.powered = False
                  self.pi.write(self.power, 0)
                  time.sleep(2)
                  self.pi.write(self.power, 1)
                  time.sleep(2)
                  self.powered = True
         elif self.bit < 39:    # Short message receieved.
            self.bad_SM += 1    # Bump short message count.
            self.no_response = 0

         else:                  # Full message received.
            self.no_response = 0

   def temperature(self):
      """Return current temperature."""
      return self.temp

   def humidity(self):
      """Return current relative humidity."""
      return self.rhum

   def staleness(self):
      """Return time since measurement made."""
      if self.tov is not None:
         return time.time() - self.tov
      else:
         return -999

   def bad_checksum(self):
      """Return count of messages received with bad checksums."""
      return self.bad_CS

   def short_message(self):
      """Return count of short messages."""
      return self.bad_SM

   def missing_message(self):
      """Return count of missing messages."""
      return self.bad_MM

   def sensor_resets(self):
      """Return count of power cycles because of sensor hangs."""
      return self.bad_SR

   def trigger(self):
      """Trigger a new relative humidity and temperature reading."""
      if self.powered:
         if self.LED is not None:
            self.pi.write(self.LED, 1)

         self.pi.write(self.gpio, pigpio.LOW)
         time.sleep(0.017)  # 17 ms
         self.pi.set_mode(self.gpio, pigpio.INPUT)
         self.pi.set_watchdog(self.gpio, 200)

   def cancel(self):
      """Cancel the DHT22 sensor."""

      self.pi.set_watchdog(self.gpio, 0)

      if self.cb is not None:
         self.cb.cancel()
         self.cb = None

if __name__ == "__main__":

   import time

   import pigpio

   import DHT22
   
   import matplotlib.pyplot as plt
   import csv

   # Intervals of about 2 seconds or less will eventually hang the DHT22.
   INTERVAL = 60 # Messung jede Minute
   # How many measuring point should be displayed - size of the FIFO-Buffer
   DISPLAY_COUNT = 15
   # How many values to generate a meanvalue
   MEAN_COUNT = 10 # 10 min Mittelwert

   pi = pigpio.pi()

   s = DHT22.sensor(pi, 2, LED=16, power=8)

   r = 0
   feuchte=[]
   Temp=[]
   Zeit=[]
   row=[]
   row.append(0)
   row.append(0)
   row.append(0)

   next_reading = int( time.time())
   
   
   while next_reading % 600 != 0:  # volle 10 Minuten
       next_reading = int(time.time())
       #print( next_reading % 60)
   
   start = next_reading
   
   #opening csv file
   fn = time.strftime("%d_%m_%Y", time.localtime())+".csv"
   
   
   plt.ion()

   figure, ax = plt.subplots(figsize=(8,6))

   while True:

      m_h = 0
      m_t = 0
      
      ### Buffer for computing the meanvalue
      while r < MEAN_COUNT:
        r += 1
        s.trigger()

        time.sleep(0.2)
      
        
        m_h += s.humidity()
        m_t += s.temperature()

        
        s.sensor_resets()
        next_reading += INTERVAL

        time.sleep(next_reading-time.time())  # Overall INTERVAL second polling.
          
      tt = time.strftime("%d.%m.%Y %H:%M:00", time.localtime())
      
      #### FIFO Buffer for the Display
      if len(Zeit) == DISPLAY_COUNT:
        feuchte.pop(0)
        Temp.pop(0)
        Zeit.pop(0)
        
        feuchte.append(m_h/r)
        Temp.append(m_t/r)
        Zeit.append(tt)
        
      else:
        feuchte.append(m_h/r)
        Temp.append(m_t/r)
        Zeit.append(tt)
      #print ( feuchte, Temp )
      print(" {} {} {:3.2f} {:3.2f} ".format(
         r,tt,m_h/r , m_t/r
         ))
      row[0] = tt
      row[1] = m_h/r
      row[2] = m_t/r
      
      file = open (fn, 'a' )
      with file:
       writer = csv.writer(file, delimiter=';')
       writer.writerow(row)
      file.close()
      r = 0
      
      
      ###### Plot
      
      line1, = ax.plot(Zeit, Temp, 'r-')
      line2, = ax.plot(Zeit, feuchte, 'b-')

      plt.title("Temperatur und Feuchte dynamisch "+ time.strftime("%d.%m.%Y ", time.localtime()),fontsize=20)

      plt.xlabel("Zeit [sec]",fontsize=18)
      plt.ylabel("Temperatur und Feuchte",fontsize=18)
    
      line1.set_xdata(Zeit)
      line2.set_xdata(Zeit)
      line1.set_ydata(Temp)
      line2.set_ydata(feuchte)
    
      figure.canvas.draw()
    
      figure.canvas.flush_events()
      time.sleep(0.1)



   s.cancel()

   pi.stop()

