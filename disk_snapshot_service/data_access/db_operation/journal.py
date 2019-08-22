import json

from basic_library import xfunctions as xf
from data_access import models as m
from data_access.db_operation import session


class JournalNotExist(Exception):
    pass


class JournalQuery(object):
    """获取 Journal"""

    def __init__(self, token):
        self.token = token

    def get_obj(self):
        """获取数据

        :raise
            JournalNotExist
        """

        with session.SessionForRead() as s:
            obj = s.query(m.Journal).filter(m.Journal.token == self.token).first()
            if not obj:
                raise JournalNotExist(f'not exist token : {self.token}')
            return obj

    def get_obj_dict(self) -> dict:
        """获取数据字典

        :raise
            JournalNotExist
        """

        return self.get_obj().obj_to_dict()

    def get_inst(self):
        """获取实例

        :raise
            JournalNotExist
        """

        return generate_create_params_dict(self.get_obj_dict())

    @staticmethod
    def get_inst_from_journal_obj(journal_obj):
        """获取journal_obj的inst"""

        if journal_obj:
            return generate_create_params_dict(journal_obj)
        raise JournalNotExist(f'not exist journal')


class UpdateJournal(object):
    def __init__(self, token, column_name, new_data, session_=session.SessionForReadWrite()):
        self.token = token
        self.column_name = column_name  # 更新的字段名
        self.new_data = new_data  # 更新的数据
        self.session = session_

    def update(self):
        with session.SessionForReadWrite() as s:
            s.query(m.Journal).filter(m.Journal.token == self.token).update({self.column_name: self.new_data})
            s.commit()


class ConsumeJournalsQuery(object):
    """批量消费Journals"""

    def __init__(self, tokens: list, session_=session.SessionWithTrans()):
        self.tokens = tokens
        self.session = session_

    def consume(self):
        with self.session as s:
            for token in self.tokens:
                journal = s.query(m.Journal).filter(m.Journal.token == token).first()
                journal.consumed_timestamp = xf.current_timestamp()


class UnconsumedJournalsQuery(object):
    """获取未消费的Journals"""

    def __init__(self, tree_ident=None, journal_types=None):
        self.tree_ident = tree_ident
        self.journal_types = journal_types

    def query_objs(self):
        """获取创建日志"""

        with session.SessionForRead() as s:
            q = s.query(m.Journal).filter(m.Journal.consumed_timestamp.is_(None))
            if self.tree_ident:
                q = q.filter(m.Journal.tree_ident == self.tree_ident)
            if self.journal_types:
                q = q.filter(m.Journal.operation_type.in_(self.journal_types))
            return q.order_by(m.Journal.id).all()

    def journal_dicts(self):
        """objs to dicts"""

        return [obj.obj_to_dict() for obj in self.query_objs()]

    def query_insts(self):
        """获取创建实例"""

        result = list()
        for obj in self.journal_dicts():
            result.append(generate_create_params_dict(obj))
        return result


def generate_create_params_dict(journal_dict: dict) -> dict:
    assert journal_dict['operation_type'] in m.Journal.JOURNAL_CREATE_TYPES, \
        f'journal type NOT JOURNAL_CREATE_TYPES {journal_dict["id"]}'
    return json.loads(journal_dict['operation_str']) 


# class OperationInJournal(object):
#     """获取操作信息基类"""
#
#     def __init__(self, journal_obj):
#         self.journal_obj = journal_obj
#         self._operation_cache = None
#
#     @property
#     def operation(self) -> dict:
#         if self._operation_cache is None:
#             self._operation_cache = json.loads(self.journal_obj.operation_str)
#         return self._operation_cache
#
#     @property
#     def token(self):
#         return self.journal_obj.token
#
#
# class NormalCreateInJournal(OperationInJournal):
#     """创建普通备份点（QCOW and CDP）信息"""
#
#     def __init__(self, journal_obj):
#         super(NormalCreateInJournal, self).__init__(journal_obj)
#
#     @property
#     def parent_ident(self):
#         return self.operation['parent_ident']
#
#     @property
#     def parent_timestamp(self):
#         return self.operation['parent_timestamp']
#
#     @property
#     def new_ident(self):
#         return self.operation['new_ident']
#
#     @property
#     def new_type(self):
#         return self.operation['new_type']
#
#     @property
#     def new_storage_folder(self):
#         return self.operation['new_storage_folder']
#
#     @property
#     def new_disk_bytes(self):
#         return self.operation['new_disk_bytes']
#
#     @property
#     def new_hash_type(self):
#         return self.operation['new_hash_type']
#
#     def is_root(self):
#         if self.operation['parent_ident']:
#             return True
#         return False
#
#     def is_cdp(self):
#         if self.operation['new_type'] == 'cdp':
#             return True
#         return False
#
#
# class DestroyInJournal(OperationInJournal):
#     """删除备份点信息"""
#
#     def __init__(self, journal_obj):
#         super(DestroyInJournal, self).__init__(journal_obj)
#
#     @property
#     def idents(self):
#         return self.operation['idents']
#
#
# class CreateFromQcowInJournal(OperationInJournal):
#     """源为QCOW备份点的创建信息"""
#
#     def __init__(self, journal_obj):
#         super(CreateFromQcowInJournal, self).__init__(journal_obj)
#
#     @property
#     def source_ident(self):
#         return self.operation['source_ident']
#
#     @property
#     def new_ident(self):
#         return self.operation['new_ident']
#
#
# class CreateFromCdpInJournal(OperationInJournal):
#     """源为CDP备份点的创建信息"""
#
#     def __init__(self, journal_obj):
#         super(CreateFromCdpInJournal, self).__init__(journal_obj)
#
#     @property
#     def source_idents(self):
#         return self.operation['source_idents']
#
#     @property
#     def new_ident(self):
#         return self.operation['new_ident']
#
#
# _journal_sub_class = {
#     m.Journal.TYPE_NORMAL_CREATE: NormalCreateInJournal,
#     m.Journal.TYPE_DESTROY: DestroyInJournal,
#     m.Journal.TYPE_CREATE_FROM_QCOW: CreateFromQcowInJournal,
#     m.Journal.TYPE_CREATE_FROM_CDP: CreateFromCdpInJournal,
# }
#
#
# # 表驱动
# def generate_journal_inst(journal_obj):
#     if journal_obj:
#         return _journal_sub_class[journal_obj.operation_type](journal_obj)
#     else:
#         return None


class NormalCreateInJournal(object):
    """NormalCreate类型创建通过journal传递的参数"""

    def __init__(self, normal_create_inst):
        self.normal_create_inst = normal_create_inst

    @property
    def parent_ident(self):
        return self.normal_create_inst['parent_ident']

    @property
    def parent_timestamp(self):
        return self.normal_create_inst['parent_timestamp']

    @property
    def new_ident(self):
        return self.normal_create_inst['new_ident']

    @property
    def new_type(self):
        return self.normal_create_inst['new_type']

    @property
    def new_storage_folder(self):
        return self.normal_create_inst['new_storage_folder']

    @property
    def new_disk_bytes(self):
        return self.normal_create_inst['new_disk_bytes']

    @property
    def new_hash_type(self):
        return self.normal_create_inst['new_hash_type']

    def is_root(self):
        if self.normal_create_inst['parent_ident']:
            return True
        return False

    def is_cdp(self):
        if self.normal_create_inst['new_type'] == 'cdp':
            return True
        return False
