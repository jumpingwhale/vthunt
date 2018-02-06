# HOW TO INSTALL #



## vtreport.py ##
This module crawl virustotal report and store it to local database using public API. Needs [virustotal package](https://github.com/jumpingwhale/virustotal), don't forget to copy/paste it.

## vtnoti.py ##
This module stands for gathering virustotal hunting notification. Needs virustotal private API.

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
CMD [ "python", "./main.py" ]
```
```
docker build -t vthunt .
```

### Creating Container ###
```
docker \
  run \
  -d \
  -it \
  --volume /volume1/docker/python/vthunt:/usr/src/app/log \
  --name vthunt_con \
  vthunt
```


## store.py ##
This module stands for storing samples to sample server from specific local directory.
Manual upload to sample server does nothing because sample server has own database describing sample binary's location in its filesystem.
`store.py` monitors specific directory's contents and every 15 seconds, it stores all files from monitoring directory to sample server.
Monitoring directory in container is `/usr/src/app/monitor`, configurable at `config.yaml`