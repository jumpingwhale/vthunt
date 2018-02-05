#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
main.py
_________
"""
import os
import json
import time
import requests
import pymysql
import logging


CHECK_NOTIFICATION_DUPLICATED = 'SELECT hunt FROM virustotal WHERE md5=%s'
INSERT_NOTIFICATION = 'INSERT INTO virustotal (hunt, md5) VALUES (%s, %s)'


class Notification:
    def __init__(self, config):
        self.config = config
        self.api = config['virustotal']['api']
        self.logger = logging.getLogger(__name__)
        self.trigger = False
        self.conn = None
        self.cur = None
        self.url_noti = 'https://www.virustotal.com/intelligence/hunting/notifications-feed/?key=%s&output=json' % \
                        self.api
        self.url_del = 'https://www.virustotal.com/intelligence/hunting/delete-notifications/programmatic/?key=%s' % \
                       self.api
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

    def __delete_noti(self, ids):
        # virustotal 서버에서 noti 삭제
        try:
            requests.post(self.url_del, data=json.dumps(ids))
        except Exception:
            self.logger.critical('failed to delete notification')
            raise
        return True

    def work(self):
        while True:
            res = requests.post(self.url_noti)  # hunting notification 수령
            if res.content:
                content = res.json()
                notis = content['notifications']

                if notis:
                    self.logger.info('processing %d hashes' % len(notis))

                    # 처리 완료된 notification id
                    complete_ids = list()

                    for noti in notis:  # 공지는 리스트형태
                        # 완료처리할 목록에 추가
                        complete_ids.append(noti['id'])

                        # 노티 중복확인
                        vals = (noti['md5'],)
                        self.cur.execute(CHECK_NOTIFICATION_DUPLICATED, vals)
                        if self.cur.rowcount:  # 중복, 패스
                            self.logger.warning('already registered in samples.virustotal %s' % noti['md5'])
                        else:  # 신규등록해쉬
                            # DB 저장
                            vals = (json.dumps(noti), noti['md5'])
                            try:
                                self.cur.execute(INSERT_NOTIFICATION, vals)
                                self.conn.commit()
                            except Exception as e:
                                self.logger.critical('failed to insert new notification %s' % noti['md5'])
                                raise
                            else:
                                self.logger.info('%s has done' % noti['md5'])

                    # 완료처리 (virustotal 서버에서 noti 삭제)
                    self.__delete_noti(complete_ids)

            time.sleep(60)


def work(config):
    # UTC -> 로컬타임
    os.environ['TZ'] = 'Asia/Seoul'
    time.tzset()
    while True:
        try:
            # 예외시 재접속
            noti = Notification(config)
        except Exception as e:
            time.sleep(10)
            continue
        else:
            try:
                # 작업시작
                noti.work()
            except Exception as e:
                time.sleep(10)
                continue


if __name__ == '__main__':
    pass
