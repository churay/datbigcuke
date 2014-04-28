"""Module for Group repository.

GroupRepository offers access and persistence of Group objects.
"""

__author__ = 'Eunsoo Roh'
__copyright__ = 'Copyright 2014 Bigdatcuke Project'
__email__ = 'roh7@illinois.edu'

from datbigcuke.entities.UserRepository import UserRepository
from datbigcuke.entities.User import User
from datbigcuke.entities.Group import Group
from datbigcuke.entities.AbstractRepository import AbstractRepository
import datbigcuke.db
import operator

# @TODO(halstea2) Add 'remove' method for deleting a user.

class GroupRepository(AbstractRepository):

    def __init__(self):
        super(GroupRepository, self).__init__(Group)

    def close(self):
        self._conn.close()

    def persist(self, group):
        super(GroupRepository, self).persist(group)

        delta = group.get_delta()
        delta.pop('id', None)  # make sure id does not exist
        if group.id is None:
            # new user object
            with self._conn.cursor() as cursor:
                cursor.execute('INSERT INTO `membership_entity` VALUES ()')
                # TODO(roh7): figure out whether it is worth using exception
                # i.e. is there a case this would be true where execute() does
                # not throw an exception itself?
                print type(delta['description'])
                print type(delta['type'])

                assert cursor.lastrowid != 0
                cursor.execute('INSERT INTO `group`'
                               '(`id`, `name`, `description`, `type`, `maintainerId`) '
                               'VALUES (?, ?, ?, ?, ?);',
                               (cursor.lastrowid, delta['name'],
                                delta['description'], delta['type'], delta['maintainerId']))
                
                cursor.execute('SELECT `id`, `name`, `description`, `type`, `maintainerId` '
                               'FROM `group` '
                               'WHERE `id`=LAST_INSERT_ID()')
                group = self._fetch_group(cursor)
                print "Just after assignment: " + str(group)

        else:
            # old user object
            if delta:
                assert 'id' not in delta
                keys = delta.keys()
                args = list(delta.values())
                args.append(group.id)
                query = ','.join('`{}`=?'.format(k) for k in keys)
                with self._conn.cursor() as cursor:
                    cursor.execute('UPDATE `group` '
                                   'SET {} WHERE `id`=?'.format(query),
                                   args)

        return group
            
    def fetch(self, group_id):
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `id`, `name`, `description`, `type`, `maintainerId` '
                           'FROM `group`'
                           'WHERE `id`=?', (group_id,))
            return self._fetch_group(cursor)

    def fetch_all(self):
        group_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `id`, `name`, `description`, `type`, `maintainerId` '
                           'FROM `group`')
            for result in self._fetch_all_dict(cursor):
                group_list.append(self._create_entity(data=result))

        return group_list

    def fetch_by_name(self, name):
        group_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `id`, `name`, `description`, `type`, `maintainerId` '
                           'FROM `group` '
                           'WHERE `name` =?', (name,))
            for result in self._fetch_all_dict(cursor):
                group_list.append(self._create_entity(data=result))

        return group_list

    def get_groups_of_user(self, user_id):
        group_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `g`.`id` AS `id`, `g`.`name` AS `name`,'
                           '`g`.`description` AS `description`, `g`.`type` AS `type`, `g`.`maintainerId` '
                           'FROM `group` AS `g`'
                           'JOIN `group_membership` AS `m`'
                           '    ON (`m`.`group_id` = `g`.`id`)'
                           'WHERE `m`.`member_id`=?', (user_id,))
            for result in self._fetch_all_dict(cursor):
                group_list.append(self._create_entity(data=result))

        return group_list

    # TODO(ciurej2): Improve this function to be less hacky.
    def get_groups_of_user_rec(self, user_id):
        user_group_list = self.get_groups_of_user(user_id)
        user_group_ids = { group.id : group for group in user_group_list }
        nonroot_group_ids = {}
        for user_group in user_group_list:
            user_group.subgroups = [ user_group_ids[ subgroup.id ] for subgroup in self.get_subgroups_of_group(user_group.id) if subgroup.id in user_group_ids ]

            for subgroup in user_group.subgroups:
                nonroot_group_ids[ subgroup.id ] = True

        for group in user_group_list:
            if not group.id in nonroot_group_ids:
                return [ group ]

        return []

    def get_supergroup_of_group(self, group_id):
        supergroup = None
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `g`.`id` AS `id`, `g`.`name` AS `name`,'
                           '`g`.`description` AS `description`, `g`.`type` AS `type`, `g`.`maintainerId`'
                           'FROM `group` AS `gr`'
                           'JOIN `group_membership` AS `m`'
                           '    ON (`m`.`member_id` = `gr`.`id`)'
                           'JOIN `group` AS `g`'
                           '    ON (`g`.`id` = `m`.`group_id`)'
                           'WHERE `gr`.`id` =?', (group_id,))
            for result in self._fetch_all_dict(cursor):
                supergroup = self._create_entity(data=result)
                
        return supergroup
    
    def get_supergroup_list(self, group_id):
        supergroup = self.get_supergroup_of_group(group_id)
        if supergroup is None:
            return []
            
        suplist = self.get_supergroup_list(supergroup.id)
        suplist.append(supergroup)
        print suplist
        return suplist

    def get_subgroups_of_group(self, group_id):
        group_list = []
        with self._conn.cursor() as cursor:
            cursor.execute('SELECT `g`.`id` AS `id`, `g`.`name` AS `name`,'
                           '`g`.`description` AS `description`, `g`.`type` AS `type`, `g`.`maintainerId`'
                           'FROM `group` AS `gr`'
                           'JOIN `group_membership` AS `m`'
                           '    ON (`m`.`group_id` = `gr`.`id`)'
                           'JOIN `group` AS `g`'
                           '    ON (`g`.`id` = `m`.`member_id`)'
                           'WHERE `gr`.`id` =?', (group_id,))
            for result in self._fetch_all_dict(cursor):
                group_list.append(self._create_entity(data=result))
        
        return group_list

    def get_subgroups_of_group_rec(self, group_id):
        group_list = self.get_subgroups_of_group(group_id)
        for group in group_list:
            group.subgroups = self.get_subgroups_of_group_rec(group.id)
            
        return group_list

    def add_group_as_subgroup(self, group_id, subgroup_id):
        with self._conn.cursor() as cursor:
            cursor.execute('INSERT INTO `group_membership` (`group_id`, `member_id`)'
                           'VALUES (?,?)', (group_id, subgroup_id))
        
    def get_group_maintainer_rec(self, group):
        group.maintainer = UserRepository().fetch(group.maintainerId)
        print group.name
        for subgroup in group.subgroups:
            self.get_group_maintainer_rec(subgroup)
        
    def _fetch_group(self, cursor):
        result = self._fetch_dict(cursor)
        if result is not None:
            return self._create_entity(data=result)
