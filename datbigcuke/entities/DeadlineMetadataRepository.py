"""Module for User repository.

DeadlineMetadataRepository offers access and persistence of DeadlineMetadata objects.
"""

__author__ = 'Kyle Nusbaum'
__copyright__ = 'Copyright 2014 Bigdatcuke Project'
__email__ = 'kjnusba2@illinois.edu'


from datbigcuke.entities.DeadlineMetadata import DeadlineMetadata
from datbigcuke.entities.AbstractRepository import AbstractRepository
import datbigcuke.db
import operator


class DeadlineMetadataRepository(AbstractRepository):

    def __init__(self):
        super(DeadlineMetadataRepository, self).__init__(DeadlineMetadata)

    def persist(self, deadlineMeta):
        super(DeadlineMetadataRepository, self).persist(deadlineMeta)

        delta = deadlineMeta.get_delta()
        if deadlineMeta.user_id is None or deadlineMeta.deadline_id is None or getattr(deadlineMeta, 'insert', False) == True:
            delta.pop('insert', None)
            with self._conn.cursor() as cursor:
                cursor.execute('INSERT INTO `deadline_metadata` '
                               '(`user_id`, `deadline_id`, `notes`)'
                               'VALUES (?,?,?)',(deadlineMeta.user_id, deadlineMeta.deadline_id, deadlineMeta.notes))
        else:
            if delta:
                keys = delta.keys()
                args = list(delta.values())
                print "args:", args
                args.append(deadlineMeta.user_id)
                args.append(deadlineMeta.deadline_id)
                query = ','.join('`{}`=?'.format(k) for k in keys)
                print "query:", query
                with self._conn.cursor() as cursor:
                    cursor.execute('UPDATE `deadline_metadata` '
                                   'SET {} WHERE `user_id`=? AND `deadline_id`=?'.format(query),
                                   args)

    def fetch(self, deadline_id):
        deadline_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `user_id`, `deadline_id`, `notes` '
                           'FROM `deadline_metadata` '
                           'WHERE `deadline_id`=?', (deadline_id,))
            for result in self._fetch_all_dict(cursor):
                deadline_list.append(self._create_entity(data=result))
            
        return deadline_list

    def fetch_user(self, user_id):
        deadline_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `user_id`, `deadline_id`, `notes` '
                           'FROM `deadline_metadata` '
                           'WHERE `user_id`=?', (user_id,))
        for result in self._fetch_all_dict(cursor):
            deadline_list.append(self._create_entity(data=result))
            
        return deadline_list

    def _fetch_deadline_meta(self, cursor):
        result = self._fetch_dict(cursor)
        if result is not None:
            return self._create_entity(data=result)
