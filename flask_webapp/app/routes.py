from flask import render_template, flash, redirect
from app import app
from app.forms import LoginForm
import pygal

with open("D:/Yano/Drive/Other/python/auctionator_history/auction_history.txt","r") as auction_history_file: # Load dict of auction history
    auction_history = {}
    try:
        auction_history = eval(auction_history_file.read())
    except SyntaxError:
        pass

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
                date_list = []
                for data_point in auction_history[item]:
                    price_list.append(int(data_point[1]))
                    date_list.append(int(data_point[0]))
                chart = pygal.Line()
                chart.title = "{}'s price history".format(item)
                chart.x_labels = date_list
                chart.add(item, price_list)
                chart = chart.render_data_uri()
                return render_template('Lordaeron_AH_history.html', title='Search AH history', form=form, chart=chart)
    return render_template('Lordaeron_AH_history.html', title='Search AH history', form=form)