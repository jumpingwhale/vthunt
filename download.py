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
import logging
from logging.handlers import RotatingFileHandler
import requests
import pymysql
import paramiko
import yaml

# virustotal.hunt 엔 있고, depot 엔 저장되지 않은(depot.path == NULL) 샘플들만 다운로드 받는다
SELECT_SAMPLES_NOT_STORED = 'SELECT  JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.md5")), depot.path ' \
                            'FROM virustotal INNER JOIN depot ' \
                            'ON virustotal.md5 = depot.md5 AND depot.path IS NULL ' \
                            'LIMIT 10'

UPDATE_PATH = 'UPDATE depot SET path=%s WHERE md5=%s'


class VTDownloader:

    def __init__(self, config):
        self.config = config
        self.logger = self.__setup_log(config['log'])
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

    def __setup_log(self, config):
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
                self.sftp.mkdir(path_to_remote_dir)  # MD5 해쉬값, 두 글자단위, 2 depth 로 폴더생성

        # 이미 파일 있으면 삭제
        if exists(remote_path):
            self.sftp.remove(remote_path)

        fp = io.BytesIO(binary)
        self.sftp.putfo(fp, remote_path)
        return remote_path

    def work(self):

        while True:
            time.sleep(5)

            try:
                # 미다운로드 샘플 확인 (path 가 NULL 이면 미다운로드로 간주)
                sql = SELECT_SAMPLES_NOT_STORED
                self.cur.execute(sql)
            except Exception as e:
                self.logger.critical(str(e))
                raise
            else:
                if self.cur.rowcount:
                    self.logger.info('%d samples queued' % self.cur.rowcount)

                    # 미다운로드 md5 확보
                    md5s = [row[0].lower() for row in self.cur.fetchall()]

                    # 각각 다운로드
                    for md5 in md5s:
                        url_download = 'https://www.virustotal.com/intelligence/download/?hash=%s&apikey=%s' % \
                              (md5, config['virustotal']['api'])
                        try:
                            res = requests.post(url_download)
                        except Exception as e:
                            self.logger.critical(str(e))
                            raise

                        # 서버저장 및 서버 저장위치 리턴
                        path = self.__store_sftp(md5, res.content)
                        if path:
                            path = path.replace('\\', '/')  # 저장경로 linux_path 로 변환
                        else:
                            self.logger.critical('failed to store SFTP')
                            raise IOError

                        try:
                            self.cur.execute(UPDATE_PATH, (path, md5))  # DB에 저장경로 업데이트
                            self.conn.commit()
                        except Exception as e:
                            self.logger.critical(str(e))
                            raise
                        else:
                            self.logger.info('stored \'%s\'' % md5)


if __name__ == '__main__':
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception:
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    while True:
        try:
            # 예외시 재접속
            vt = VTDownloader(config)
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
