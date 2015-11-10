import os
import shutil
import re

def setup(dir):
    if not os.path.exists('settings.py'):
        secret_key = os.urandom(24)
        copy_and_replace('settings.example.py', 'settings.py', r'^SECRET_KEY\s*=', 'SECRET_KEY = ' + repr(secret_key))

    if not os.path.exists(dir + '/openssl.cnf'):
        shutil.copy('ca/openssl.example.cnf', dir + '/openssl.cnf')

    mkdirs(dir + '/keys')
    mkdirs(dir + '/db')

    if not os.path.exists(dir + '/db/serial'):
        with open(dir + '/db/serial', 'w') as index_file:
            index_file.write('01')

    if not os.path.exists(dir + '/db/index.txt'):
        open(dir + '/db/index.txt', 'w').close()


def mkdirs(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def copy_and_replace(src_path, dst_path, regex, replacement):
    with open(dst_path, 'w') as dst:
        with open(src_path) as src:
            for line in src:
                if re.match(regex, line) is not None:
                    dst.write(replacement + "\n")
                else:
                    dst.write(line)


if __name__ == '__main__':
    setup('ca')
