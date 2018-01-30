# HOW TO INSTALL #

## vtnoti.py ##
This module stands for gathering virustotal hunting notification. Needs virustotal private API.

### Creating Docker Image ###
```Dockerfile
# 베이스 이미지
FROM python:3
# 폴더관련 작업(생성, 작업폴더설정, 외부노출)
RUN mkdir -p /usr/src/app
RUN mkdir -p /usr/src/app/log
WORKDIR /usr/src/app
VOLUME /usr/src/app/log
# requirements.txt 이미지로 복사 및 모듈 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
# 소스코드 복사
COPY . .
# 스크립트 실행
CMD [ "python", "./vtnoti.py" ]
```
```
docker build -t vthunt_notification .
```

### Creating Container ###
```
docker \
  run \
  -d \
  -it \
  --volume /volume1/docker/python/vthunt_noti:/usr/src/app/log \
  --name vthunt_notification_con \
  vthunt_notification
```

## vtdownload.py ##
This module stands for downloading samples which filtered out by virustotal hunting rule. Needs virustotal private API.
Make sure that `/usr/src/app/log` path is as same as `config['log']['logfile']`

### Creating Docker Image ###
```Dockerfile
# 베이스 이미지
FROM python:3
# 폴더관련 작업(생성, 작업폴더설정, 외부노출)
RUN mkdir -p /usr/src/app
RUN mkdir -p /usr/src/app/log
WORKDIR /usr/src/app
VOLUME /usr/src/app/log
# requirements.txt 이미지로 복사 및 모듈 설치
COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt
# 소스코드 복사
COPY . .
# 스크립트 실행
CMD [ "python", "./download.py" ]
```
```
docker build -t vthunt_download .
```

### Creating Container ###
```
docker \
  run \
  -d \
  -it \
  --volume /volume1/docker/python/vthunt_download:/usr/src/app/log \
  --name vthunt_download_con \
  vthunt_download
```