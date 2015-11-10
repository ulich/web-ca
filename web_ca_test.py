import os
import web_ca
import unittest
import tempfile
import shutil
import tempfile

class WebCATestCase(unittest.TestCase):

    def setUp(self):
        web_ca.app.config['TESTING'] = True
        web_ca.app.config['WTF_CSRF_ENABLED'] = False

        self.workdir = tempfile.mkdtemp()
        web_ca.app.config['WEB_CA_WORK_DIR'] = self.workdir

        shutil.copy('ca/ca.crt', self.workdir)
        shutil.copy('ca/ca.key', self.workdir)
        shutil.copy('ca/openssl.cnf', self.workdir)
        os.makedirs(self.workdir + '/db')
        os.makedirs(self.workdir + '/keys')

        with open(self.workdir + '/db/index.txt', 'wb') as index_file:
            index_file.write("")
        with open(self.workdir + '/db/serial', 'wb') as serial_file:
            serial_file.write("01")

        self.app = web_ca.app.test_client()


    def tearDown(self):
        shutil.rmtree(self.workdir)


    def test_index(self):
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('id="page-create-certificate"', rv.data)


    def test_show_create_certificate_form(self):
        rv = self.app.get('/certificate')
        self.assertIn('id="page-create-certificate"', rv.data)


    def test_create_certificate(self):
        rv = self.app.post('/certificate', follow_redirects=True, data=dict(
            common_name='foo_bar',
            email='foo@bar.com',
            organization='Foo Bar AG',
            organizational_unit='R&D',
            locality='Berlin',
            country='DE',
            days_valid='31',
            password='foosecret123'
        ))
        self.assertIn('id="page-certificate"', rv.data)
        self.assertIn(' Subject: C=DE, L=Berlin, O=Foo Bar AG, OU=R&amp;D, CN=foo_bar/emailAddress=foo@bar.com\n', rv.data)


if __name__ == '__main__':
    unittest.main()
