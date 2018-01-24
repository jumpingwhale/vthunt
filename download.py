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
import requests
import pymysql
import paramiko
import yaml
import sqls


def work(config):
    # DB 접속
    conn = pymysql.connect(
        host=config['mysql']['host'],
        port=config['mysql']['port'],
        database=config['mysql']['database'],
        user=config['mysql']['user'],
        passwd=config['mysql']['passwd'], )
    cur = conn.cursor()

    # 로거 설정
    logger = logging.getLogger(config['log']['logname'])

    # SFTP 접속
    conn_sftp(config['SFTP'])

    while True:
        time.sleep(5)

        # 미다운로드 샘플 확인 (path 가 NULL 이면 미다운로드로 간주)
        sql = sqls.SELECT_SAMPLES_NOT_STORED
        try:
            cur.execute(sql)
        except Exception as e:
            logger.critical(str(e))
            continue
        else:
            if cur.rowcount:
                # 미다운로드 md5 확보
                md5s = [row[0].lower().replace('"', '') for row in cur.fetchall()]
                # 각각 다운로드
                for md5 in md5s:
                    url_download = 'https://www.virustotal.com/intelligence/download/?hash=%s&apikey=%s' % \
                          (md5, config['virustotal']['api'])
                    try:
                        res = requests.post(url_download)
                    except Exception as e:
                        logger.critical(str(e))
                        continue

                    # 저장및 저장위치 리턴
                    path = store(md5, res.content)
                    if path:
                        path = path.replace('\\', '/')  # 저장경로 linux_path 로 변환
                    else:
                        continue

                    try:
                        cur.execute(sqls.UPDATE_PATH, (path, md5))  # DB에 저장경로 업데이트
                        conn.commit()
                    except Exception as e:
                        logger.critical(str(e))
                        continue
                    else:
                        logger.info('stored \'%s\'' % md5)


def store(md5, binary):
    root = 'md5'
    prefixes = [md5[:2], md5[2:4]]

    # 디렉토리 생성
    if not os.path.exists(os.path.join(root, *prefixes)):  # '*' makes list to pointer?
        storepath = root
        for prefix in prefixes:
            storepath = os.path.join(storepath, prefix)
            try:
                os.mkdir(storepath)  # MD5 해쉬값, 두 글자단위, 2 depth 로 폴더생성
            except FileExistsError:
                pass
    # 파일저장
    with open(os.path.join(root, *prefixes, md5), 'wb') as fp:
        fp.write(binary)

    return os.path.join(root, *prefixes, md5)


def store_sftp(sftp, md5, binary):
    def exists(path):
        try:
            sftp.stat(path)
        except IOError as e:
            if e.errno == errno.ENOENT:
                return False
            raise
        else:
            return True

    root = 'md5'
    prefixes = [md5[:2], md5[2:4]]
    remote_dir = '/'.join([root, ] + prefixes)
    remote_path = '/'.join([remote_dir, md5])

    if not exists(remote_dir):
        path_to_remote_dir = root
        for prefix in prefixes:
            path_to_remote_dir = '/'.join([path_to_remote_dir, prefix])
            try:
                sftp.mkdir(path_to_remote_dir)  # MD5 해쉬값, 두 글자단위, 2 depth 로 폴더생성
            except Exception:
                pass

    fp = io.BytesIO(binary)
    try:
        sftp.putfo(fp, remote_path)
    except Exception:
        return False
    else:
        return remote_path


def conn_sftp(config):
    host = config['host']
    port = config['port']
    user = config['user']
    passwd = config['passwd']

    ret = False
    sock = (host, port)

    try:
        t = paramiko.Transport(sock)
    except paramiko.SSHException as e:
        print(str(e))
    else:
        # Transport 로 서버 접속
        try:
            t.connect(username=user, password=passwd)
        except paramiko.SFTPError as e:
            print(str(e))
        except paramiko.SSHException as e:
            print(str(e))
        else:
            # 클라이언트 초기화
            try:
                sftp = paramiko.SFTPClient.from_transport(t)
            except paramiko.SFTPError as e:
                print(str(e))
            else:
                ret = sftp
    return ret


if __name__ == '__main__':
    """test code"""
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception:
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    sftp = conn_sftp(config['sftp'])
    if sftp:
        store_sftp(sftp, '00000000000000000000000000000000', b'111')
