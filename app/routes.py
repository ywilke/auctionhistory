import datetime
import json
import math
import sqlite3 as sqlite
import pickle
from hashlib import md5
import os

from flask import render_template, request, abort
from flask_recaptcha import ReCaptcha
import redis
import plotly.offline as plotly
import plotly.graph_objs as plotgo
import pandas as pd
import numpy as np

from app import app

def o_pad(i):
    x = str(i)
    if len(x) == 1:
        x = f'0{x}'
    return x


def copper_to_price(copper, as_dic=False):
    '''Return the price in WoW currency.'''
    try:
        copper = int(copper)
    except ValueError:
        if as_dic == True:
            return dict([('g', 0), ('s', 0), ('c', 0), ('na', 1)])
        else:
            return 'NA'
    s, c = divmod(copper, 100)
    g, s = divmod(s, 100)
    if as_dic == True:
        p_dic = dict([('g', g), ('s', s), ('c', o_pad(c)), ('na', 0)])
        if g != 0:
            p_dic['g'] = o_pad(g)
        if g != 0 or s != 0:
            p_dic['s'] = o_pad(s)
        return p_dic
        
    if g == 0:
        if s == 0:
            return f'{c}c'
        else:
            return f'{s}s{c}c'
    else:
        return f'{g}g{s}s{c}c'


def create_card_stats(item, df, epoch_now):
    '''Return stats about the price history'''
    card_stats = {}
    card_stats['item'] = item
    d7 = pd.Timestamp(epoch_now - 60*60*24*7, unit='s')
    card_stats['7davg'] = copper_to_price(df[d7:].mean()[0], as_dic=True)
    d30 = pd.Timestamp(epoch_now - 60*60*24*30, unit='s')
    card_stats['30davg'] = copper_to_price(df[d30:].mean()[0], as_dic=True)
    d14 = pd.Timestamp(epoch_now - 60*60*24*14, unit='s')
    card_stats['14dmin'] = copper_to_price(df[d14:].min()[0], as_dic=True)
    card_stats['last_p'] = copper_to_price(df["prices"][-1], as_dic=True)
    last_seen = df.index[-1].strftime('%d %b %Y')
    if last_seen[0] == '0':
        last_seen = last_seen.replace('0', '', 1)
    card_stats['last_seen'] = last_seen
    return card_stats


def get_date(unix_time):
    '''Return date in dd-mm-yyyy.'''
    return datetime.datetime.fromtimestamp(unix_time).strftime('%d-%m-%y')


def get_ip():
    '''Return ip of user'''
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    return ip


def write_log(server="NA", realm="NA", faction="NA", search="NA", resp="NA",
              time="NA", r_time="NA", info=""):
    '''Logs user searches'''
    date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('log.tsv', 'a') as log:
        log.write(f'{date}\t{get_ip()}\t{server}\t{realm}\t{faction}\t{search}\t{time}\t{resp}\t{r_time}\t{info}\n')


# Setup vars
R = redis.Redis(host="127.0.0.1", port=6379)

con = sqlite.connect('file:import/auctionhistory.db?mode=ro', uri=True) #db path
cur = con.cursor()

SERVER_LIST = pickle.load(open('SERVER_LIST.p', 'rb'))
REALMS = pickle.load(open('REALMS.p', 'rb'))
CAP = pickle.load(open('CAP.p', 'rb'))

html_page = 'search.html'
time_dir = {'30d': 2592000,
            '3m': 7890000,
            '1y': 31536000,
}

# Create servers json for API
servers_json = {"servers": list()}
cur_servers = dict()
cur_i = 0
for server_obj in SERVER_LIST:
    snameSite = server_obj["server"]
    expan = server_obj["expansion"]
    try:
        snameNice = CAP[snameSite]
    except:
        snameNice = snameSite
        
    # Format realm data
    realm_list = list()
    for realm_obj in server_obj["realms"]:
        rnameGame = realm_obj["realm"]
        rnameSite = realm_obj["name"]
        rnameNice = rnameSite.replace('_', ' ')
            
        rtemp_obj = {"nameNice": rnameNice,
                     "nameSite": rnameSite,
                     "nameGame": rnameGame,
                     "expansion": expan}
        
        realm_list.append(rtemp_obj)
    
    # Append realm data
    try:
        server_i = cur_servers[snameSite]
        servers_json["servers"][server_i]["realms"] = servers_json["servers"][server_i]["realms"] + realm_list
        
    except KeyError:
        cur_servers[snameSite] = cur_i
        cur_i += 1
        
        stemp_obj = {"nameSite": snameSite,
                    "nameNice": snameNice,
                    "realms": realm_list}
        
        servers_json["servers"].append(stemp_obj)
servers_json = json.dumps(servers_json)

# Setup recaptcha
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", default=None)
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", default=None)

