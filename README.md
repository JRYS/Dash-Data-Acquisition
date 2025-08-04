# Capture Data with Your Favorite Browser
<img width="1821" height="913" alt="image" src="https://github.com/user-attachments/assets/d4768278-4a16-4036-8aca-a800cf2bb8ce" />

Last month, I described a simple stateless web application using Python and Plotly's Dash module. It created a dashboard allowing users to select waveform channels, update rate, and the number of samples that comprise the x-axis. It used this information to display simulated analog data, which was used to explain how data is stored in an HTML element, and how new data is added to the display. This month, I used the same application framework. However, instead of generating the data, I used an MCC USB 200 series device to capture live data in real time, while maintaining the stateless nature of a browser application. This application has two parts: a lightweight socket server responsible for controlling the hardware device, and a web application that sends commands to the server and displays the data.

Download the **client_server_web_application.zip** file and extract its contents to a folder on your hard drive. Browse this folder using Explorer and open a terminal by entering 'CMD' in the address bar. Do this twice. Activate your virtual environment in both terminals. 

Please ensure you have the following components before running the server and web application Python code.
1. Install MCC's InstaCal utility: Use the following installation program: https://files.digilent.com/downloads/InstaCal/icalsetup.exe.
2. Install MCC's Windows Python support: Following the instructions on: https://github.com/mccdaq/mcculw
3. Install Plotly's Dash and Dash_Daq:**pip install dash**, and **dash_daq**
   
Start two command prompts from the folder containing all the files. If required, activate your virtual environment.  **python server.py** on the command line. Enter python <em>web-app.py</em> in the other terminal. When it runs, it displays an IP address to enter into your favorite browser's address bar to start the application.

Disclaimer: The code discussed here is provided as-is. It has not been thoroughly tested or validated as a product for use in a deployed application, system, or hazardous environment. You assume all risks when using</span><span> the example code</span><span>.</span>
