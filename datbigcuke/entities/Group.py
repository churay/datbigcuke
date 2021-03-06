"""Module for Group entity."""

__author__ = 'Eunsoo Roh'
__copyright__ = 'Copyright 2014 Bigdatcuke Project'
__email__ = 'roh7@illinois.edu'


from datbigcuke.entities.AbstractEntity import AbstractEntity
import os
import hashlib


class Group(AbstractEntity):
    _ATTRIB_TO_DATA = {
        '_id' : 'id',
        '_name' : 'name',
        '_description' : 'description',
        '_type' : 'type',
        '_maintainerId' : 'maintainerId',
        '_academic_entity_id' : 'academic_entity_id',
        '_academic_entity_type' : 'academic_entity_type',
    }

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def maintainerId(self):
        return self._maintainerId

    @maintainerId.setter
    def maintainerId(self, value):
        self._maintainerId = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def subgroups(self):
        if self._subgroups is None:
            self._subgroups = []
        return self._subgroups

    @subgroups.setter
    def subgroups(self, value):
        self._subgroups = value

    @property
    def academic_entity_id(self):
        return self._academic_entity_id

    @academic_entity_id.setter
    def academic_entity_id(self, value):
        self._academic_entity_id = value

    @property
    def academic_entity_type(self):
        return self._academic_entity_type

    def validate(self):
        # TODO(roh7): implement proper validation
        return True
