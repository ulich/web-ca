from flask import Flask, render_template, send_file, request, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import StringField, IntegerField, SubmitField, validators, ValidationError

from ca import CA

app = Flask(__name__)
app.config['WEB_CA_WORK_DIR'] = 'ca'
app.config.from_object('settings')
Bootstrap(app)

ca = CA(app.config)

@app.route("/")
def index():
    return redirect(url_for('create_certificate'))


class CreationForm(Form):
    _valid_chars_cn = validators.Regexp('^[A-Za-z0-9_\-\.]+$', message='Letters, numbers and one of the following characters are allowed: _-.')
    _valid_chars = validators.Regexp('^[A-Za-z0-9_\-\.& ]+$', message='Letters, numbers, whitespaces and one of the following characters are allowed: _-.&')

    common_name = StringField('Common Name*', validators=[validators.InputRequired(), _valid_chars_cn], default='Max_Mustermann_2015')
    email = StringField('Email', validators=[validators.Optional(), validators.Email()], default='max@mustermann.de')
    organization = StringField('Organization', validators=[validators.Optional(), _valid_chars], default='Nonesense GmbH')
    organizational_unit = StringField('Organizational Unit', validators=[validators.Optional(), _valid_chars], default='R&D')
    locality = StringField('Locality', validators=[validators.Optional(), _valid_chars], default='Buxtehude')
    state = StringField('State', validators=[validators.Optional(), _valid_chars], default='Niedersachsen')
    country = StringField('Country', validators=[validators.Optional(), _valid_chars], default='DE')
    days_valid = IntegerField('Valid for x days*', validators=[validators.InputRequired(), validators.NumberRange(min=1)], default='365')
    password = StringField('Password*', validators=[validators.InputRequired()])
    create_certificate = SubmitField('Create certificate')

    def __init__(self, **kwargs):
        super(CreationForm, self).__init__(**kwargs)
        self.password.data = ca.random_password(8)

    def validate_common_name(form, field):
        if ca.certificate_exists(field.data):
            raise ValidationError('A certificate with this CN already exists. Please choose a different one')


@app.route("/certificate", methods=['GET', 'POST'])
def create_certificate():
    form = CreationForm()
    if form.validate_on_submit():
        cn = ca.create(form)
        return redirect(url_for('display_certificate', cn=cn))
    else:
        return render_template('index.html', form=form)


@app.route("/certificate/<cn>")
def display_certificate(cn):
    content, password = ca.load(cn)
    return render_template('certificate.html', cn=cn, certificate=content, password=password)


@app.route("/certificate/<cn>/download")
def download_certificate(cn):
    memory_file = ca.load_as_zip(cn)
    return send_file(memory_file, attachment_filename=cn + '.zip', as_attachment=True)


if __name__ == '__main__':
    app.run()
