#!/usr/bin/env python3

import sys
import getopt
import hashlib
import tarfile
import glob
import os
import shutil

from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)

def _password_to_key(password):
    password = password.encode()
    for _ in range(100):
        password = hashlib.sha256(password).digest()
    return password[:16]

def _generate_iv(key, salt):
    temp_iv = key + salt
    for _ in range(100):
        temp_iv = hashlib.sha256(temp_iv).digest()
    return temp_iv[:16]

class SecureTarFile:
    def __init__(self, filename, password):
        self._file = None
        self._name = Path(filename)

        self._tar = None
        self._tar_mode = "r|gz"

        self._aes = None
        self._key = _password_to_key(password)

        self._decrypt = None

    def __enter__(self):
        self._file = self._name.open("rb")

        cbc_rand = self._file.read(16)

        self._aes = Cipher(
            algorithms.AES(self._key),
            modes.CBC(_generate_iv(self._key, cbc_rand)),
            backend=default_backend(),
        )

        self._decrypt = self._aes.decryptor()

        self._tar = tarfile.open(fileobj=self, mode=self._tar_mode)
        return self._tar

    def __exit__(self, exc_type, exc_value, traceback):
        if self._tar:
            self._tar.close()
        if self._file:
            self._file.close()

    def read(self, size = 0):
        return self._decrypt.update(self._file.read(size))

    @property
    def path(self):
        return self._name

    @property
    def size(self):
        if not self._name.is_file():
            return 0
        return round(self._name.stat().st_size / 1_048_576, 2)  # calc mbyte

def _extract_tar(filename):
    _dirname = '.'.join(filename.split('.')[:-1])

    try:
        shutil.rmtree('_dirname')
    except FileNotFoundError:
        pass

    print(f'Extracting {filename}...')
    _tar  = tarfile.open(name=filename, mode="r")
    _tar.extractall(path=_dirname)

    return _dirname

def _extract_secure_tar(filename, password):
    _dirname = '.'.join(filename.split('.')[:-2])
    print(f'Extracting secure tar {filename.split("/")[-1]}...')
    try:
        with SecureTarFile(filename, password) as _tar:
            _tar.extractall(path=_dirname)
    except tarfile.ReadError:
        print("Unable to extract SecureTar - maybe your password is wrong or the tar is not password encrypted?")
        sys.exit(5)

    return _dirname

def print_usage():
    print(f'{sys.argv[0]} -i <inputfile> -p <password>')

def main():
    _inputfile = None
    _password=None

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hi:p:")
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit()
        elif opt in ("-i"):
            _inputfile = arg
        elif opt in ("-p"):
            _password = arg

    if not _inputfile:
        print ("Missing inputfile")
        print_usage()
        sys.exit(3)

    if not _password:
        print ("Missing password")
        print_usage()
        sys.exit(4)

    _dirname = _extract_tar(_inputfile)
    for _secure_tar in glob.glob(f'{_dirname}/*.tar.gz'):
        _extract_secure_tar(_secure_tar, _password)
        os.remove(_secure_tar)

    print("Done")

if __name__ == "__main__":
    main()
