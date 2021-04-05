from flask import Flask, render_template, Response
from datetime import datetime
import io
import cbpro
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
import yaml
import math
import os
import time
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.figure import Figure
from apscheduler.schedulers.background import BackgroundScheduler

import plotly
import plotly.graph_objs as go
import plotly.express as px
import json

BUY_LOCK = False
PLT_LOCK = True

product = []
STATE_P = []

def main():

    with open('app/state.yaml') as f:
        STATE = yaml.load(f,Loader=yaml.FullLoader)

    # STATE['bought'] = not STATE['bought']

    #print(auth_client.get_accounts())
    balance = float(auth_client.get_account("c7e286f1-e04f-46fb-ace5-34a27245c95f")['available'])
    balance = math.floor(balance*100)/100.0

    bitcoin = float(auth_client.get_account("e02112f4-5daf-4970-9ce1-563e5460e523")['available'])

    #print(balance)

    ##print(auth_client.get_product_order_book('BTC-USD'))

    #print(auth_client.get_product_ticker(product_id='BTC-USD'))

    ##print(auth_client.get_product_historic_rates('BTC-USD',granularity=60))

    #print(auth_client.get_product_24hr_stats('BTC-USD'))

    #this should be done with web socket instead if polling frequently?
    items = auth_client.get_product_historic_rates('BTC-USD',granularity=300)

    x = []
    y = []
    for item in items[::-1]:
        #plt.plot(item[0],item[4],'.')
        x.append(item[0])
        y.append(item[4])
    # plt.plot(x,y,'-g')
    price = pd.Series(y)

    #sma1 = ta.volatility.bollinger_mavg(price, n=n1, fillna=False)
    # for i in range(len(x)):
    #     plt.plot(x[i],sma1[i],'.')

    global product
    product = pd.DataFrame({'time' : x, 'price': y})

    # n1 = 8
    # n2 = 20
    # n1 = 20
    # n2 = 45
    n1 = 25
    n2 = 50
    product['SMA1'] = product['price'].rolling(n1).mean()
    product['SMA2'] = product['price'].rolling(n2).mean()




    stance = STATE['bought']
    money = balance
    btc = bitcoin
    numbuy = STATE['numbuy']
    numsell = STATE['numsell']
    #print(money)
    #.5% == *.005
    # for t,s1,s2,p in zip(product['time'][n2:],product['SMA1'][n2:],product['SMA2'][n2:],product['price'][n2:]):
    #     if not stance and (s1>s2):
    #         stance = True
    #         plt.plot(t,p,'.g')
    #         btc += (money*.995)/p #only 99.5% goes in
    #         money -= money ##fix this
    #         print(str(money) + '    ' + str(btc))
    #     elif stance and (s2>s1):
    #         stance = False
    #         plt.plot(t,p,'.r')
    #         money += btc*p*.995 #only 99.5% comes back out
    #         btc -= btc
    #         print(str(money) + '    ' + str(btc))


    s1 = product['SMA1'].iloc[-1]
    s2 = product['SMA2'].iloc[-1]
    #t = product['time'].iloc[-1]
    # print(stance)
    # print(s1)
    # print(s2)


    if not stance and (s1 > s2):

        print('Buying BTC with funds: ' + str(money))
        if not BUY_LOCK:
            auth_client.place_market_order(product_id='BTC-USD',side='buy',funds = money)
            stance = True
            numbuy+=1
            STATE['buylocs']['locs'].append(float(product['time'].iloc[-1]))
            STATE['buylocs']['vals'].append(float(product['price'].iloc[-1]))
    elif stance and (s2>s1):

        print('Selling BTC with size: ' + str(btc))
        if not BUY_LOCK:
            auth_client.place_market_order(product_id='BTC-USD',side='sell',size = btc)
            stance = False
            numsell+=1
            STATE['selllocs']['locs'].append(float(product['time'].iloc[-1]))
            STATE['selllocs']['vals'].append(float(product['price'].iloc[-1]))



    #update STATE



    # print('---')
    # print(money)
    # print(btc)
    # print(stance)
    if not PLT_LOCK:
        plt.show()

    #time.sleep(5)
    date = datetime.now()
    mpldate = matplotlib.dates.date2num(date)
    #print(date.isoformat())

    balance = float(auth_client.get_account("c7e286f1-e04f-46fb-ace5-34a27245c95f")['available'])
    bitcoin = float(auth_client.get_account("e02112f4-5daf-4970-9ce1-563e5460e523")['available'])

    STATE['bought'] = stance
    STATE['money'] = balance
    STATE['BTC'] = bitcoin
    STATE['last'] = date.isoformat()
    STATE['numbuy'] = numbuy
    STATE['numsell'] = numsell
    STATE['moneyOT'].append(balance)
    STATE['BTCOT'].append(bitcoin)
    STATE['timeOT'].append(mpldate)
    with open('app/state.yaml', 'w') as f:
        yaml.dump(STATE, f)
        print('Updated YAML')

    global STATE_P
    STATE_P = STATE
    # return STATE



