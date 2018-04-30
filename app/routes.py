from flask import render_template, request
from app import app
import plotly.offline as plotly
import plotly.graph_objs as plotgo
import pandas as pd
import datetime
import sqlite3 as sqlite
import numpy as np

con = sqlite.connect('import/auctionhistory.db') #db path
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
    return render_template('index.html', title='Warmane Auction House History')

@app.route('/server/<server_arg>', methods=['GET'])
def search(server_arg):
    search_arg = request.args.get('search', '')
    time_arg = request.args.get('time', None)
    title = '{} Auction House History'.format(server_arg.replace('_', ' '))
    html_page = 'search.html'
    time_dir = {'30d' : 2592000, '3m' : 7890000, '1y' : 31536000, 'all' : 0}
    try: 
        scantime = int(datetime.datetime.now().timestamp()) - time_dir[time_arg]
    except KeyError:
        scantime = None
    
    if search_arg and scantime:
        query = (search_arg, server_arg, scantime)
        # Execute query
        cur.execute("SELECT itemname, price, scantime FROM prices "
                    "INNER JOIN items ON prices.itemid=items.itemid "
                    "INNER JOIN scans ON prices.scanid=scans.scanid "
                    "INNER JOIN servers ON prices.serverid=servers.serverid "
                    "WHERE items.itemname IS ? "
                    "AND servers.servername IS ? "
                    "AND scans.scantime > ?;", query)
        datapoints = sorted(cur.fetchall(), key=lambda x: x[2])
        
        if not datapoints:
            if len(search_arg) < 3:
                return render_template(html_page, title='Item not found', error='Type at least 3 characters.')
            cur.execute("SELECT itemname FROM items WHERE itemname LIKE ?;",
                       ('{0}{search}{0}'.format('%', search=query[0]),))
            item_matches = sorted(cur.fetchall(), key=lambda x: len(x[0]))
            if item_matches:
                item_suggestions = []
                for match in item_matches:
                    href_display = match[0]
                    href_item = match[0].replace(' ', '+')
                    href = '/server/{server_arg}?search={item}&time={time}'.format(
                            server_arg=server_arg, item=href_item, time=time_arg )
                    item_suggestions.append((href_display, href))
                return render_template(html_page, title=title, suggestions=item_suggestions)
            
            else:
                return render_template(html_page, title='Item not found', error='Item was not found in the database.')
        
        # Format data from query
        item = datapoints[0][0]
        time_list = []
        price_list = []
        for i in datapoints:
            time_list.append(i[2])
            price_list.append(i[1])
        # Generate moving average
        window = '5D'
        index = pd.to_datetime(time_list, unit = 's')
        df = pd.DataFrame({'prices': price_list}, index)
        dfr = df.rolling('5D').mean()
        # Create traces
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

        # Layout
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

        fig = dict(data=plotdata, layout=layout)
        chart = plotly.offline.plot(fig, include_plotlyjs=False, output_type="div")
        return render_template(html_page, title=title, chart=chart)
    
    else:
        return render_template(html_page, title=title)


