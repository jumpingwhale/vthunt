#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
main.py
_________
"""
import os
import time
import glob
import multiprocessing
import re
import pprint
import logging
from logging.handlers import TimedRotatingFileHandler
from logging.handlers import SMTPHandler
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
import vtdownload
import vtnoti
import vtreport


def setup_module_log(config, modules):
    for m in modules:
        # 각 모듈별 로거는 모듈 이름을 사용
        logname = m.__name__
        logger = logging.getLogger(logname)
        logger.setLevel(config['loglevel'])

        logfile = os.path.join(config['path'], logname + '.log')
        h = TimedRotatingFileHandler(
            logfile,
            when='midnight',  # Virustotal resets private API count at midnight UTC (add 9 to Asia/Seoul)
            interval=1,
            backupCount=1,
            utc=True,
        )
        h.suffix = '%Y-%m-%d'
        format = logging.Formatter(config['format'])
        h.setFormatter(format)

        logger.addHandler(h)
    return True


def setup_smtp_log(config):
    # 로그 취합/전송하는 smtp 로거는 설정파일에 명시된 이름 사용
    logger = logging.getLogger(config['logname'])
    logger.setLevel(config['loglevel'])
    gmail_host = config['gmail_host']
    gmail_port = config['gmail_port']
    fromaddr = config['fromaddr']
    toaddrs = config['toaddrs']
    subject = config['subject']
    credentials = config['credentials']
    secure = ()
    smtphandler = SMTPHandler((gmail_host, gmail_port), fromaddr, toaddrs, subject, credentials, secure)
    logger.addHandler(smtphandler)

    return logger


def parse_log(filename):
    p_queue = re.compile(r'processing\s[0-9]{0,8}\shashes')

    with open(filename, 'r') as fp:
        queue = 0
        warning = 0
        critical = 0

        # 각 로그라인별로
        for line in fp.readlines():

            # 큐 크기 수집
            match = p_queue.search(line)
            if match:
                queue += int(match.group(0).split(' ')[1])

            if line.find('CRITICAL') > -1:
                critical += 1

            if line.find('WARNING') > -1:
                warning += 1

    return queue, warning, critical


if __name__ == '__main__':

    # UTC -> 로컬타임
    os.environ['TZ'] = 'Asia/Seoul'
    time.tzset()  # Unix only

    # 설정파일 읽기
    try:
        with open("config_master.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)
    except Exception as e:
        print(e)
        with open("config.yml", 'r') as ymlfile:
            config = yaml.load(ymlfile)

    # 모듈 로거 설정
    modules = [vtdownload, vtreport, vtnoti]
    setup_module_log(config['module_log'], modules)

    # 이메일 로거 설정
    smtp_logger = setup_smtp_log(config['smtp_log'])

    procs = list()
    for m in modules:
        proc = multiprocessing.Process(target=m.work, args=(config, ))
        procs.append(proc)
        proc.start()

    [proc.join() for proc in procs]

    sched = BlockingScheduler()

    @sched.scheduled_job('cron', id='my_job_id', hour=9, minute=30, second=0)
    def send_email():
        result = dict()

        for module in modules:
            files = glob.glob('log/%s*' % module.__name__)
            for f in files:
                if not f.endswith('log'):
                    queue, warning, critical = parse_log(f)

                    result[module.__name__] = {
                        'filename': f,
                        'queue': queue,
                        'warning': warning,
                        'critical': critical,
                    }

        msg = pprint.pformat(result, indent=4)
        smtp_logger.info(msg)

    sched.start()
