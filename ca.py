from flask_wtf import Form
from wtforms import StringField, IntegerField, SubmitField, validators, ValidationError

from subprocess import check_output, STDOUT
import os, zipfile, io, random, string


class CreationForm(Form):
    common_name = StringField('Common Name', validators=[validators.InputRequired(), validators.Regexp('^[A-Za-z0-9_-]+$', message='Only letters, numbers, - or _')], default='Max_Mustermann_2015')
    email = StringField('Email', validators=[validators.Email()], default='max@mustermann.de')
    organization = StringField('Organization', validators=[validators.InputRequired()], default='Nonesense GmbH')
    organizational_unit = StringField('Organizational Unit', validators=[validators.Optional()], default='R&D')
    locality = StringField('Locality', validators=[validators.InputRequired()], default='Buxtehude')
    state = StringField('State', validators=[validators.InputRequired()], default='Niedersachsen')
    country = StringField('Country', validators=[validators.InputRequired()], default='DE')
    days_valid = IntegerField('Valid for x days', validators=[validators.InputRequired(), validators.NumberRange(min=1)], default='365')
    password = StringField('Password', validators=[validators.InputRequired()])
    create_certificate = SubmitField('Create certificate')

    def __init__(self, **kwargs):
        super(CreationForm, self).__init__(**kwargs)
        self.password.data = random_password(8)

    def validate_common_name(form, field):
        if certificate_exists(field.data):
            raise ValidationError('A certificate with this CN already exists. Please choose a different one')


def create(form):
    cn = form.common_name.data
    ou = '/OU=' + form.organizational_unit.data if form.organizational_unit.data != '' else ''

    subject = '/C={}/ST={}/L={}/O={}{}/CN={}/emailAddress={}'.format(form.country.data, form.state.data, form.locality.data, form.organization.data, ou, cn, form.email.data)

    ca_dir = get_ca_dir()

    key_filepath = '{}/keys/{}.key'.format(ca_dir, cn)
    csr_filepath = '{}/keys/{}.csr'.format(ca_dir, cn)
    crt_filepath = '{}/keys/{}.crt'.format(ca_dir, cn)
    p12_filepath = '{}/keys/{}.p12'.format(ca_dir, cn)
    pwd_filepath = '{}/keys/{}.pass'.format(ca_dir, cn)
    ca_filepath = '{}/db/ca.crt'.format(ca_dir)

    with open(pwd_filepath, 'w') as passfile:
        passfile.write(form.password.data)

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
        '-days', str(form.days_valid.data),
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
        '-passin', 'pass:' + form.password.data,
        '-passout', 'pass:' + form.password.data,
    ], cwd=ca_dir, stderr=STDOUT)

    return cn


def load(cn):
    ca_dir = get_ca_dir()
    
    with open('{}/keys/{}.crt'.format(ca_dir, cn)) as certfile:
        content = certfile.read()

    with open('{}/keys/{}.pass'.format(ca_dir, cn)) as passfile:
        # read first line and strip off the trailing newline
        password = passfile.readline().strip()

    return content, password


def load_as_zip(cn):
    """
    returns an in memory zip file containing the .crt, .key and .p12 files of the given CN
    """
    directory = get_ca_dir() + '/keys'

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for ext in ['.crt', '.key', '.p12']:
            filename = cn + ext
            zf.write(directory + '/' + filename, arcname=filename)

    memory_file.seek(0)
    return memory_file


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


def random_password(length):
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))
