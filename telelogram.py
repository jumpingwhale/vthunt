#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import logging
import threading
from queue import PriorityQueue
from logging.handlers import RotatingFileHandler
from telepot import Bot, glance
try:
    from cStringIO import StringIO      # Python 2 compatible
except ImportError:
    from io import StringIO


CRITICAL = logging.CRITICAL  # 50
ERROR = logging.ERROR  # 40
WARNING = logging.WARNING  # 30
INFO = logging.INFO  # 20
DEBUG = logging.DEBUG  # 10
NOTSET = logging.NOTSET  # 0


_MAX_BYTES = 5*1024*1024
_MAX_BACKUP = 5


_LOG_NAME = ''


class _Telegram(threading.Thread):
    """Telegram 봇 관리 클래스"""

    def __init__(self, token, queue):
        """
        봇 초기화 및 메시지루프 등록

        봇은 botfather 을 통해 등록가능
        자세한 사용법은 여기 참고
        https://core.telegram.org/bots/api
        # TODO: 링크추가

        :param token: 텔레그램 봇 API 키
        :type token: str
        """
        threading.Thread.__init__(self)
        self.bot = Bot(token)
        self.bot.message_loop(self.msg_handler)

        self.chat_ids = set([])  # 메시지를 전송할 chat_id 리스트(set([]) 는 리스트와 동일하게 사용가능)

        self.queue = queue

    def __del__(self):
        self.bot.deleteWebhook()

    def send_log(self, msg):
        """
        등록한 모든 사용자에게 로그 전송

        :param msg:
        :return:
        """
        for chat_id in self.chat_ids:
            self.send_msg(chat_id, msg)

    def send_msg(self, chat_id, msg):
        """
        해당하는 id에 메시지 전송

        :param chat_id:
        :param msg:
        :return:
        """
        self.bot.sendMessage(chat_id, msg)

    def msg_handler(self, msg):
        """
        메시지 핸들러

        콜백으로 동작한다
        :param msg:
        :return:
        """
        # 사용자가 보내온 메시지 정리
        content_type, chat_type, chat_id = glance(msg)

        # 보낸 메시지가 텍스트라면 해당하는 명령 수행
        if content_type is 'text':
            if msg['text'] == '/enter':
                self.chat_ids.add(chat_id)
                self.queue.put((0, 'Chat_id(%d) is registered to Telelogram' % chat_id))
                self.queue.put((0, 'current users: %d' % len(self.chat_ids)))
            elif msg['text'] == '/exit':
                self.chat_ids.remove(chat_id)
                self.queue.put((0, 'Chat_id(%d) is deleted from Telelogram' % chat_id))
                self.queue.put((0, 'current users: %d' % len(self.chat_ids)))
            else:  # 해당없는 텍스트는 echo
                self.queue.put((0, 'Chat_Id(%d) said \'%s\'' % (chat_id, msg['text'])))

    def run(self):
        while True:
            _priority, msg = self.queue.get()
            self.send_log(msg)


class _TelegramHandler(logging.StreamHandler):
    """텔레그램 메시지 전송을 위한 로그메시지 핸들러"""
    def __init__(self, apikey=None, keepalive=0):
        super().__init__(None)

        # 텔레그램 동시전송 방지를 위해 큐로 변경
        self.queue = PriorityQueue()

        # 가장 최신 로그 저장변수
        self.last_msg = 'No logs yet'

        # 텔레그램 메시지 전송용 쓰레드 생성
        self.thread_telegram = _Telegram(apikey, self.queue)
        self.thread_telegram.start()

        # KeepAlive 용 쓰레드 생성
        self.keepalive = keepalive  # keepalive 메시지 전송간격 (초)
        if self.keepalive and isinstance(self.keepalive, int):
            self.hthread = threading.Thread(target=self.emit_keepalive)
            self.hthread.start()

    def __del__(self):
        del self.thread_telegram
        self.queue.empty()
        del self.queue

    def emit(self, record):
        """
        Emit a record.

        If a formatter is specified, it is used to format the record.
        The record is then written to the stream with a trailing newline.  If
        exception information is present, it is formatted using
        traceback.print_exception and appended to the stream.  If the stream
        has an 'encoding' attribute, it is used to determine how to do the
        output to the stream.
        """
        try:
            # 로그메시지 수신
            msg = self.format(record)
            self.last_msg = msg

            # 큐가 너무 길 경우 ignore silently (1000 개 보내는데 보통 8분 소요)
            if len(self.queue.queue) > 100:
                raise IOError

            # 텔레그램에 전달
            self.queue.put((1, msg))
            self.flush()
        except Exception:
            self.handleError(record)

    def emit_keepalive(self):
        import time
        while True:
            time.sleep(self.keepalive)
            self.queue.put((0, 'KEEP ALIVE - ' + self.last_msg))


