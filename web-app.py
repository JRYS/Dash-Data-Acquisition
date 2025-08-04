#!/usr/bin/env python
#  -*- coding: utf-8 -*-
"""
This example demonstrates a simple web server client providing visualization of
data from a USB-201 device. It makes use of the Dash Python framework for web-based
interfaces and a plotly graph.  To install the
dependencies for this example, run:
   $ pip install dash

you will also need the MCC Windows Python library and the MCC InstaCal utility installed.
Instructions for the Windows Python Library can be found on https://github.com/mccdaq/mcculw
To install InstaCal, use the following installer program:
https://files.digilent.com/downloads/InstaCal/icalsetup.exe

Running this example:
1. Start the server by opening a terminal and entering python server.py
2. Open a second terminal and enter python dash_server.py. It will display
    an IP address.
2. Open a web browser on a device on the same network as the host device and
    in the address bar, enter the IP address with the port number

Stopping this example:
1. To stop the server, use Ctrl+C in the terminal window where the server
   was started.
"""
import logging
import socket
import json
import math
import statistics

from collections import deque
from dash import Dash, dcc, html, ctx
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.graph_objs as go

# to add authorization install the following
# pip install dash==3.1.1
# pip install dash-auth==2.0.0

# uncomment the following line to import dash authorization module
# import dash_auth

from collections import namedtuple
from mcculw.enums import ULRange

from daqSocketManager import DaqSocketManager

# uncomment the following lines to specify user name and password
# VALID_USERNAME_PASSWORD_PAIRS = {
#     'NewUser': 'welcome'
# }

app = Dash(__name__)

# uncomment the following lines to enable user login
#auth = dash_auth.BasicAuth(
#    app,
#    VALID_USERNAME_PASSWORD_PAIRS
#)

PORT = 65432
#HOST = '192.168.1.163'
HOST = '127.0.0.1'
CHANNEL_COUNT = 8  # maximum channel checkboxes
debug = False
daq_socket_manager = DaqSocketManager(HOST, PORT)

# prevents debug message from being sent to console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_channel_position(led_channel, active_channels):
    """
    This function is used in the DAQ LEDDisplay update routines
    to determine the channel index, when fetching the channels data
    from the chart data array
    data
    """
    if led_channel in active_channels:
        channels = []
        active_channels.sort()
        for channel in active_channels:
            channels.append(channel)
        pos = channels.index(led_channel)
    else:
        pos = -1
    return pos

def create_board_selector():
    """
    Gets a list of available USB devices and creates a corresponding
    dash-core-components Dropdown element for the user interface.

    Returns:
        dcc.Dropdown: A dash-core-components Dropdown object.
    """

    board_selection_options = []
    if daq_socket_manager.connect(HOST, PORT) is True:

        dev_list = daq_socket_manager.get_device_list()

        if len(dev_list) > 0:
            for device in dev_list:
                board = namedtuple('board', ['board_num',
                                             'serial_num',
                                             'type',
                                             'product_name'])

                bd = board(board_num=device['Board_Number'],
                           serial_num=device['Serial_Number'],
                           type=device['Product_ID'],
                           product_name=device['Name'])

                label = '{0}: {1}'.format(bd.board_num, bd.product_name)
                option = {'label': label, 'value': json.dumps(bd._asdict())}
                board_selection_options.append(option)

        selection = None
        if board_selection_options:
            selection = board_selection_options[0]['value']

        return dcc.Dropdown(
            id='daqSelector', options=board_selection_options,
            value=selection, clearable=False,  style={'width': 200,
                                                      'height': 40,
                                                      'border-radius': '10px',
                                                      'font-size': '16px'})
    else:

        label = '{0}: {1}'.format(-1, 'no devices')
        option = {'label': label, 'value': 0}
        board_selection_options.append(option)
        return dcc.Dropdown(
            id='daqSelector', options=board_selection_options,
            clearable=False)


