#!/usr/bin/python3

# (c) 2021 Christian Gajan <christian.gajan@netapp.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

'''
fill_sql_db
'''

from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {'metadata_version': '1.0.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
module: fill_sql_db
author: Christian Gajan <christian.gajan@netapp.com>
short_description: Save records in a SQLite DB
description:
    - This module allows you to create a table in a new or existing SQLite DB files
      and fill it with provided data records given as list of list in json format
      Schema of the table is given as a list of dict in json format
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

from ansible.module_utils.basic import AnsibleModule

def main():
    # Define Module Arguments
    module_args = dict(
       state=dict(type='str', required=False),
       db_base=dict(type='str', required=False),
       db=dict(type='str', required=False),
       table=dict(type='str', required=False),
       structure=dict(type='str', required=False),
       records=dict(type='list', elements='list', required=False)
    )

    module = AnsibleModule(argument_spec=module_args)
    result= {}
    result['changed'] = False

    # Read Module Arguments
    state = module.params['state']
    db_base = module.params['db_base']
    db = module.params['db']
    table = module.params['table']
    structure = module.params['structure']
    records = module.params['records']

    # Set some default argument values when they are not specified
    if state is None:
        state = "load"
    if db_base is None:
       db_base = "/tmp/DB_"
    if db is None:
       # When no DB file is specified, this means
       # that we have to create one
       db = db_base + str(uuid.uuid4())

    if state != 'absent':  # state == 'load'
       # We must create DB if not exist,
       # Create the table and fill the table with given data

       # Check if needed attributes are provided
       if table is None:
           module.fail_json(msg="No table attribute specified to define the table name", **result)
       if structure is None:
           module.fail_json(msg="No structure attribute specified to define the table '%s' schema" % table, **result)
       if records is None:
           module.fail_json(msg="No records attribute specified to define entries to insert in table '%s'" % table, **result)
       # Parse the json string which define the table schema
       try:
           model = json.loads(structure)
       except Exception as e:
           module.fail_json(msg="Fail to parse structure json string: %s" % e, **result)
       # Build the SQL requests to create the Table and to fill it
       sql_create_table = "CREATE TABLE IF NOT EXISTS " + table + " ("
       sql_insert_table = "REPLACE INTO " + table + " ("
       pk = ""
       arg = ""
       ccount = 0
       for column in model:
           sql_create_table = sql_create_table + column['name'] + " " + column['type'] + ", "
           sql_insert_table = sql_insert_table + column['name'] + ", "
           arg = arg + "?, "
           ccount += 1
           if column['pk'] == 1:
               pk = pk + column['name'] + ", "
       if pk != "":
           sql_create_table = sql_create_table + "PRIMARY KEY (" + pk[:-2] + "));"
       else:
           sql_create_table = sql_create_table[:-2] + ");"
       sql_insert_table = sql_insert_table[:-2] + ") VALUES (" + arg[:-2] + ")"

       # Check that data record has the right number of column
       if (len(records) > 0) and (len(records[0]) != ccount):
           module.fail_json(msg="Number of data columns does not match the table structure", **result)
       # Open the SQLite DB file
       try:
           conn = sqlite3.connect(db)
       except Exception as e:
           module.fail_json(msg="Fail to open the db file '%s': %s" % (db, e), **result)
       # Execute the table creation SQL query
       try:
           c = conn.cursor()
           c.execute(sql_create_table)
           result['changed'] = True
           result['db'] = db
       except Exception as e:
           conn.close()
           module.fail_json(msg="Fail to create the table '%s': %s" % (table, e), **result)
       # Execute the insertion SQL query
       try:
           if len(records) > 0:
             c.executemany(sql_insert_table, records)
       except Exception as e:
           conn.close()
           module.fail_json(msg="Fail to insert data the table '%s': %s" % (table, e), **result)
       # Commit DB change and close the DB file
       try:
           conn.commit()
           conn.close()
       except Exception as e:
           module.fail_json(msg="Fail to commit modification in db '%s': %s" % (db, e), **result)
       # Return Success and the DB file path for other call
       module.exit_json(changed=True, db=db)
    else:  # state == 'absent'
       # db parameter must be provided
       if db is None:
           module.fail_json(msg="No db attribute specified to define the db file to be deleted", **result)
       # Remove the db file if exist
       try:
           if os.path.exists(db):
               os.remove(db)
           # Return Success
           module.exit_json(changed=True, db=db)
       except Exception as e:
           module.fail_json(msg="Fail to remove the db file '%s': %s" % (db, e), **result)

if __name__ == '__main__':
    main()

