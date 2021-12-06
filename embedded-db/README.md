# Advanced Selection with Ansible

Recently I started to work with Ansible, especialy to implement automation for storage provisioning. To provision a resource in a infrastructure, the process will probably always be roughly the same:

- collecting environment information
- run selection criteria on these environment information to select the right target for the provisioning
- finally create the new resource on the selected target

In recent time, more and more software and infrastructure providers are offering Ansible modules to collect information and to create resources on their systems. NetApp was one of the first, with its set of official modules available in Ansible Galaxy (https://galaxy.ansible.com/netapp).

Ansible module and espacially module which collect environment information return structured output in json format. When required selection criteria are simple, Ansible provides natively data filtering feature based on Jinja2 template filters (https://docs.ansible.com/ansible/latest/user_guide/playbooks_filters.html) and json query and JMESPath (https://jmespath.org/) which allow us to implement these simple criteria.

However, when selection criteria become complex, it is difficult to use these filtering methods especially when criteria apply on joins of several data sources.

To try to make the selection stage easier, I developed a couple of simple Ansible modules which allow to use SQL queries on multiple environment information sources.

Foundation ideas behind these two modules are:

- What could be simplier than SQL query to select something based on multiple advanced criteria
- Try to make things simple without dependencies

The magic component to implement these ideas is SQLite (https://sqlite.org/). Yes SQLite is bundle with Python which is bundle with Ansible and SQLite is a DB in a file which does not run any daemon server, so *no dependencies*. Yes SQLite speak SQL so welcome to *SQL queries power*.

Now let's see how easy it is to use it:

```
- name: Store Aggregate Info in DB
  fill_sql_db:
     db: "{{ db_info.embedded_db | default(omit, true) }}"
     table: "aggregate"
     structure: >
          [ { "name": "cluster", "type": "string", "pk": 1 },
            { "name": "aggregate", "type": "string", "pk": 1 },
            { "name": "percent_used_capacity", "type": "integer", "pk": 0 },
            { "name": "size_available", "type": "integer", "pk": 0 } ]
     records: "{{ aggr_list }}"
     register: db_info
     when: aggr_list is defined
```
	 
The first time the module is called the `db` parameter is omitted an so the module creates a new db file returned in the `db_info` variable. The `table` parameter specifies the table name to be created in the DB. The `structure` parameter defines the schema of the table (column name and type and if it is a primary key). Finally the `records` parameter provides a list of table row entries to fill the table.

```
- name: Store Volume Info in DB
  fill_sql_db:
     db: "{{ db_info.embedded_db | default(omit, true) }}"
     table: "volume"
     structure: >
          [ { "name": "cluster", "type": "string", "pk": 1 },
            { "name": "svm", "type": "string", "pk": 1 },
            { "name": "volume", "type": "string", "pk": 1 },
            { "name": "size", "type": "integer", "pk": 0 },
            { "name": "size_available", "type": "integer", "pk": 0 } ]
     records: "{{ vol_list }}"
     register: db_info
     when: aggr_list is defined
```

The second time the module is called the `db` parameter is set with the value of DB file created during the previous call. A new table is created and filled in the same embedded DB file. We can add and fill as many tables as needed.

When all needed environment information are collected in the DB, we can run our complex criteria queries:

```
- name: Request for a Suitable Volume
  select_sql_db:
     db: "{{ db_info.embedded_db }}"
     query: >
                 SELECT svm.cluster,volume.svm,volume.name
                 FROM volume
                 JOIN svm ON svm.name = volume.svm
                 LEFT JOIN snapmirror_destination AS sm
                    ON sm.src_path = volume.svm || ':' || volume.name
                    AND sm.dst_svm LIKE '%svmbck%'
                 WHERE volume.name NOT LIKE '%00'
                 AND (
                   ('{{ is_res }}' = 'true' AND volume.name REGEXP '^RES_.+$')
                   OR
                   ('{{ is_res }}' = 'false' AND volume.name NOT REGEXP '^RES_.+$')
                 )
                 AND volume.svm IN ({{ quoted_svm_list }})
                 AND (
                   ('{{ is_bck }}' = 'true' AND ( sm.src_svm IS NOT NULL OR volume.comment LIKE '%WITH_BACKUP%'))
                   OR
                   ('{{ is_bck }}' = 'false' AND sm.src_svm IS NULL AND volume.comment NOT LIKE '%WITH_BACKUP%')
                 )
                 ORDER BY volume.available DESC
                 LIMIT 1
  register: selected_volume
  when: db_info is defined
```

The `db` parameter references the embedded DB previously created and filled. The `query` parameter defines the SQL query to run and the result will be stored in the `selected_volume` variable.

After running all the needed selection SQL queries the embedded DB can be deleted:

```
- name: Remove embedded DB
  fill_sql_db:
     state: absent
     db: "{{ db_info.embedded_db }}"
  ignore_errors: yes
  when: db_info is defined
```

Hope that can help.
