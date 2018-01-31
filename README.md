# HOW TO INSTALL #

## store.py ##
This module stands for storing samples to sample server from specific local directory.
Manual upload to sample server does nothing because sample server has own database describing sample binary's location in its filesystem.
'store.py' monitors specific directory's contents and every 15 seconds, it stores all files from monitoring directory to sample server.
Monitoring directory in container is `/usr/src/app/monitor`, configurable at 'config.yaml' 

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
# 모니터링 폴더 노출
RUN mkdir -p /usr/src/app/monitor
VOLUME /usr/src/app/monitor
# 소스코드 복사
COPY . .
# 스크립트 실행
CMD [ "python", "./store.py" ]
```
```
docker build -t store_sample .
```

### Creating Container ###

```
docker \
  run \
  -d \
  -it \
  --volume /volume1/docker/python/store_sample:/usr/src/app/log \
  --volume /volume1/docker/python/store_sample/monitor:/usr/src/app/monitor \
  --name store_sample_con \
  store_sample
```

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
CMD [ "python", "./vtdownload.py" ]
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