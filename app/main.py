from flask import Flask, render_template, Response, request
from datetime import datetime,timedelta
import io
import cbpro
# import matplotlib.pyplot as plt
# import matplotlib
import pandas as pd
import yaml
import math
import os
import time
# from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
# from matplotlib.backends.backend_svg import FigureCanvasSVG
# from matplotlib.figure import Figure
from apscheduler.schedulers.background import BackgroundScheduler

import plotly
import plotly.graph_objs as go
import plotly.express as px
import json

BUY_LOCK = True
PLT_LOCK = True

product = []
STATE_P = []
STATE_R = []

NSTATE = []

PARAM1 = 25
PARAM2 = 50

PARAMRSI1 = 70
PARAMRSI2 = 30

STRATEGY = 'MA'

def main():

    with open('app/state.yaml') as f:
        STATE = yaml.load(f,Loader=yaml.FullLoader)


    auth_client = cbpro.PublicClient()

    items = auth_client.get_product_historic_rates('BTC-USD',granularity=300)

    x = []
    y = []
    for item in items[::-1]:
        #plt.plot(item[0],item[4],'.')
        x.append(item[0])
        y.append(item[4])
    # plt.plot(x,y,'-g')
    price = pd.Series(y)


    global product
    product = pd.DataFrame({'time' : x, 'price': y})

    # n1 = 8
    # n2 = 20
    # n1 = 20
    # n2 = 45
    global PARAM1, PARAM2
    n1 = min(PARAM1, PARAM2)
    n2 = max(PARAM2, PARAM1)
    product['SMA1'] = product['price'].rolling(n1).mean()
    product['SMA2'] = product['price'].rolling(n2).mean()

    stance = False
    STATE['buylocs']['locs'] = []
    STATE['buylocs']['vals'] = []
    STATE['selllocs']['locs'] = []
    STATE['selllocs']['vals'] = []
    for t,s1,s2,p in zip(product['time'][n2:],product['SMA1'][n2:],product['SMA2'][n2:],product['price'][n2:]):
        if not stance and (s1>s2):
            stance = True
            # btc += (money*.995)/p #only 99.5% goes in
            # money -= money ##fix this
            # print(str(money) + '    ' + str(btc))
            STATE['buylocs']['locs'].append(float(t))
            STATE['buylocs']['vals'].append(float(s1))
        elif stance and (s2>s1):
            stance = False
            # plt.plot(t,p,'.r')
            # money += btc*p*.995 #only 99.5% comes back out
            # btc -= btc
            # print(str(money) + '    ' + str(btc))
            STATE['selllocs']['locs'].append(float(t))
            STATE['selllocs']['vals'].append(float(s2))


    stance = STATE['bought']

    numbuy = STATE['numbuy']
    numsell = STATE['numsell']

    s1 = product['SMA1'].iloc[-1]
    s2 = product['SMA2'].iloc[-1]

    if not PLT_LOCK:
        plt.show()

    date = datetime.now()



    global STATE_P
    STATE_P = STATE
    # return STATE

    #RSI stuff
    rsi_period = 14
    chg = product['price'].diff(1)
    gain = chg.mask(chg < 0,0)
    product['gain'] = gain
    loss = chg.mask(chg > 0,0)
    product['loss'] = loss

    avg_gain = gain.ewm(com = rsi_period -1, min_periods = rsi_period).mean()
    avg_loss = loss.ewm(com = rsi_period -1, min_periods = rsi_period).mean()

    product['avg_gain'] = avg_gain
    product['avg_loss'] = avg_loss
    rs = abs(avg_gain/avg_loss)
    rsi = 100-(100/(1+rs))
    # print(rsi)
    # STATE['RSI'] = rsi
    product['RSI'] = rsi

    stance = False
    with open('app/state.yaml') as f:
        STATE = yaml.load(f,Loader=yaml.FullLoader)
    STATE['buylocs']['locs'] = []
    STATE['buylocs']['vals'] = []
    STATE['buylocs']['valsr'] = []
    STATE['selllocs']['locs'] = []
    STATE['selllocs']['vals'] = []
    STATE['selllocs']['valsr'] = []
    p1 = max(PARAMRSI1,PARAMRSI2)
    p2 = min(PARAMRSI1,PARAMRSI2)
    for t,r,p in zip(product['time'],product['RSI'],product['price']):
        if not stance and (r<p2):
            stance = True
            # btc += (money*.995)/p #only 99.5% goes in
            # money -= money ##fix this
            # print(str(money) + '    ' + str(btc))
            STATE['buylocs']['locs'].append(float(t))
            STATE['buylocs']['vals'].append(float(p))
            STATE['buylocs']['valsr'].append(float(r))
        elif stance and (r>p1):
            stance = False
            # plt.plot(t,p,'.r')
            # money += btc*p*.995 #only 99.5% comes back out
            # btc -= btc
            # print(str(money) + '    ' + str(btc))
            STATE['selllocs']['locs'].append(float(t))
            STATE['selllocs']['vals'].append(float(p))
            STATE['selllocs']['valsr'].append(float(r))

    global STATE_R
    STATE_R = STATE


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
    fig.update_layout(autosize=True,hovermode='x unified',title='Moving Average with window size: '  + str(PARAM1) + ' vs. ' + str(PARAM2))
    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    with open('plot_p.json','w') as f:
        # print(type(graphJSON))
        json.dump(graphJSON,f)


    return graphJSON

