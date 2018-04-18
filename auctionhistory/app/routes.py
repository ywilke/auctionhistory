from flask import render_template, flash, redirect, request
from app import app
import plotly.offline as plotly
import plotly.graph_objs as plotgo
import pandas as pd
import datetime
import sqlite3 as sqlite
import numpy as np
import datetime #timing

con = sqlite.connect('import/AH_history.db') #db path
cur = con.cursor()

def copper_to_price(copper): # Converts copper int to a normal price
    copper = int(copper)
    s, c = divmod(copper, 100)
    g, s = divmod(s, 100)
    if g == 0:
        if s == 0:
            return '{}c'.format(c)
        else:
            return '{}s{}c'.format(s, c)
    else:
        return '{}g{}s{}c'.format(g, s, c)


def get_date(unix_time):# Converts unix time dd-mm-yy
    return datetime.datetime.fromtimestamp(unix_time).strftime('%d-%m-%y')

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')

@app.route('/Lordaeron_Horde', methods=['GET'])
def login():
    start_time = (datetime.datetime.now()) #timing
    search_q = request.args.get('search', '')
    if search_q:
        print (str(datetime.datetime.now() - start_time)+' query prepared') #timing
        # query data
        cur.execute("SELECT itemname, price, scantime FROM LOR_H_prices "
                    "INNER JOIN LOR_H_items ON LOR_H_prices.itemid=LOR_H_items.itemid "
                    "INNER JOIN LOR_H_scans ON LOR_H_prices.scanid=LOR_H_scans.scanid "
                    "WHERE LOR_H_items.itemname IS ?;",(search_q,))
        datapoints = sorted(cur.fetchall(), key=lambda x: x[2])
        print (str(datetime.datetime.now() - start_time)+' query executed')#timing
        if not datapoints: # need to add error message
            return render_template('Lordaeron_Horde.html', title='Lordaeron Horde', error='Item was not found in the database. Make sure you wrote the exact item name.')
        # prepare query data
        item = datapoints[0][0]
        time_list = []
        price_list = []
        for i in datapoints:
            time_list.append(i[2])
            price_list.append(i[1])
        print (str(datetime.datetime.now() - start_time)+' query data processed')#timing
        # generate moving average
        window = '5D'
        index = pd.to_datetime(time_list, unit = 's')
        df = pd.DataFrame({'prices': price_list}, index)
        dfr = df.rolling('5D').mean()
        print (str(datetime.datetime.now() - start_time)+' MA generated')#timing
        # set traces
        trace_price = plotgo.Scattergl(
        x = index,
        y = price_list,
        text = list(map(copper_to_price, price_list)),
        hoverinfo = 'text+x',
        name = item,
        mode = 'markers',
        )
        
        trace_avg = plotgo.Scattergl(
        x = dfr.axes[0],
        y = dfr['prices'],
        text = list(map(copper_to_price, dfr['prices'])),
        hoverinfo = 'text+x',
        name = 'average ({window})'.format(window = window),
        mode = 'lines',
        )
        
        plotdata = [trace_price, trace_avg]
        print (str(datetime.datetime.now() - start_time)+' traces generated')#timing
        # layout
        max_val = max(price_list)
        nr_ticks = 6
        y_val = 0
        y_vals = []
        
        t1 = (max_val / nr_ticks)
        t2 = int(np.log10(t1))
        t3 = int(t1 / (10**t2)) + 1
        step = t3*10**t2
        for i in range(nr_ticks):
            y_val += step
            y_vals.append(y_val)
        
        layout = plotgo.Layout(
            title = "{item}'s price history".format(item = item),
            font = dict(
                color = '#ffffff'
                
            ),
            yaxis=dict(
                gridcolor='rgba(26, 26, 26, 0.6)',
                tickvals = y_vals,
                ticktext = list(map(copper_to_price, y_vals))
            ),
            xaxis = dict(
                gridcolor='rgba(26, 26, 26, 0.2)',
                hoverformat = '%e %b %Y'
            ),
            paper_bgcolor='#263238',
            plot_bgcolor='#263238'
            
        )
        print (str(datetime.datetime.now() - start_time)+' layout generated')#timing
        fig = dict(data=plotdata, layout=layout)
        print (str(datetime.datetime.now() - start_time)+' fig generated')#timing
        chart = plotly.offline.plot(fig, include_plotlyjs=False, output_type="div")
        print (str(datetime.datetime.now() - start_time)+' chart generated')#timing
        
        return render_template('Lordaeron_Horde.html', title='Lordaeron Horde', chart=chart)
    
    return render_template('Lordaeron_Horde.html', title='Lordaeron Horde')


