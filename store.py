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
import glob
import hashlib
from pytz import timezone


# virustotal.hunt 엔 있고, depot 엔 저장되지 않은(depot.path == NULL) 샘플들만 다운로드 받는다
INSERT_NEW_SAMPLE = 'INSERT INTO depot (md5, path) VALUES (%s, %s)'


class Store:
    def __init__(self, config):
        self.config = config
        self.api = config['virustotal']['api']
        self.logger = logging.getLogger(config['log']['logname'])
        self.conn = None
        self.cur = None
        self.sftp = None
        self.monitor = config['store']['monitor_path']
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

    def work(self):
        def completed(file, size_before=0):
            time.sleep(3)
            size_now = os.path.getsize(file)
            if size_now == size_before:
                return True
            else:
                # maximum recursion depth is usually 300
                return completed(file, size_now)

        while True:
            files = glob.glob(os.path.join(self.monitor, '*'))
            if len(files):
                self.logger.info('%d files queued' % len(files))
                for f in files:
                    self.logger.info('processing %s' % os.path.basename(f))

                    # 다운로드 완료됐는지 검증
                    try:
                        completed(f)
                    except RecursionError:
                        self.logger.info('looks like still downloading %s' % os.path.basename(f))
                        # 이번 루프 다 끝나면 나중에 재시도
                        continue

                    # 파일크기 검증
                    if os.path.getsize(f) > 1024 * 1024 * 40:  # 40MB 이상 스킵
                        self.logger.info('file size is too big %d' % os.path.getsize(f))
                        os.remove(f)
                        continue

                    # 업로드
                    with open(f, 'rb') as fp:
                        buf = fp.read()

                        # 해쉬값 생성
                        m = hashlib.md5()
                        m.update(buf)
                        md5 = m.hexdigest()

                        # 업로드
                        remote = self.__store_sftp(md5, buf)

                        # db 인서트
                        sql = INSERT_NEW_SAMPLE
                        vals = (md5, remote)
                        self.cur.execute(sql, vals)
                        self.conn.commit()

                    # 완료파일 삭제
                    os.remove(f)
            else:
                time.sleep(15)

    def __store_sftp(self, md5, binary):
        def exists(path):
            try:
                self.sftp.stat(path)
            except IOError as e:
                if e.errno == errno.ENOENT:
                    return False
                else:
                    raise
            else:
                return True

        root = 'md5'
        prefixes = [md5[:2], md5[2:4]]
        remote_dir = '/'.join([root, ] + prefixes)
        remote_path = '/'.join([remote_dir, md5])

        # 폴더 없으면 생성
        if not exists(remote_dir):
            path_to_remote_dir = root
            for prefix in prefixes:
                path_to_remote_dir = '/'.join([path_to_remote_dir, prefix])
                try:
                    self.sftp.mkdir(path_to_remote_dir)  # MD5 해쉬값, 두 글자단위, 2 depth 로 폴더생성
                except Exception:
                    pass

        # 이미 파일 있으면 삭제
        if exists(remote_path):
            self.sftp.remove(remote_path)

        # 업로드
        fp = io.BytesIO(binary)
        self.sftp.putfo(fp, remote_path)
        return remote_path

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


def setup_log(config):
    logger = logging.getLogger(config['logname'])
    logger.setLevel(config['loglevel'])
    filehandler = RotatingFileHandler(
        config['filename'],
        mode='a',
        maxBytes=config['maxsize'],
        backupCount=10
    )
    format = logging.Formatter(config['format'])
    filehandler.setFormatter(format)
    logger.addHandler(filehandler)

    return logger


if __name__ == '__main__':
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception:
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    setup_log(config['log'])

    while True:
        try:
            # 예외시 재접속
            vt = Store(config)
        except Exception as e:
            time.sleep(10)
            continue
        else:
            try:
                # 작업시작
                vt.work()
            except Exception as e:
                time.sleep(10)
                continue
