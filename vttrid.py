#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import json
import time
import tempfile
import pymysql
import logging
import paramiko
from subprocess import Popen, PIPE



SELECT_SAMPLE_WITHOUT_TRID = 'SELECT path FROM depot INNER JOIN virustotal on depot.md5=virustotal.md5 WHERE virustotal.trid IS NULL'
MAXIMUM_WORK_SET = 1000
TEMP_FILE_PREFIX = 'trid_'


class VtTrid:
    def __init__(self, config):
        self.config = config
        self.api = config['virustotal']['api']
        self.logger = logging.getLogger(__name__)
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

    def work(self):
        self.cur.execute(SELECT_SAMPLE_WITHOUT_TRID)
        rows = self.cur.fetchmany(MAXIMUM_WORK_SET)
        while rows:
            for r in rows:
                tname = tempfile.mktemp(prefix=TEMP_FILE_PREFIX)
                self.sftp.get(r[0], tname)
                process = Popen(["trid", tname], stdout=PIPE)
                (output, err) = process.communicate()
                exit_code = process.wait()
                print(output)
