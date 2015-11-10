from subprocess import check_output, STDOUT, CalledProcessError
import os, zipfile, io, random, string

class CA:
    def __init__(self, config):
        self.appconfig = config


    def create(self, form):
        cn = form.common_name.data
        ou = '/OU=' + form.organizational_unit.data if form.organizational_unit.data != '' else ''

        subject = '/C={}/ST={}/L={}/O={}{}/CN={}/emailAddress={}'.format(form.country.data, form.state.data, form.locality.data, form.organization.data, ou, cn, form.email.data)

        ca_dir = self.get_ca_dir()

        key_filepath = '{}/keys/{}.key'.format(ca_dir, cn)
        csr_filepath = '{}/keys/{}.csr'.format(ca_dir, cn)
        crt_filepath = '{}/keys/{}.crt'.format(ca_dir, cn)
        p12_filepath = '{}/keys/{}.p12'.format(ca_dir, cn)
        pwd_filepath = '{}/keys/{}.pass'.format(ca_dir, cn)
        ca_filepath = '{}/ca.crt'.format(ca_dir)

        with open(pwd_filepath, 'w') as passfile:
            passfile.write(form.password.data)

        self._exec([
            'openssl', 'req',
            '-config', 'openssl.cnf',
            '-new',
            '-extensions', 'server',
            '-subj', subject,
            '-passout', 'file:' + pwd_filepath,
            '-keyout', key_filepath,
            '-out', csr_filepath,
        ])

        self._exec([
            'openssl', 'ca',
            '-config', 'openssl.cnf',
            '-batch',
            '-days', str(form.days_valid.data),
            '-out', crt_filepath,
            '-infiles', csr_filepath,
        ])

        self._exec([
            'openssl', 'pkcs12',
            '-export',
            '-inkey', key_filepath,
            '-CAfile', ca_filepath,
            '-certfile', ca_filepath,
            '-in', crt_filepath,
            '-out', p12_filepath,
            '-passin', 'pass:' + form.password.data,
            '-passout', 'pass:' + form.password.data,
        ])

        return cn


    def load(self, cn):
        ca_dir = self.get_ca_dir()
        
        with open('{}/keys/{}.crt'.format(ca_dir, cn)) as certfile:
            content = certfile.read()

        with open('{}/keys/{}.pass'.format(ca_dir, cn)) as passfile:
            # read first line and strip off the trailing newline
            password = passfile.readline().strip()

        return content, password


    def load_as_zip(self, cn):
        """
        returns an in memory zip file containing the .crt, .key and .p12 files of the given CN
        """
        directory = self.get_ca_dir() + '/keys'

        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for ext in ['.crt', '.key', '.p12']:
                filename = cn + ext
                zf.write(directory + '/' + filename, arcname=filename)

        memory_file.seek(0)
        return memory_file


    def get_ca_dir(self):
        """
        returns the absolute path to the ca dir, which is either self.workdir if it is already absolute,
        or relative located next to this script
        """
        workdir = self.appconfig['WEB_CA_WORK_DIR']
        if os.path.isabs(workdir):
            return workdir
        else:
            return os.path.dirname(os.path.abspath(__file__)) + '/' + workdir


    def certificate_exists(self, cn):
        ca_dir = self.get_ca_dir()
        for ext in ['pass', 'crt', 'csr', 'key']:
            path = '{}/keys/{}.{}'.format(ca_dir, cn, ext)
            if os.path.isfile(path):
                return True
        return False


    def random_password(self, length):
        return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))


    def _exec(self, cmd):
        try:
            check_output(cmd, cwd=self.get_ca_dir(), stderr=STDOUT)
        except CalledProcessError, e:
            raise Exception('Error executing command. Output was: ' + e.output)