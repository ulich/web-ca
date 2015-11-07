#!/bin/bash

if [ ! -f settings.py ]; then
    key=$(openssl rand -base64 32)
    sed "s/SECRET_KEY = /SECRET_KEY = '$key'/" settings.example.py > settings.py
fi

if [ ! -f ca/openssl.cnf ]; then
    cp ca/openssl.example.cnf ca/openssl.cnf
fi

if [ ! -f ca/db/serial ]; then
    echo "01" > ca/db/serial
fi

if [ ! -f ca/db/index.txt ]; then
    touch ca/db/index.txt
fi