def init_chart_data(number_of_channels, number_of_samples, sample_rate):
    """
    Initializes the chart with the specified number of samples.

    Args:
        number_of_channels (int): The number of channels to be displayed.
        number_of_samples (int): The number of samples to be displayed.
        sample_rate (float): The current sampling rate

    Returns:
        str: A string representation of a JSON object containing the chart data.
    """
    t = 1 / sample_rate
    samples = []
    for i in range(number_of_samples):
        samples.append(i * t)
    data = []
    for _ in range(number_of_channels):
        data.append([None] * number_of_samples)

    chart_data = {'data': data, 'samples': samples, 'sample_count': 0}

    return json.dumps(chart_data)

# Define the HTML layout for the user interface, consisting of
# dash-html-components and dash-core-components.
app.layout = dbc.Container([

    html.Div([
        html.Div(
            [
                daq.LEDDisplay(id='led_0', value=f"{0.0000:.3f}", size=32, color='#FF5E5E', backgroundColor='lightgrey',
                               label={'label': 'Channel 0', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_1', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 1', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_2', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 2', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_3', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 3', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_4', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 4', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_5', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 5', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_6', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 6', 'style': {'color': '#0d0d0d'}}, style={'margin-right': '10px'}),
                daq.LEDDisplay(id='led_7', value=f"{0.0000:.3f}", size=32, color='#FF5E5E',backgroundColor='lightgrey',
                               label={'label': 'Channel 7', 'style': {'color': '#0d0d0d'}}),
            ],
            style={'display': 'flex',
                   'flexDirection': 'row',
                   'alignItems': 'top',
                   'justifyContent': 'right',
                   'height': 100,
                   'padding-left': 400,
                   'padding-right': 120,
                   'box-sizing': 'border-box',
                   'border-radius': '20px',
                   'margin-top': '1%',
                   }

        ),

        html.Div(
            id='rightContent',
            children=[
                dcc.Graph(id='stripChart',  style={'height': 800, 'width': 1600, 'border': 100, 'border-radius': 40, 'overflow': 'hidden'} ),
                html.Div(id='errorDisplay',
                         children='',
                         style={'font-weight': 'bold', 'color': 'red'}),
            ],  style={'box-sizing': 'border-box', 'float': 'left', 'padding-left': 320,}

        ),

        html.Div(
            id='leftContent',
            children=[
                html.H1('USB-200 Series Web DAQ Browser', style={'textAlign': 'left',
                                                                 'margin-top': 0,
                                                                 'width': 600,
                                                                 'display': 'block',
                                                                 'padding': '0px',
                                                                 'margin': '0px'
                                                                 }),
                html.Br(),
                html.Label('Select device:',
                           style={'font-weight': 'bold',
                                  'font-size':'20px',
                                  'display': 'block'}),
                create_board_selector(),

                html.Label('Range',
                           style={'font-weight': 'bold',
                                  'font-size': '20px',
                                  'display': 'block'}),
                dcc.Dropdown(id='rangeSelector', #fixed at ± 10V for USB-200 series
                             options=[{'label': '± 10V', 'value': ULRange.BIP10VOLTS},
                                      {'label': '± 5V', 'value': ULRange.BIP5VOLTS},
                                      {'label': '± 2V', 'value': ULRange.BIP2VOLTS},
                                      {'label': '± 1V', 'value': ULRange.BIP1VOLTS}],
                             value=ULRange.BIP10VOLTS, clearable=False, disabled=True,
                             style={'width': 200,
                                    'height': 40,
                                    'display': 'block',
                                    'border-radius': '10px',
                                    'font-size': '16px'}),

                html.Label('Sample Rate (Hz)',
                           style={'font-weight': 'bold', 'display': 'block','font-size': '20px',
                                  'margin-top': 10}),
                dcc.Input(id='sampleRate', type='number', step=1, value=1000.0,
                          style={'width': 100,'height': 30,
                                 'display': 'block',
                                 'border-radius': '10px',
                                 'font-size': '16px',
                                 'textAlign': 'center'}),
                html.Label('Samples to Display',
                           style={'font-weight': 'bold','font-size': '20px',
                                  'display': 'block', 'margin-top': 10}),
                dcc.Input(id='numberOfSamples', type='number', step=1, value=1000,
                          style={'width': 100,
                                 'height': 30,
                                 'display': 'block',
                                 'border-radius': '10px',
                                 'font-size': '16px',
                                 'textAlign': 'center'}),
                #html.Br(),
                html.P(id='textOut'),
                html.Label('Active Channels',
                           style={'font-weight': 'bold', 'display': 'block',
                                  'margin-top': 10}),
                dcc.Checklist(
                    id='channelSelections',
                    options=[
                        {'label': 'Channel 0', 'value': 0},
                        {'label': 'Channel 1', 'value': 1},
                        {'label': 'Channel 2', 'value': 2},
                        {'label': 'Channel 3', 'value': 3},
                        {'label': 'Channel 4', 'value': 4},
                        {'label': 'Channel 5', 'value': 5},
                        {'label': 'Channel 6', 'value': 6},
                        {'label': 'Channel 7', 'value': 7},
                    ],
                    labelStyle={'display': 'block'},
                    value=[0, 1, 2, 3]
                ),
                html.Div([
                    html.Button(

                        children='Start',
                        id='startButton',
                        style={'width': 160, 'height': 60, 'text-align': 'center',
                               'margin-top': 10,'border-radius': '10px'}
                    ),
                    html.Br(),
                    html.Button(

                        children='Cancel',
                        id='cancelButton',
                        style={'width': 160, 'height': 60, 'text-align': 'center',
                               'margin-top': 10, 'border-radius': '10px'}
                    ),
                    html.Div(id='button_container'),
                ]),

            ], style={'width': 320, 'height': 800, 'box-sizing': 'border-box', 'padding': 50,
                      'position': 'absolute', 'top': 0, 'left': 0}

        ),
    ], style={'position': 'relative', 'display': 'block',
              'overflow': 'hidden'}),

    dcc.Interval(
        id='timer',
        interval=1000 * 60 * 60 * 24,  # in milliseconds
        n_intervals=0
    ),
    html.Div(
        id='chartData',
        style={'display': 'none'},
        children=init_chart_data(4, 1000, 1000)
    ),
    html.Div(
        id='chartInfo',
        style={'display': 'none'},
        children=json.dumps({'sample_count': 1000})
    ),
    html.Div(
        id='status',
        style={'display': 'none'}
    ),

],fluid=True, className='dashboard-container')