def _exception_hook(exc_type, exc_value, exc_traceback):
    """
    Unhandled exception 을 위한 전역 예외처리기

    :param exc_type:
    :param exc_value:
    :param exc_traceback:
    :return:
    """
    # if issubclass(exc_type, KeyboardInterrupt):  # 키보드 인터럽트의 경우
    #     sys.__excepthook__(exc_type, exc_value, exc_traceback)  # 흑 원본 호출
    logging.getLogger(_LOG_NAME).critical('Unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))


def setup_log(logpath=None, logname=__name__, loglevel=DEBUG, apikey=None, hook=False, keepalive=0):
    """
    전역로거를 설치한다

    로거는 '이름'으로 접근할 수 있다
    이름을 명시하지 않으면, 현재 모듈이름을 DEBUG 레벨로 자동으로 가져온다

    'root' 로거 사용시 파이썬 내장 모듈의 로그도 같이 뜰 것이니 주의

    logging.getLogger('MyLoggerName').debug('My debug msg') 와 같이
    한번 설치한 로거를 어디서든 쓸 수 있다

    로그 메시지는 하나의 로거에 '핸들러'를 추가해
    로거에 전달된 메시지를 각각의 핸들러가 포맷과 출력기기에 맞게 출력해주는 방식

    logpath 명시 안하면, stderr 로만 로그를 출력한다
    텔레그램 봇이 없다고? apikey 를 생략하면 된다

    hook 은 전역 예외처리기에 관한 부분
    전역 예외처리기 등록시 예상치 못한 에러에도 앱을 계속 실행할 수 있다
    단, multi thread 환경에선 불가

    :param logpath: 로그파일 저장경로(파일명 포함)
    :type logpath: str
    :param logname: 로거 이름
    :type logname: str
    :param loglevel: 로그 레벨
    :type loglevel: int
    :param apikey: 텔레그램 봇 api키
    :type apikey: str
    :param hook: 전역 예외처리 훅 설치 여부
    :type hook: bool
    :param keepalive: keep alive 전송 간격 (초)
    :type keepalive: int
    """
    # exception_hook 을 위한 글로벌 로거명 설정
    global _LOG_NAME
    _LOG_NAME = logname

    # logger 인스턴스를 생성
    _logger = logging.getLogger(logname)

    # 로깅 레벨 설정
    _logger.setLevel(loglevel)

    # 파일로그의 경우
    if isinstance(logpath, str):
        # 저장경로 설정
        _main_path = os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__))
        _log_path = os.path.join(_main_path, logpath)  # (원본실행위치 + 상대경로)

        # 핸들러 설정
        _file = RotatingFileHandler(_log_path, mode='a', maxBytes=_MAX_BYTES, backupCount=_MAX_BACKUP)

        # 핸들러 로거에 추가
        _logger.addHandler(_file)

    # 텔레그램로그의 경우
    if isinstance(apikey, str):
        # 핸들러 설정
        _telegram = _TelegramHandler(apikey, keepalive)

        # 핸들러 로거에 추가
        _logger.addHandler(_telegram)

    # 기본로그(stderr) 의 경우
    if True:
        # 핸들러 설정
        _stderr = logging.StreamHandler()  # stderr 출력용 핸들러

        # 핸들러 로거에 추가
        _logger.addHandler(_stderr)

    # 전체 핸들러에 대한 로그 포맷과 로그레벨 설정
    _formatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    for handlr in _logger.handlers:
        handlr.setFormatter(_formatter)
        handlr.setLevel(loglevel)

    # 전역 에러 핸들러 설정, main 쓰레드의 예상치 못한 에러에도 계속 실행이 가능하다
    if hook:
        sys.excepthook = _exception_hook

    _logger.info('Logger \'%s\' initiated with %s' % (logname, str(_logger.handlers)))

    return _logger


def __how_to_use():
    """
    사용예제

    1. botFather 에서 봇 생성
    2. @my_bot 대화창을 열고 대기한다
    3. setup_log(logname='mylogger', loglevel=DEBUG, apikey='MY_API_KEY')
    4. @my_bot 대화창에서 '/enter' 입력
    5. logging.getLogger('mylogger').debug('My debug msg')  # 어디서든 이 형태로 출력 가능
    :return:
    """
    setup_log(logname='mylogger', loglevel=DEBUG, apikey='MY_API_KEY', hook=True)
    while True:
        msg = input('Type anything: ')
        logging.getLogger('mylogger').debug('Test log: \'%s\'' % str(msg))


if __name__ == '__main__':
    pass