def create_plot_p():
    # fig = px.line(product,x='time',y=['price','SMA1','SMA2'])
    #
    # color_discrete_map = {'vals': 'rgb(255,0,0)'}
    # fig2 = go.Scatter(x=STATE_P['buylocs']['locs'],y=STATE_P['buylocs']['vals'],mode='markers',marker_color='rgba(0, 255, 0, .8)')
    # fig3 = go.Scatter(x=STATE_P['selllocs']['locs'],y=STATE_P['selllocs']['vals'],mode='markers',marker_color='rgba(255, 0, 0, .8)')
    # data = [
    #     fig.data[0],fig.data[1],fig.data[2],fig2,fig3
    # ]

    fig = go.Figure()
    strstamps = []
    for elem in product['time']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=product['price'],mode='lines',name='price',marker_color='rgba(0,135,0,.6)'))
    fig.add_trace(go.Scatter(x=strstamps,y=product['SMA1'],mode='lines',name='SMA1',marker_color='rgba(255,0,0,.6)'))
    fig.add_trace(go.Scatter(x=strstamps,y=product['SMA2'],mode='lines',name='SMA2',marker_color='rgba(0,0,255,.6)'))

    strstamps = []
    for elem in STATE_P['buylocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_P['buylocs']['vals'],name='buy',mode='markers',marker_color='rgba(0, 245, 95, 1)'))
    strstamps = []
    for elem in STATE_P['selllocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_P['selllocs']['vals'],name='sell',mode='markers',marker_color='rgba(255, 0, 0, .9)'))
    fig.update_layout(autosize=True,hovermode='x unified',title='Overview')
    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

def create_plot_m():
    # fig = px.line(product,x='time',y=['price','SMA1','SMA2'])
    #
    # color_discrete_map = {'vals': 'rgb(255,0,0)'}
    # fig2 = go.Scatter(x=STATE_P['buylocs']['locs'],y=STATE_P['buylocs']['vals'],mode='markers',marker_color='rgba(0, 255, 0, .8)')
    # fig3 = go.Scatter(x=STATE_P['selllocs']['locs'],y=STATE_P['selllocs']['vals'],mode='markers',marker_color='rgba(255, 0, 0, .8)')
    # data = [
    #     fig.data[0],fig.data[1],fig.data[2],fig2,fig3
    # ]


    fig = go.Figure()

    newdict = {'timeOT' : [], 'moneyOT': []}
    for time,money in zip(STATE_P['timeOT'],STATE_P['moneyOT']):
        if money > .1:
            newdict['timeOT'].append(time)
            newdict['moneyOT'].append(money)

    strstamps = []
    for elem in newdict['timeOT']:
        strstamps.append(matplotlib.dates.num2date(elem))

    fig.add_trace(go.Scatter(x=strstamps,y=newdict['moneyOT'],mode='lines',name='money',marker_color='rgba(0,155,0,.6)'))
    fig.update_layout(hovermode='x unified',title='Money')

    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

def create_plot_b():
    # fig = px.line(product,x='time',y=['price','SMA1','SMA2'])
    #
    # color_discrete_map = {'vals': 'rgb(255,0,0)'}
    # fig2 = go.Scatter(x=STATE_P['buylocs']['locs'],y=STATE_P['buylocs']['vals'],mode='markers',marker_color='rgba(0, 255, 0, .8)')
    # fig3 = go.Scatter(x=STATE_P['selllocs']['locs'],y=STATE_P['selllocs']['vals'],mode='markers',marker_color='rgba(255, 0, 0, .8)')
    # data = [
    #     fig.data[0],fig.data[1],fig.data[2],fig2,fig3
    # ]


    fig = go.Figure()
    newdict = {'timeOT' : [], 'BTCOT': []}
    for time,money in zip(STATE_P['timeOT'],STATE_P['BTCOT']):
        if money != 0.0:
            newdict['timeOT'].append(time)
            newdict['BTCOT'].append(money)

    strstamps = []
    for elem in newdict['timeOT']:
        strstamps.append(matplotlib.dates.num2date(elem))
    fig.add_trace(go.Scatter(x=strstamps,y=newdict['BTCOT'],mode='lines',name='money',marker_color='rgba(0,155,0,.6)'))
    fig.update_layout(hovermode='x unified',title='BTC')

    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    return graphJSON

sched = BackgroundScheduler(daemon=True)
sched.add_job(main,'interval',minutes=5)
sched.start()

app = Flask(__name__,template_folder='templates')



@app.route("/")
def home_view():
    # global STATE_P
    # STATE_P = main()
    # return "<h1>Welcome to " + str(stance) + "Geeks for Geeks</h1>"
    main()
    plot_p = create_plot_p()
    plot_m = create_plot_m()
    plot_b = create_plot_b()
    return render_template('index.html',plot_p=plot_p, plot_m=plot_m, plot_b=plot_b)

@app.route('/prices.png')
def plot_prices():
    fig = Figure()
    axis = fig.add_subplot(1,1,1)
    axis.plot(product['time'],product['price'],'-g')
    axis.plot(product['time'],product['SMA1'],'-r')
    axis.plot(product['time'],product['SMA2'],'-b')
    axis.plot(STATE_P['buylocs']['locs'],STATE_P['buylocs']['vals'],'.y')
    axis.plot(STATE_P['selllocs']['locs'],STATE_P['selllocs']['vals'],'.r')
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype='image/svg+xml')

@app.route('/money.png')
def plot_money():
    fig = Figure()
    axis = fig.add_subplot(1,1,1)
    axis.plot_date(STATE_P['timeOT'],STATE_P['moneyOT'],'-')
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype='image/svg+xml')

@app.route('/btc.png')
def plot_btc():
    fig = Figure()
    axis = fig.add_subplot(1,1,1)
    axis.plot_date(STATE_P['timeOT'],STATE_P['BTCOT'],'-')
    output = io.BytesIO()
    FigureCanvasSVG(fig).print_svg(output)
    return Response(output.getvalue(), mimetype='image/svg+xml')
