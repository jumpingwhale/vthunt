#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
sqls.py
_________
"""
CHECK_DUPLICATE = 'SELECT * FROM storage WHERE JSON_EXTRACT(notification, "$.md5")=%s'
INSERT_NOTIFICATION = 'INSERT INTO storage (notification) VALUES (%s)'

SELECT_SAMPLES_NOT_STORED = 'SELECT JSON_EXTRACT(notification, "$.md5") FROM storage WHERE path IS NULL LIMIT 10'
UPDATE_PATH = 'UPDATE storage SET path=%s WHERE JSON_EXTRACT(notification, "$.md5")=%s'
