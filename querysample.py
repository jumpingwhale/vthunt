#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
querysample.py
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
import json
import pprint
import sqlite3


class QuerySample:

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(config['log']['logname'])
        self.trigger = False
        self.conn = None
        self.cur = None
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

    qs = QuerySample(config)

    con = sqlite3.connect('statistics.db')
    cur = con.cursor()

    hashes = []

    nomd5 = 0
    noreport = 0
    for hash in hashes:
        sql = 'SELECT report FROM virustotal WHERE md5=%s'
        vals = (hash, )
        qs.cur.execute(sql, vals)
        row = qs.cur.fetchone()
        if not row:
            print('%s no md5' % hash)
            nomd5 += 1
            continue

        if not row[0]:
            print('%s no report' % hash)
            noreport +=1
            continue

    print('total %d' % len(hashes))
    print('nomd5 %d' % nomd5)
    print('noreport %d' % noreport)
        #
        # report = json.loads(row[0])
        # p = report['positives']
        #
        # sql = 'UPDATE statistics SET positives=? WHERE md5=?'
        # vals = (p, hash)
        # cur.execute(sql, vals)
        # con.commit()
