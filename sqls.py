#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
sqls.py
_________
"""

NULL_AS_JSON = 'SELECT * FROM samples.virustotal where JSON_EXTRACT(hunt, "$.ruleset_name") = CAST("null" AS JSON);'

CHECK_NOTIFICATION_DUPLICATED = 'SELECT hunt FROM virustotal WHERE md5=%s'
INSERT_NOTIFICATION = 'INSERT INTO virustotal (hunt, md5) VALUES (%s, %s)'

SELECT_SAMPLES_NOT_STORED = 'SELECT JSON_EXTRACT(notification, "$.md5") FROM storage WHERE path IS NULL LIMIT 10'
UPDATE_PATH = 'UPDATE storage SET path=%s WHERE JSON_EXTRACT(notification, "$.md5")=%s'

SELECT_BY_RULESET = 'SELECT md5 FROM samples.virustotal where JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.ruleset_name")) = "%s"'
SELECT_RULESET_NAMES = 'SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.ruleset_name")) FROM virustotal'
