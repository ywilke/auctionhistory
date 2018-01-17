from flask import render_template, flash, redirect
from app import app
from app.forms import LoginForm
import pygal
import datetime

with open("D:/Yano/Drive/github/AH_history/import/auction_history.txt","r") as auction_history_file: # Load dict of auction history
    auction_history = {}
    try:
        auction_history = eval(auction_history_file.read())
    except SyntaxError:
        pass

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

@app.route('/Lordaeron_AH_history', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        for item in auction_history:
            if form.item_search.data.lower() == item.lower():
                price_list = []
                for datapoint in auction_history[item]:
                    price_list.append((int(datapoint[0]),int(datapoint[1])))
                chart = pygal.XY(x_label_rotation=35, value_formatter=lambda y: copper_to_price(y), x_value_formatter=lambda x: get_date(x))
                chart.title = "{}'s price history".format(item)
                chart.add(item, price_list)
                chart = chart.render_data_uri()
                return render_template('Lordaeron_AH_history.html', title='Search AH history', form=form, chart=chart)
    return render_template('Lordaeron_AH_history.html', title='Search AH history', form=form)

