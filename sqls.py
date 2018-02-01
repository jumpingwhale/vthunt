#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
sqls.py
_________
"""
SELECT_EMPTY_REPORT_SAMPLE = 'SELECT depot.md5 FROM depot INNER JOIN virustotal ON depot.md5=virustotal.md5 WHERE virustotal.report IS NULL'
NULL_AS_JSON = 'SELECT * FROM samples.virustotal where JSON_EXTRACT(hunt, "$.ruleset_name") = CAST("null" AS JSON);'

CHECK_NOTIFICATION_DUPLICATED = 'SELECT hunt FROM virustotal WHERE md5=%s'
INSERT_NOTIFICATION = 'INSERT INTO virustotal (hunt, md5) VALUES (%s, %s)'

SELECT_SAMPLES_NOT_STORED = 'SELECT  JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.md5")), depot.path ' \
                            'FROM virustotal INNER JOIN depot ' \
                            'ON virustotal.md5 = depot.md5 AND depot.path IS NULL ' \
                            'LIMIT 100'
UPDATE_PATH = 'UPDATE depot SET path=%s WHERE md5=%s'

SELECT_BY_RULESET = 'SELECT md5 FROM samples.virustotal where JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.ruleset_name")) = "%s"'
SELECT_RULESET_NAMES = 'SELECT DISTINCT JSON_UNQUOTE(JSON_EXTRACT(virustotal.hunt, "$.ruleset_name")) FROM virustotal'

CHECK_DUPLICATE = 'SELECT md5 FROM virustotal GROUP BY md5 HAVING COUNT(md5) > 1'
COMPARE_TABLE = 'SELECT virustotal.md5 FROM virustotal WHERE NOT EXISTS (SELECT md5 FROM depot WHERE virustotal.md5=depot.md5)'