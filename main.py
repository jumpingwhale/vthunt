#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
main.py
_________
"""
import json
import sqls
import time
import threading
import yaml
import requests
import pymysql
import download
import telelogram


def main():
    # 설정파일 열기
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception:
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    # 로거세팅
    logger = telelogram.setup_log(
        logname=config['log']['logname'],
        loglevel=config['log']['loglevel'],
        apikey=config['log']['apikey'])

    # DB 접속
    conn = pymysql.connect(
        host=config['mysql']['host'],
        port=config['mysql']['port'],
        database=config['mysql']['database'],
        user=config['mysql']['user'],
        passwd=config['mysql']['passwd'],)
    cur = conn.cursor()

    # 다운로드 쓰레드 생성
    t = threading.Thread(target=download.work, args=(config,))
    t.start()

    # 관련 URL 설정
    url_noti = 'https://www.virustotal.com/intelligence/hunting/notifications-feed/?key=%s&output=json' % \
               config['virustotal']['api']
    url_del = 'https://www.virustotal.com/intelligence/hunting/delete-notifications/programmatic/?key=%s' % \
              config['virustotal']['api']

    while True:
        time.sleep(5)

        try:
            res = requests.post(url_noti)  # hunting 룰에 걸린 보고서 요청
        except Exception as e:
            logger.critical(str(e))
            continue
        else:
            if res.content:
                report = res.json()
                for noti in report['notifications']:  # 공지는 리스트형태

                    # 미리 지정한 룰셋만 DB 저장
                    if noti['ruleset_name'] == config['virustotal']['ruleset_name']:
                        try:
                            cur.execute(sqls.CHECK_DUPLICATE, noti['md5'])  # 중복확인
                        except Exception as e:
                            logger.critical(str(e))
                            continue
                        else:
                            if not cur.rowcount:  # 중복 없을때만
                                try:
                                    cur.execute(sqls.INSERT_NOTIFICATION, json.dumps(noti))  # DB 저장
                                    conn.commit()
                                except Exception as e:
                                    logger.critical(str(e))
                                    continue
                                else:
                                    # 서버에서 noti 삭제
                                    requests.post(url_del, data=json.dumps([noti['id'], ]))
                                    logger.info('added \'%s\'' % noti['md5'])


if __name__ == '__main__':
    main()
