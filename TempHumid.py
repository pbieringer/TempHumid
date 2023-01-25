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