@app.callback(
    Output('status', 'children'),
    [Input('startButton', 'n_clicks'),
     Input('cancelButton', 'n_clicks')],
    [State('startButton', 'children'),
     State('channelSelections', 'value'),
     State('sampleRate', 'value'),
     State('numberOfSamples', 'value'),
     State('rangeSelector', 'value'),
     State('daqSelector', 'value')],
    prevent_initial_call=False
)
def start_stop_click(btn1, btn2, btn1_label, active_channels,
                     sample_rate_val, samples_to_display_val,
                     input_range, daq_descriptor_json_str):
    """
     A callback function to change the application status when the Ready,
     Start or Stop button is clicked.

     Args:
         btn1 (int): button id
         btn2 (int): button id
         btn1_label (str): The current label on the button.
         active_channels ([int]): A list of integers corresponding to the user
            selected Active channel checkboxes.
         sample_rate_val (float): current sample rate
         samples_to_display_val (int): the width of the x-axis in samples
         input_range: ([int]): A list of integers representing input range for each channel;
         daq_descriptor_json_str: json string representing the combo box selection

     Returns:
         str: The new application status - "idle", "configured", "running"
         or "error"

     """
    sample_rate = int(sample_rate_val)
    samples_to_display = int(samples_to_display_val)
    button_clicked = ctx.triggered_id
    output = 'idle'
    if btn1 is not None and btn1 > 0:
        if button_clicked == 'startButton' and btn1_label == 'Configure':
            if samples_to_display is not None and sample_rate is not None and active_channels:
                if (99 < samples_to_display <= 10000) and (99 < sample_rate <= 12500):
                    channels = []
                    gains = []
                    active_channels.sort()
                    for channel in active_channels:
                        channels.append(channel)
                        gains.append(input_range)

                    daq_socket_manager.set_rate(sample_rate_val)
                    daq_socket_manager.set_samples(samples_to_display)
                    daq_socket_manager.set_gains(gains)
                    daq_socket_manager.set_channels(channels)

                    daq_descriptor = json.loads(daq_descriptor_json_str)
                    board_number = str(daq_descriptor['board_num'])
                    daq_socket_manager.open_list_device(board_number)
                    output = 'configured'
                else:
                    output = 'error'
            else:
                output = 'error'
        elif button_clicked == 'startButton' and btn1_label == 'Start':
            msg = daq_socket_manager.start_server()
            output = msg

    if btn2 is not None and btn2 > 0:
        if button_clicked == 'cancelButton':
            output = daq_socket_manager.stop_server()

    return output


