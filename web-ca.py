from flask import Flask, render_template, send_file, request, redirect, url_for
from flask_bootstrap import Bootstrap

import ca

app = Flask(__name__)
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.secret_key = "\xd0\x03A\xea\x94\xd4\x17_`\x1b\x14+|\xe6\xb1bB$\x88\xb3\x06\xc6b\x11"  # TODO: keep this secret
Bootstrap(app)


@app.route("/")
def index():
    return redirect(url_for('create_certificate'))


@app.route("/certificate", methods=['GET', 'POST'])
def create_certificate():
    form = ca.CreationForm()
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
    app.run(debug = True)
