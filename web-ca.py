from flask import Flask, render_template, send_file, request, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import StringField, SubmitField, validators, ValidationError
from subprocess import check_output, STDOUT
import os, zipfile, io

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.secret_key = "\xd0\x03A\xea\x94\xd4\x17_`\x1b\x14+|\xe6\xb1bB$\x88\xb3\x06\xc6b\x11"  # TODO: keep this secret
Bootstrap(app)


class CertificateCreationForm(Form):
    common_name = StringField('Common Name', validators=[validators.InputRequired(), validators.Regexp('^[A-Za-z0-9_-]+$', message='Only letters, numbers, - or _')], default='Max_Mustermann_2015')
    email = StringField('Email', validators=[validators.Email()], default='max@mustermann.de')
    organization = StringField('Organization', validators=[validators.InputRequired()], default='Nonesense GmbH')
    organizational_unit = StringField('Organizational Unit', validators=[validators.Optional()], default='R&D')
    locality = StringField('Locality', validators=[validators.InputRequired()], default='Buxtehude')
    state = StringField('State', validators=[validators.InputRequired()], default='Niedersachsen')
    country = StringField('Country', validators=[validators.InputRequired()], default='DE')
    days_valid = StringField('Valid for x days', validators=[validators.InputRequired(), validators.NumberRange(min=1)], default='365')
    password = StringField('Password', validators=[validators.InputRequired()], default='secret123')
    create_certificate = SubmitField('Create certificate')

    def validate_common_name(form, field):
        if certificate_exists(field.data):
            raise ValidationError('A certificate with this CN already exists. Please choose a different one')


@app.route("/")
def index():
    return redirect(url_for('create_certificate'))


@app.route("/certificate", methods=['GET', 'POST'])
def create_certificate():
    form = CertificateCreationForm()
    if form.validate_on_submit():
        cn = form.common_name.data
        ou = '/OU=' + form.organizational_unit.data if form.organizational_unit.data != '' else ''

        subject = '/C={}/ST={}/L={}/O={}{}/CN={}/emailAddress={}'.format(form.country.data, form.state.data, form.locality.data, form.organization.data, ou, cn, form.email.data)

        generate_certificate_files(subject, cn, form.days_valid.data, form.password.data)

        return redirect(url_for('display_certificate', cn=cn))
    else:
        return render_template('index.html', form=form)


def generate_certificate_files(subject, cn, days_valid, password):
    ca_dir = get_ca_dir()

    key_filepath = '{}/keys/{}.key'.format(ca_dir, cn)
    csr_filepath = '{}/keys/{}.csr'.format(ca_dir, cn)
    crt_filepath = '{}/keys/{}.crt'.format(ca_dir, cn)
    p12_filepath = '{}/keys/{}.p12'.format(ca_dir, cn)
    pwd_filepath = '{}/keys/{}.pass'.format(ca_dir, cn)
    ca_filepath = '{}/db/ca.crt'.format(ca_dir)

    with open(pwd_filepath, 'w') as passfile:
        passfile.write(password)

    check_output([
        'openssl', 'req',
        '-config', 'openssl.cnf',
        '-new',
        '-extensions', 'server',
        '-subj', subject,
        '-passout', 'file:' + pwd_filepath,
        '-keyout', key_filepath,
        '-out', csr_filepath,
    ], cwd=ca_dir, stderr=STDOUT)

    check_output([
        'openssl', 'ca',
        '-config', 'openssl.cnf',
        '-batch',
        '-days', days_valid,
        '-out', crt_filepath,
        '-infiles', csr_filepath,
    ], cwd=ca_dir, stderr=STDOUT)

    check_output([
        'openssl', 'pkcs12',
        '-export',
        '-inkey', key_filepath,
        '-CAfile', ca_filepath,
        '-certfile', ca_filepath,
        '-in', crt_filepath,
        '-out', p12_filepath,
        '-passin', 'pass:' + password,
        '-passout', 'pass:' + password,
    ], cwd=ca_dir, stderr=STDOUT)


@app.route("/certificate/<cn>")
def display_certificate(cn):
    ca_dir = get_ca_dir()
    
    with open('{}/keys/{}.crt'.format(ca_dir, cn)) as certfile:
        cert = certfile.read()

    with open('{}/keys/{}.pass'.format(ca_dir, cn)) as passfile:
        # read first line and strip off the trailing newline
        password = passfile.readline().strip()

    return render_template('certificate.html', cn=cn, certificate=cert, password=password)


@app.route("/certificate/<cn>/download")
def download_certificate(cn):
    """
    creates an in memory zip file containing the .crt, .key and .p12 files of the given CN and send it to the browser
    """
    directory = get_ca_dir() + '/keys'

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for ext in ['.crt', '.key', '.p12']:
            filename = cn + ext
            zf.write(directory + '/' + filename, arcname=filename)

    memory_file.seek(0)
    return send_file(memory_file, attachment_filename=cn + '.zip', as_attachment=True)


def get_ca_dir():
    """
    returns the absolute path to the ca dir, which is located next to this script
    """
    return os.path.dirname(os.path.abspath(__file__)) + '/ca'


def certificate_exists(cn):
    ca_dir = get_ca_dir()
    for ext in ['pass', 'crt', 'csr', 'key']:
        path = '{}/keys/{}.{}'.format(ca_dir, cn, ext)
        if os.path.isfile(path):
            return True
    return False


if __name__ == '__main__':
    app.run(debug = True)
