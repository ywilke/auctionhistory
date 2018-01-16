from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    item_search = StringField('Item', validators=[DataRequired()])
    submit = SubmitField('Search')