recaptcha = ReCaptcha(app=app, site_key=RECAPTCHA_SITE_KEY,
                      secret_key=RECAPTCHA_SECRET_KEY, theme="dark")

# Routing
@app.route('/')
@app.route('/index')
def index():
    write_log(resp="home")
    return render_template('index.html', title='Legacy Servers')


@app.route('/contact')
def contact():
    write_log(resp="contact")
    return render_template('contact.html', title='Contact')


@app.route('/api/servers')
def api_servers():
    response = app.response_class(
        response=servers_json,
        status = 200,
        mimetype='application/json'
    )
    return response


@app.route('/<server_arg>/<realm_arg>', methods=['GET'])
def search(server_arg, realm_arg):
    # Ratelimit check
    ip = get_ip()
    try:
        verify = int(R.get(f"ver:{ip}").decode())
    except AttributeError:
        verify = 0
    
    n_items = R.scard(f"item:{ip}")
    
    first_check = 25
    second_check = 60
    if n_items == first_check or n_items >= second_check:
        bot_check = True
        if not (n_items < second_check and verify == 2): # dont set for verify if already passed first check and below second check
            R.set(f"ver:{ip}", 1)
    elif n_items >= 120: # Passed the max number of items for the day
        abort(429, "items")
    elif n_items < first_check:
        bot_check = False
        if verify == 1: # If they are below the limits remove their verify status
            R.delete(f"ver:{ip}")
            verify = 0
    else:
        bot_check = False
        
    # Validate url and set expansion
    try:
        expan = REALMS[server_arg][realm_arg]
    except KeyError:
        if server_arg not in REALMS: # Invalid server_arg
            abort(404)
        elif f"{realm_arg}_Alliance" in REALMS[server_arg] or f"{realm_arg}_Horde" in REALMS[server_arg]:
            # Return faction select page
            write_log(server=server_arg, realm=realm_arg, resp="realms")
            return render_template('realms.html',server=server_arg,
                realm=realm_arg, title=f"{CAP[server_arg]}: {realm_arg.replace('_', ' ')}")
        else: # Invalid url
            abort(404)
    
    # Setup request vars
    start_time = datetime.datetime.now()
    search_arg = request.args.get('search', '')
    time_arg = request.args.get('time', None)
    AH_title = f"{realm_arg.replace('_', ' ')} Auction House"
    tab = f"{CAP[server_arg]}: {realm_arg.replace('_', ' ')}"

    epoch_now = int(datetime.datetime.now().timestamp())
    try: 
        scantime = epoch_now - time_dir[time_arg]
    except KeyError:
        if time_arg == "all":
            scantime = 0
        else:
            scantime = None
            
    # Check captcha response
    capt_resp = request.args.get('g-recaptcha-response', None)
    if capt_resp != None:
        capt_pass = recaptcha.verify(capt_resp, ip)
        if capt_pass == True and n_items < second_check:
            R.set(f"ver:{ip}", 2, ex=14400)
        elif capt_pass == True and n_items >= second_check:
            R.delete(f"ver:{ip}")
    else:
        capt_pass = False

    # Check if captcha needs to be rendered
    if bot_check == False or (n_items < second_check and verify == 2) or (n_items < second_check and capt_pass == True):
        captcha = None
    else:
        captcha = recaptcha
    
    # Return blank search page if no search
    if search_arg == None or scantime == None:        
        return render_template(html_page, title=tab, AH_title=AH_title,
                               tvalue='all', capt=captcha) 
        
    # Validate search argument
    if len(search_arg) > 80 or "\t" in search_arg:
        return render_template(html_page, title='Invalid search',
                           AH_title=AH_title, capt=captcha,
                           error='Invalid search. Too long or contains tabs',
                           value=search_arg, tvalue=time_arg)
    
    # Validate if captcha was passed if required
    if verify == 1 and capt_pass == False:
        msg = "Please complete the ReCaptcha"
        return render_template(html_page, title=tab, AH_title=AH_title, value=search_arg,
                        tvalue=time_arg, error=msg, capt=recaptcha)
    
    # Check if item is known
    log_r, log_f = realm_arg.rsplit("_", 1)
    temp_sql = f"SELECT itemid FROM {expan}_items WHERE itemname IS ? ;"
    cur.execute(temp_sql, (search_arg,))
    
    if not cur.fetchone():  # No direct match
        # Search needs to be at least 3 characters
        if len(search_arg) < 3:
            return render_template(html_page, title='Item not found',
                                   AH_title=AH_title, capt=captcha,
                                   error='Type at least 3 characters',
                                   value=search_arg, tvalue=time_arg)
        # Check for item names that contain the search string
        temp_sql = f"SELECT itemname FROM {expan}_items WHERE itemname LIKE ?;"
        cur.execute(temp_sql, (f'%{search_arg}%',))
        item_matches = sorted(cur.fetchall(), key=lambda x: len(x[0]))
        if item_matches:
            item_suggestions = []
            for match in item_matches:
                href_display = match[0]
                href_item = match[0].replace(' ', '+')
                href = f'/{server_arg}/{realm_arg}?search={href_item}&time={time_arg}'
                item_suggestions.append((href_display, href))
            r_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
            write_log(server=server_arg, realm=log_r, faction=log_f,
                      search=search_arg, resp='suggest', r_time=r_time)
            return render_template(html_page, title=tab,
                                   AH_title=AH_title, capt=captcha,
                                   suggestions=item_suggestions,
                                   value=search_arg, tvalue=time_arg)
        else:
            return render_template(html_page, title='Item not found',
                                   AH_title=AH_title, capt=captcha,
                                   error='Item was not found in the database',
                                   value=search_arg, tvalue=time_arg)
    
    # Get prices for item in database
    short = f"{realm_arg.rsplit('_', 1)[0]}_{realm_arg.rsplit('_', 1)[1][0]}"
    temp_sql = (f"""SELECT itemname, price, scantime FROM {short}_prices
        INNER JOIN {expan}_items ON {short}_prices.itemid={expan}_items.itemid 
        INNER JOIN scans ON {short}_prices.scanid=scans.scanid 
        WHERE {expan}_items.itemname IS ? 
        AND scans.scantime > ?;""")
    cur.execute(temp_sql, (search_arg, scantime))
    datapoints = sorted(cur.fetchall(), key=lambda x: x[2])
    if not datapoints:
        msg = "This item has not been listed on the auction house in the selected time range."
        return render_template(html_page, title='No prices available',
                               AH_title=AH_title, error=msg, capt=captcha,
                               value=search_arg, tvalue=time_arg)
    
    # Remove outliers
    prices = []
    outliers = []
    for i in datapoints:
        prices.append(i[1])
    prices.sort()
    high_price = 1.5 * prices[int(0.95 * len(prices))]
    for i, point in enumerate(datapoints):
        price = point[1]
        if price > high_price:
            outliers.append(i)
    for index in sorted(outliers, reverse=True):
        del datapoints[index]
    
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
    card_stats = create_card_stats(item, df, epoch_now)
    dfr = df.rolling(window).mean()
    # Create traces
    
    trace_price = plotgo.Scattergl(
        x = index,
        y = price_list,
        text = list(map(copper_to_price, price_list)),
        hoverinfo = 'text+x',
        name = item,
        mode = 'markers',)
    
    trace_avg = plotgo.Scattergl(
        x = dfr.axes[0],
        y = dfr['prices'],
        text = list(map(copper_to_price, dfr['prices'])),
        hoverinfo = 'text+x',
        hoverlabel = dict(bordercolor = '#ffffff',
            font = dict(color = '#ffffff')),
        name = 'average ({window})'.format(window = window),
        mode = 'lines',)
    plotdata = [trace_price, trace_avg]
    # Layout    
    nr_ticks = 10
    y_vals = []
    p_range = max(price_list) - min(price_list)
    if p_range == 0:
        p_range = 2 * min(price_list)
    t_range = p_range / (nr_ticks - 1)
    x = math.ceil(np.log10(t_range))
    t1 = t_range / (10 ** x)
    if t1 == 0.1:
        pass
    elif t1 <= 0.25:
        t1 = 0.25
    elif t1 <= 0.50:
        t1 = 0.50
    elif t1 <= 1.0:
        t1 = 1.0
    tick_step = t1 * (10 ** x)
    tick_start = int(min(price_list) / tick_step)
    y_start = tick_start * tick_step
    for i in range(nr_ticks):
        y_start += tick_step
        y_vals.append(y_start)
    
    layout = plotgo.Layout(
        title = "{item}'s price history".format(item=item),
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
    r_time = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
    write_log(server=server_arg, realm=log_r, faction=log_f, search=search_arg,
              resp='graph', time=time_arg, r_time=r_time)
    
    # Log search for rate limiting
    hash_obj = md5(f"{realm_arg}{item}".encode())
    hash_id = hash_obj.hexdigest()[0:8]
    R.sadd(f"item:{ip}", hash_id)
    if R.ttl(f"item:{ip}") == -1:
        R.expire(f"item:{ip}", 86400)
    
    return render_template(html_page, title=tab, AH_title=AH_title, chart=chart,
                           value=search_arg, tvalue=time_arg, stats=card_stats,
                           capt=captcha)

@app.errorhandler(429)
def ratelimit_handler(e):
    rule = e.description
    write_log(resp='429', info=rule)
    return render_template('429.html', title='Too Many Requests', limit=rule), 429

@app.errorhandler(404)
def notfound_handler(e):
    return render_template('404.html', title='Page Not Found'), 404