def create_plot_r():
    # fig = px.line(product,x='time',y=['price','SMA1','SMA2'])
    #
    # color_discrete_map = {'vals': 'rgb(255,0,0)'}
    # fig2 = go.Scatter(x=STATE_P['buylocs']['locs'],y=STATE_P['buylocs']['vals'],mode='markers',marker_color='rgba(0, 255, 0, .8)')
    # fig3 = go.Scatter(x=STATE_P['selllocs']['locs'],y=STATE_P['selllocs']['vals'],mode='markers',marker_color='rgba(255, 0, 0, .8)')
    # data = [
    #     fig.data[0],fig.data[1],fig.data[2],fig2,fig3
    # ]

    global PARAMRSI1, PARAMRSI2
    p1 = PARAMRSI1
    p2 = PARAMRSI2
    fig = go.Figure()
    strstamps = []
    for elem in product['time']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=product['RSI'],mode='lines',name='price',marker_color='rgba(0,135,0,.6)'))

    strstamps = []
    for elem in product['time']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=[p1]*len(product['time']),mode='lines',name='Upper Bound',marker_color='rgba(0,13,130,.6)'))
    strstamps = []
    for elem in product['time']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=[p2]*len(product['time']),mode='lines',name='Lower Bound',marker_color='rgba(0,13,130,.6)'))


    strstamps = []
    for elem in STATE_R['buylocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_R['buylocs']['valsr'],name='buy',mode='markers',marker_color='rgba(0, 245, 95, 1)'))
    strstamps = []
    for elem in STATE_R['selllocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_R['selllocs']['valsr'],name='sell',mode='markers',marker_color='rgba(255, 0, 0, .9)'))
    fig.update_layout(autosize=True,hovermode='x unified',title='Relative Strength Index with UpperBound = ' + str(PARAMRSI1) + ', and LowerBound = ' + str(PARAMRSI2) )
    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    # with open('plot_r.json','w') as f:
    #     # print(type(graphJSON))
    #     json.dump(graphJSON,f)

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
    strstamps = []
    for elem in product['time']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=product['price'],mode='lines',name='price',marker_color='rgba(0,135,0,.6)'))

    strstamps = []
    for elem in STATE_R['buylocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_R['buylocs']['vals'],name='buy',mode='markers',marker_color='rgba(0, 245, 95, 1)'))
    strstamps = []
    for elem in STATE_R['selllocs']['locs']:
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=STATE_R['selllocs']['vals'],name='sell',mode='markers',marker_color='rgba(255, 0, 0, .9)'))
    fig.update_layout(autosize=True,hovermode='x unified',title='Price')
    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    with open('plot_m.json','w') as f:
        # print(type(graphJSON))
        json.dump(graphJSON,f)


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
        strstamps.append(datetime.fromtimestamp(elem).strftime('%Y-%m-%d %H:%M:%S'))
    fig.add_trace(go.Scatter(x=strstamps,y=newdict['BTCOT'],mode='lines',name='money',marker_color='rgba(0,155,0,.6)'))
    fig.update_layout(hovermode='x unified',title='BTC')

    data = fig
    graphJSON = json.dumps(data, cls=plotly.utils.PlotlyJSONEncoder)

    with open('plot_b.json','w') as f:
        # print(type(graphJSON))
        json.dump(graphJSON,f)


    # with open('test.json') as f:
    #     graphJSONn = json.load(f)
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
    # plot_r = create_plot_r()
    # plot_b = create_plot_b()
    # return render_template('index.html',plot_p=plot_p, plot_m=plot_m, plot_b=plot_b)
    return render_template('index.html',plot_p=plot_p)