@app.callback(
    Output('timer', 'interval'),
    Input('status', 'children'),
    [State('channelSelections', 'value'),
     State('sampleRate', 'value')],
)
def update_timer_interval(acq_state, channels, rate):
    """
    A callback function to update the timer interval.  The timer is temporarily
    disabled while processing data by setting the interval to 1 day and then
    re-enabled when the data read has been plotted.  The interval value when
    enabled is calculated based on the sample rate and some trial and error

    Args:
        acq_state (str): The application state of "idle", "configured",
            "running" or "error" - triggers the callback.
        channels (list): A list of integers corresponding to the user selected
            channels
        rate (float): The user specified sample rate

    Returns:
        refresh_rate (int): timer tick interval
    """

    # use a long refresh rate to disable timer
    refresh_rate = 1000 * 60 * 60 * 24  # 1 day

    if acq_state == 'running':
        sample_rate = int(rate)
        number_of_channels = len(channels)
        one_second = sample_rate * number_of_channels
        buffer_size = (one_second - (one_second % 96))
        half_buf = int(buffer_size / 2)
        refresh_rate = math.ceil(half_buf / sample_rate * 100)

    return refresh_rate



@app.callback(
    Output('daqSelector', 'disabled'),
    [Input('status', 'children')]
)
def disable_device_selector_dropdown(acq_state):
    """
    A callback function to disable the device selector dropdown when the
    application status changes to configured or running.
    """
    disabled = False
    if acq_state == 'configured' or acq_state == 'running':
        disabled = True
    return disabled


@app.callback(
    Output('sampleRate', 'disabled'),
    [Input('status', 'children')]
)
def disable_sample_rate_input(acq_state):
    """
    A callback function to disable the sample rate input when the
    application status changes to configured or running.
    """
    disabled = False
    if acq_state == 'configured' or acq_state == 'running':
        disabled = True
    return disabled


@app.callback(
    Output('numberOfSamples', 'disabled'),
    [Input('status', 'children')]
)
def disable_samples_to_disp_input(acq_state):
    """
    A callback function to disable the number of samples to display input
    when the application status changes to configured or running.
    """
    disabled = False
    if acq_state == 'configured' or acq_state == 'running':
        disabled = True
    return disabled


@app.callback(
    Output('channelSelections', 'options'),
    [Input('status', 'children')]
)
def disable_channel_checkboxes(acq_state):
    """
    A callback function to disable the active channel checkboxes when the
    application status changes to configured or running.
    """
    options = []
    for channel in range(CHANNEL_COUNT):
        label = 'Channel ' + str(channel)
        disabled = False
        if acq_state == 'configured' or acq_state == 'running':
            disabled = True
        options.append({'label': label, 'value': channel, 'disabled': disabled})
    return options


