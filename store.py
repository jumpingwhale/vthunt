#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""

_________
"""

import os
import io
import errno
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler
import pymysql
import paramiko
import yaml
import hashlib
from scandir import scandir


# virustotal.hunt 엔 있고, depot 엔 저장되지 않은(depot.path == NULL) 샘플들만 다운로드 받는다
INSERT_NEW_SAMPLE = 'INSERT INTO depot (md5, path) VALUES (%s, %s)'
ALREADY_UPLOADED = 'SELECT md5, path FROM depot WHERE md5=%s'


class Store:
    def __init__(self, config):
        self.config = config
        self.api = config['virustotal']['api']
        self.logger = logging.getLogger(config['module_log']['logname'])
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
        # UTC -> 로컬타임
        os.environ['TZ'] = 'Asia/Seoul'
        time.tzset()  # unix only

        while True:
            # 리소스소모 방지
            time.sleep(self.config['store']['scandelay'])

            for entry in scandir(self.monitor):  # 모든 파일목록을 한번에 로드하는걸 방지
                if not entry.is_file(follow_symlinks=False):
                    continue
                filename = entry.name  # 파일 이름
                fullpath = entry.path  # 파일 경로

                currtime = datetime.datetime.now()  # 현재시각
                mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fullpath))  # 마지막 수정시각
                delta = currtime - mtime  # 마지막 수정부터 현재까지 시간

                # 수정한지 n초가 넘었으면(다운로드가 끝났으면)
                if datetime.timedelta(seconds=self.config['store']['timedelta']) < delta:
                    self.logger.info('processing %s' % os.path.basename(filename))

                    # 파일크기 검증
                    if os.path.getsize(fullpath) > 1024 * 1024 * 40:  # 40MB 이상 스킵
                        self.logger.warning('file size is too big %d' % os.path.getsize(filename))
                        os.remove(fullpath)
                        continue

                    # 파일읽기
                    with open(fullpath, 'rb') as fp:
                        buf = fp.read()

                    # 해쉬값 생성
                    m = hashlib.md5()
                    m.update(buf)
                    md5 = m.hexdigest()

                    # 중복 업로드 검증
                    vals = (md5,)
                    self.cur.execute(ALREADY_UPLOADED, vals)
                    if self.cur.rowcount:
                        self.logger.warning('hash duplicated')
                        os.remove(fullpath)
                        continue

                    # 업로드
                    remote = self.__store_sftp(md5, buf)

                    # db 인서트
                    sql = INSERT_NEW_SAMPLE
                    vals = (md5, remote)
                    self.cur.execute(sql, vals)
                    self.conn.commit()

                    # 완료파일 삭제
                    os.remove(fullpath)

    def __store_sftp(self, md5, binary):
        def exists(sftp, path):
            try:
                sftp.stat(path)
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
        if not exists(self.sftp, remote_dir):
            path_to_remote_dir = root
            for prefix in prefixes:
                path_to_remote_dir = '/'.join([path_to_remote_dir, prefix])
                try:
                    self.sftp.mkdir(path_to_remote_dir)  # MD5 해쉬값, 두 글자단위, 2 depth 로 폴더생성
                except Exception:
                    pass

        # 이미 파일 있으면 삭제
        if exists(self.sftp, remote_path):
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
    filename = os.path.join(config['path'], config['logname'] + '.log')
    filehandler = RotatingFileHandler(
        filename,
        mode='a',
        maxBytes=1024*1024*5,
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

    setup_log(config['module_log'])

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
