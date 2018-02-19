#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import os
import json
import time
import pymysql
import logging
import virustotal
from virustotal.err import *

WAIT_SUCCESS_TIME = 60
WAIT_ERROR_TIME = 15


class Server:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.vt = virustotal.connect(config['virustotal']['public'], False)
        try:
            self.conn = pymysql.connect(
                host=config['mysql']['host'],
                port=config['mysql']['port'],
                database=config['mysql']['database'],
                user=config['mysql']['user'],
                passwd=config['mysql']['passwd'],
            )
            self.cur = self.conn.cursor(pymysql.cursors.DictCursor)
        except:
            self.logger.critical('MySql connection error')
            raise

    def __del__(self):
        self.cur.close()
        self.conn.close()

    # 대상 해시를 가져옴
    def query_db(self):
        sql = 'select depot.md5 from depot inner join virustotal on depot.md5=virustotal.md5 where virustotal.report is null;'
        self.cur.execute(sql)
        result = self.cur.fetchall()
        return result

    # 레포트 저장
    def send_report(self, md5, report):
        sql = "update virustotal set report=%s where md5=%s"
        self.cur.execute(sql, (report, md5))
        self.conn.commit()
        if report.find('"response_code": 0') != -1:
            self.logger.info('No Report: ' + md5)
        else:
            self.logger.info('Report Saved: ' + md5)

    def work(self):
        while (True):
            try:
                hash_dicts = self.query_db()
            # 해시를 받아오지 못했을 경우
            except:
                self.logger.critical("Query Hash Error")
                time.sleep(WAIT_ERROR_TIME)
                continue
            # 대상 해시가 없으면 대기한다.
            if not hash_dicts:
                self.logger.warning("No Hashes")
                time.sleep(WAIT_SUCCESS_TIME)
                continue
            self.logger.info("processing %d hashes" % len(hash_dicts))
            # 받아온 해시 목록을 이용해 레포트를 받아온다.
            for hash_dict in hash_dicts:
                try:
                    report = self.vt.report(hash_dict['md5'])
                # 바토에 레포트가 없는 경우 레포트 생성
                except NoReportError:
                    report = {'response_code': 0, 'resource': hash_dict['md5'],
                              'verbose_msg': 'The requested resource is not among the finished, queued or pending scans'}
                except Exception as err:
                    self.logger.critical(err)
                    time.sleep(WAIT_ERROR_TIME)
                    continue
                # 레포트를 저장한다.
                report_json = json.dumps(report)
                try:
                    self.send_report(hash_dict['md5'], report_json)
                except:
                    self.logger.critical("Save Report Error")
                    time.sleep(WAIT_ERROR_TIME)
            # 한번의 해시 세트가 끝나면 대기
            self.logger.info('Hash Set Done')
            time.sleep(WAIT_SUCCESS_TIME)


def work(config):
    # UTC -> 로컬타임
    os.environ['TZ'] = 'Asia/Seoul'
    time.tzset()

    while True:
        try:
            server = Server(config)
        except:
            time.sleep(WAIT_ERROR_TIME)
            continue
        else:
            try:
                server.work()
            except:
                time.sleep(WAIT_ERROR_TIME)
                continue


if __name__ == '__main__':
    pass