@app.callback(
    Output('led_0', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_0(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 0
    """
    update_color = 'red'
    channel = 0
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_1', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_1(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 1
    """
    update_color = 'red'
    channel = 1
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_2', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_2(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 2
    """
    update_color = 'red'
    channel = 2
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_3', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_3(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 3
    """
    update_color = 'red'
    channel = 3
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_4', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_4(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 4
    """
    update_color = 'red'
    channel = 4
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color



@app.callback(
    Output('led_5', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_5(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 5
    """
    update_color = 'red'
    channel = 5
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color



@app.callback(
    Output('led_6', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')]
)
def disable_channel_led_6(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 6
    """
    update_color = 'red'
    channel = 6
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_7', 'color'),
    [Input('status', 'children'),
     Input('channelSelections', 'value')],
)
def disable_channel_led_7(acq_state, active_channels):
    """
    There is no disable feature on the LED, so instead, make
    it appear has if it is disabled by changing the color of
    the numbers to light grey. This callback disables led 7
    """
    update_color = 'red'
    channel = 7
    if acq_state == 'configured' or acq_state == 'running':
        if channel in active_channels:
            update_color = 'red'
        else:
            update_color = 'lightgrey'

    return update_color


@app.callback(
    Output('led_0', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_0', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_0(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 0
    if led not in active_channels:
        return led_value

    value_backup_str = led_value


    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return value_backup_str



@app.callback(
    Output('led_1', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_1', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_1(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 1
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value


@app.callback(
    Output('led_2', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_2', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_2(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 2
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value

@app.callback(
    Output('led_3', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_3', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_3(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 3
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value

@app.callback(
    Output('led_4', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_4', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_4(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 4
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value

@app.callback(
    Output('led_5', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_5', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_5(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 5
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value


@app.callback(
    Output('led_6', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_6', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_6(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 6
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value


@app.callback(
    Output('led_7', 'value'),
    Input('chartData', 'children'),
    [State('status', 'children'),
    State('channelSelections', 'value'),
    State('led_7', 'value'),
    State('numberOfSamples', 'value')]
)
def update_led_7(chart_data_json_str, acq_state, active_channels, led_value, samples_to_display_str):
    """
    The update_led_# callbacks updates an individual LED display. If the LED is not an active channel, it
    exits. If the LED is an active channel, it performs a mean average on the chartData
    """
    led = 7
    if led not in active_channels:
        return led_value

    position = get_channel_position(led, active_channels)

    chart_data = json.loads(chart_data_json_str)
    current_sample_count = int(chart_data['sample_count'])
    if position != -1 and current_sample_count > int(samples_to_display_str):

        data = chart_data['data']
        voltage = statistics.mean(data[position])
        format_float = f"{voltage:.3f}"
        return format_float
    else:
        return led_value



@app.callback(
    Output('startButton', 'disabled'),
    Input('status', 'children')
)
def disable_configure_start(acq_state):
    """
    A callback function to disable the start button when the
    application status changes to running.
    """
    disabled = False
    if acq_state == 'running':
        disabled = True
    return disabled


@app.callback(
    Output('startButton', 'children'),
    [Input('status', 'children')]
)
def update_start_stop_button_name(acq_state):
    """
    A callback function to update the label on the button when the application
    status changes.

    Args:
        acq_state (str): The application state of "idle", "configured",
            "running" or "error" - triggers the callback.

    Returns:
        str: The new button label of "Ready", "Start" or "Stop"
    """

    output = 'Configure'
    if acq_state == 'configured' or acq_state == 'running':
        output = 'Start'
    elif acq_state == 'idle':
        output = 'Configure'

    return output


@app.callback(
    Output('chartData', 'children'),
    [Input('timer', 'n_intervals'),
     Input('status', 'children')],
    [State('chartData', 'children'),
     State('numberOfSamples', 'value'),
     State('sampleRate', 'value'),
     State('channelSelections', 'value')],
    prevent_initial_call=False
)
def update_strip_chart_data(_n_intervals, acq_state, chart_data_json_str,
                            number_of_samples, sample_rate, active_channels):
    """
    A callback function to update the chart data stored in the chartData HTML
    div element.  The chartData element stores the existing data
    values, allowing data to be shared between callback functions. Global
    variables cannot be used to share data between callbacks (see
    https://dash.plotly.com/basic-callbacks).

    Args:
        _n_intervals (int): Number of timer intervals - triggers the callback.
        acq_state (str): The application state of "idle", "configured",
            "running" or "error" - triggers the callback.
        chart_data_json_str (str): A string representation of a JSON object
            containing the current chart data.
        number_of_samples (float): The number of samples to be displayed.
        active_channels ([int]): A list of integers corresponding to the user
            selected active channel numbers.
        sample_rate (float): the current sample rate

    Returns:
        str: A string representation of a JSON object containing the updated
        chart data.
    """

    updated_chart_data = chart_data_json_str
    samples_to_display = int(number_of_samples)
    num_channels = len(active_channels)

    if acq_state == 'running':

        data = []
        chart_data = json.loads(chart_data_json_str)
        if daq_socket_manager.get_status() is True:
            data = daq_socket_manager.get_data_list()


        sample_count = add_samples_to_data(samples_to_display, num_channels,
                                           chart_data, data, int(sample_rate))

        # Update the total sample count.
        chart_data['sample_count'] = sample_count

        updated_chart_data = json.dumps(chart_data)

    elif acq_state == 'configured':
        # Clear the data in the strip chart when Ready is clicked.
        updated_chart_data = init_chart_data(num_channels, samples_to_display, sample_rate)

    return updated_chart_data


def add_samples_to_data(number_of_samples, num_chans, chart_data, data, sample_rate):
    """
    Adds the samples read from the simulated device to the chart_data object
    used to update the strip chart.

    Args:
        number_of_samples (int): The number of samples to be displayed.
        num_chans (int): The number of selected channels.
        chart_data (dict): A dictionary containing the data that updates the
            strip chart display.
        data: A list to hold available device data
        sample_rate (float): the current sample rate

    Returns:
        int: The updated total sample count after the data is added.

    """

    num_samples_read = int(len(data) / num_chans)
    current_sample_count = int(chart_data['sample_count'])


    if num_samples_read < num_chans:
        return current_sample_count

    # Convert lists to deque objects with the maximum length set to the number
    # of samples to be displayed.  This will pop off the oldest data
    # automatically when new data is appended.
    chart_data['samples'] = deque(chart_data['samples'],
                                  maxlen=number_of_samples)
    for chan in range(num_chans):
        chart_data['data'][chan] = deque(chart_data['data'][chan],
                                         maxlen=number_of_samples)

    start_sample = 0
    if num_samples_read > number_of_samples:
        start_sample = num_samples_read - number_of_samples

    for sample in range(start_sample, num_samples_read):
        chart_data['samples'].append(float(current_sample_count + sample) * 1 / sample_rate)

        for chan in range(num_chans):
            data_index = sample * num_chans + chan
            chart_data['data'][chan].append(data[data_index])

    # Convert deque objects back to lists to be written to div
    # element.
    chart_data['samples'] = list(chart_data['samples'])
    for chan in range(num_chans):
        chart_data['data'][chan] = list(chart_data['data'][chan])

    return current_sample_count + num_samples_read


@app.callback(
    Output('stripChart', 'figure'),
    Input('chartData', 'children'),
    State('channelSelections', 'value'),
    prevent_initial_call=False
)
def update_strip_chart(chart_data_json_str, active_channels):
    """
    A callback function to update the strip chart display when new data is read.

    Args:
        chart_data_json_str (str): A string representation of a JSON object
            containing the current chart data - triggers the callback.

        active_channels ([int]): A list of integers corresponding to the user
            selected Active channel checkboxes.

    Returns:
        object: A figure object for a dash-core-components Graph, updated with
        the most recently read data.
    """
    data = []
    xaxis_range = [0, 1000]

    chart_data = json.loads(chart_data_json_str)
    dtime = 0.1
    if 'samples' in chart_data and chart_data['samples']:
        xaxis_range = [min(chart_data['samples']), max(chart_data['samples'])]
        chart_time = float(max(chart_data['samples']) - min(chart_data['samples']))
        dtime = chart_time / 10.0

    if 'data' in chart_data:
        data = chart_data['data']

    plot_data = []
    colors = ['#DD3222', '#FFC000', '#3482CB', '#FF6A00',
              '#75B54A', '#808080', '#6E1911', '#806000']
    # Update the serie data for each active channel.
    # UL requires that the device channels are ordered from low to high
    # active_channels is sorted when programming the device. So we need
    # to sort here too
    active_channels.sort()
    for chan_idx, channel in enumerate(active_channels):
        scatter_serie = go.Scatter(
            x=list(chart_data['samples']),
            y=list(data[chan_idx]),
            name='Channel {0:d}'.format(channel),
            marker={'color': colors[channel]}
        )
        plot_data.append(scatter_serie)

    figure = {
        'data': plot_data,
        'layout': go.Layout(
            xaxis=dict(title='Time (s)', range=xaxis_range, tick0=0.0, nticks=10, dtick=dtime, fixedrange=True),
            yaxis=dict(title='Voltage (V)', nticks=10, fixedrange=True),
            margin=dict(l=50, r=50, t=50, b=50),
            plot_bgcolor='#e6e6e6',
            paper_bgcolor='#e6e6e6',
            legend=dict(orientation='v', visible=True),
            showlegend=True,

        )
    }
    return figure


@app.callback(
    Output('chartInfo', 'children'),
    Input('stripChart', 'figure'),
    [State('chartData', 'children')],
    prevent_initial_call=False
)
def update_chart_info(_figure, chart_data_json_str):
    """
    A callback function to set the sample count for the number of samples that
    have been displayed on the chart.

    Args:
        _figure (object): A figure object for a dash-core-components Graph for
            the strip chart - triggers the callback.
        chart_data_json_str (str): A string representation of a JSON object
            containing the current chart data - triggers the callback.

    Returns:
        str: A string representation of a JSON object containing the chart info
        with the updated sample count.

    """

    chart_data = json.loads(chart_data_json_str)
    chart_info = {'sample_count': chart_data['sample_count']}

    return json.dumps(chart_info)

@app.callback(
    Output('textOut', 'children'),
    [Input('status', 'children')],
    [State('sampleRate', 'value'),
     State('numberOfSamples', 'value'), ]
)  # pylint: disable=too-many-arguments
def update_text(acq_state, sample_rate, number_of_samples):
    """
    A callback function to display X-Axis time span.

    Args:
        acq_state (str): The application state of "idle", "configured",
            "running" or "error" - triggers the callback.
        sample_rate (float): The user specified sample rate value.
        number_of_samples (float): The number of samples to be displayed.

    Returns:
        str: X-axis time span.

    """

    t = 1 / sample_rate
    span = number_of_samples * t

    return f'X-Axis Time Span: {span:.3f} sec.'



@app.callback(
    Output('errorDisplay', 'children'),
    [Input('status', 'children')],
    [State('sampleRate', 'value'),
     State('numberOfSamples', 'value'),
     State('channelSelections', 'value')],
    prevent_initial_call=False
)
def update_error_message(acq_state, sample_rate, number_of_samples, active_channels):
    """
    A callback function to display error messages.

    Args:
        acq_state (str): The application state of "idle", "configured",
            "running" or "error" - triggers the callback.
        sample_rate (float): The user specified sample rate value.
        number_of_samples (float): The number of samples to be displayed.
        active_channels ([int]): A list of integers corresponding to the user
            selected Active channel checkboxes.

    Returns:
        str: The error message to display.

    """
    error_message = ''
    if acq_state == 'error':
        num_active_channels = len(active_channels)
        _fmax = 12500
        _fmin = 1000
        if num_active_channels <= 0:
            error_message += 'Invalid channel selection (min 1); '

        if sample_rate > _fmax:
            error_message += 'Invalid Sample Rate (max: '
            error_message += str(_fmax) + '); '
        if sample_rate < _fmin:
            error_message += 'Invalid Sample Rate (min: '
            error_message += str(_fmin) + '); '

        if number_of_samples > 1000:
            error_message += 'Invalid Samples to display (range: 100-10000); '
        if number_of_samples < 100:
            error_message += 'Invalid Samples to display (range: 100-1000); '
    return error_message


def get_ip_address():
    """ Utility function to get the IP address of the device. """
    ip_address = '127.0.0.1'  # Default to localhost
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(('1.1.1.1', 1))  # Does not have to be reachable
        ip_address = sock.getsockname()[0]
    finally:
        sock.close()

    return ip_address


if __name__ == '__main__':

    # ip = get_ip_address()
    # or
    ip = '127.0.0.1'

    app.run(debug=False, use_reloader=True, host=ip, port=55555)

    daq_socket_manager.disconnect()
