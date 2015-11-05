from flask import Flask, render_template, send_file, request, redirect, url_for
from subprocess import check_output, STDOUT
import os, zipfile, io

app = Flask(__name__)


@app.route("/")
def index():
    return render_template('index.html')


@app.route("/certificate", methods=['POST'])
def create_certificate():
    form = request.form

    # TODO: validate input:
    # - only [A-Za-z0-9_-]

    cn = form['CN']
    ou = '/OU=' + form['OU'] if form['OU'] != '' else ''

    subject = '/C={}/ST={}/L={}/O={}{}/CN={}/emailAddress={}'.format(form['C'], form['ST'], form['L'], form['O'], ou, cn, form['email'])

    abort_if_certificate_already_exists(cn)
    generate_certificate_files(subject, cn, form['days_valid'], form['password'])

    return redirect(url_for('display_certificate', cn=cn))

    
def abort_if_certificate_already_exists(cn):
    ca_dir = get_ca_dir()
    for ext in ['pass', 'crt', 'csr', 'key']:
        path = '{}/keys/{}.{}'.format(ca_dir, cn, ext)
        if os.path.isfile(path):
            raise Exception('Certificate already exists, please choose a different CN')


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


if __name__ == '__main__':
    app.run(debug = True)