@app.route('/', methods=['POST'])
def my_form_post():
    global PARAM1, PARAM2, STRATEGY, PARAMRSI1, PARAMRSI2

    key= list(request.form.items())[0][0]
    # print(key)

    if key == 'Overview':
        return render_template('overview.html')
    elif key == 'MovingAvg':
        STRATEGY = 'MA'
        plot_p = create_plot_p()
        return render_template('index.html', plot_p=plot_p)
    elif key == 'RSI':
        STRATEGY = 'RSI'
        plot_r = create_plot_r()
        plot_m = create_plot_m()
        return render_template('rsi.html', plot_r=plot_r, plot_m=plot_m)
    # else:
    #     if STRATEGY == 'MA':
    #         PARAM1 = int(request.form['param1'])
    #         PARAM2 = int(request.form['param2'])
    #         main()
    #         plot_p = create_plot_p()
    #         return render_template('index.html',plot_p=plot_p)
    #     elif STRATEGY == 'RSI':
    #         PARAMRSI1 = int(request.form['param1'])
    #         PARAMRSI2 = int(request.form['param2'])
    #         main()
    #         plot_r = create_plot_r()
    #         plot_m = create_plot_m()
    #         return render_template('rsi.html',plot_r=plot_r, plot_m=plot_m)
    elif key == 'param1':

        PARAM1 = int(request.form['param1'])
        PARAM2 = int(request.form['param2'])
        main()
        plot_p = create_plot_p()
        return render_template('index.html',plot_p=plot_p)
    elif key == 'param1rsi':
        PARAMRSI1 = int(request.form['param1rsi'])
        PARAMRSI2 = int(request.form['param2rsi'])
        main()
        plot_r = create_plot_r()
        plot_m = create_plot_m()
        return render_template('rsi.html',plot_r=plot_r, plot_m=plot_m)



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

# @app.route('/money.png')
# def plot_money():
#     fig = Figure()
#     axis = fig.add_subplot(1,1,1)
#     axis.plot_date(STATE_P['timeOT'],STATE_P['moneyOT'],'-')
#     output = io.BytesIO()
#     FigureCanvasSVG(fig).print_svg(output)
#     return Response(output.getvalue(), mimetype='image/svg+xml')
#
# @app.route('/btc.png')
# def plot_btc():
#     fig = Figure()
#     axis = fig.add_subplot(1,1,1)
#     axis.plot_date(STATE_P['timeOT'],STATE_P['BTCOT'],'-')
#     output = io.BytesIO()
#     FigureCanvasSVG(fig).print_svg(output)
#     return Response(output.getvalue(), mimetype='image/svg+xml')
