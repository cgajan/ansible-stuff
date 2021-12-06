#!/usr/bin/python3

# (c) 2021 Christian Gajan <christian.gajan@netapp.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
select_sql_db
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.0.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: select_sql_db
author: Christian Gajan <christian.gajan@netapp.com>
short_description: Launch SQL query on a SQLite DB file
description:
    - This module allows you ...
version_added: 2.9.0
requirements:
    - uuid
    - json
    - sqlite
options:
    state:
        type: str
        description:
            - If load, table is created if no exist and filled with given data records
            - If absent, the DB file is deleted
    db_base:
        type: str
        description:
            - If present, 'vserver tunneling' will limit the output to the vserver scope.
            - Note that not all subsets are supported on a vserver, and 'all' will trigger an error.
        version_added: '1.0.0'
    db:
        type: str
        description:
            - If present, 'vserver tunneling' will limit the output to the vserver scope.
            - Note that not all subsets are supported on a vserver, and 'all' will trigger an error.
        version_added: '1.0.0'
    table
        type: str
        description:
            - If present, 'vserver tunneling' will limit the output to the vserver scope.
            - Note that not all subsets are supported on a vserver, and 'all' will trigger an error.
        version_added: '1.0.0'
    structure:
        type: str
        description:
            - If present, 'vserver tunneling' will limit the output to the vserver scope.
            - Note that not all subsets are supported on a vserver, and 'all' will trigger an error.
        version_added: '1.0.0'
    records:
        type: str
        description:
            - If present, 'vserver tunneling' will limit the output to the vserver scope.
            - Note that not all subsets are supported on a vserver, and 'all' will trigger an error.
        version_added: '1.0.0'

'''
RETURN = '''
# DEBUG: :
    description: DB file
    type: str
    returned: always
'''

import os
import uuid
import json
import sqlite3
import re

from ansible.module_utils.basic import AnsibleModule

def regexp(expr, item):
    reg = re.compile(expr)
    return reg.search(item) is not None

def main():
    # DEfine Module Arguments
    module_args = dict(
       state=dict(default='query', type='str', required=False),
       db=dict(type='str', required=True),
       query=dict(type='str', required=True),
       limit=dict(default=1, type='int', required=False),
    )

    module = AnsibleModule(argument_spec=module_args)
    result= {}
    result['changed'] = False

    # Read Module Arguments
    state = module.params['state']
    db = module.params['db']
    query = module.params['query']
    limit = module.params['limit']

    # Set some default argument values when they are not specified
    if db is None:
       module.fail_json(msg="No db attribute specified to define the db file", **result)

    if state == 'query':
       # We must create DB if not exist,
       # Create the table and fill the table with given data

       # Check if needed attributes are provided
       if query is None:
           module.fail_json(msg="No query attribute specified to define SQL query to run", **result)

       # Parse the SQL string to check that it is a single SELECT
       if not (query.upper().startswith('SELECT ') ):
           module.fail_json(msg="The SQL query is not a SELECT", **result)
       if query.find(";") != -1:
           module.fail_json(msg="The SQL query is not a single SELECT", **result)

       # Open the SQLite DB file
       try:
           conn = sqlite3.connect(db)
           conn.create_function("REGEXP", 2, regexp)
       except Exception as e:
           module.fail_json(msg="Fail to open the db file '%s': %s" % (db, e), **result)
       # Execute the table creation SQL query
       try:
           c = conn.cursor()
           c.execute(query)
           rows =  c.fetchall()
           conn.close()
           result['changed'] = True
           result['rows'] = rows
       except Exception as e:
           conn.close()
           module.fail_json(msg="Fail to run the query '%s': %s" % (query, e), **result)
       # Return Success and the DB file path for other call
       module.exit_json(**result)
    else:  # state == 'absent'
       # Others state than query are not supported
       module.fail_json(msg="Only query state is supported", **result)

if __name__ == '__main__':
    main()

