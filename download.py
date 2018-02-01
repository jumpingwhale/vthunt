#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
download.py
_________
"""

import os
import io
import errno
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler
import requests
import pymysql
import paramiko
import yaml
import hashlib
import re

GET_PATH = 'SELECT md5, path FROM depot WHERE md5=%s'


class Downloader:

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(config['log']['logname'])
        self.trigger = False
        self.conn = None
        self.cur = None
        self.sftp = None
        try:
            self.conn = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                database=config['mysql']['database'],
                user=config['mysql']['user'],
                passwd=config['mysql']['passwd'],
            )
            self.cur = self.conn.cursor()
        except Exception:
            self.logger.critical('MySql connection error')
            raise

        try:
            self.sftp = self.__conn_sftp(config['sftp'])
        except Exception:
            self.logger.critical('SFTP connection error')
            raise

    def __conn_sftp(self, config):
        host = config['host']
        port = config['port']
        user = config['user']
        passwd = config['passwd']

        sock = (host, port)

        t = paramiko.Transport(sock)

        # Transport 로 서버 접속
        t.connect(username=user, password=passwd)

        # 클라이언트 초기화
        sftp = paramiko.SFTPClient.from_transport(t)

        return sftp

    def __ishash(self, hashstr):
        pattern = r'^[a-fA-F0-9]{32}$'  # MD5

        match = re.match(pattern, hashstr)
        if match is not None:
            return True
        return False

    def download(self, md5):
        if not self.__ishash(md5):
            return False

        # 서버에 샘플 있는지 확인
        vals = (md5, )
        self.cur.execute(GET_PATH, vals)
        if self.cur.rowcount:
            row = self.cur.fetchone()
            rmd5 = row[0]
            rpath = row[1]

            # 다운로드
            self.sftp.get(rpath, os.path.join('samples', rmd5))


def setup_log(config):
    logger = logging.getLogger(config['logname'])
    logger.setLevel(config['loglevel'])

    format = logging.Formatter(config['format'])
    for h in logger.handlers:
        h.setFormatter(format)

    return logger


if __name__ == '__main__':
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception:
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    setup_log(config['log'])

    dl = Downloader(config)

    # 폴더생성
    try:
        os.mkdir('samples')
    except FileExistsError:
        pass

    hashes = []

    for h in hashes:
        dl.download(h)
