import random

from data_access.db_operation import journal
from data_access.db_operation import storage


class TestJournalQuery:

    def test_get_obj(self):
        """测试：获取日志数据库对象"""

        token = 't1'
        journal_query = journal.JournalQuery(token)
        assert journal_query.get_obj().tree_ident == 'tree_ident_1'

    def test_get_inst(self):
        """测试：获取创建实例(operation_str字段内容的字典格式)"""

        token = 't1'
        journal_query = journal.JournalQuery(token)
        assert journal_query.get_inst()['new_ident'] == 'new_ident_1'

    def test_get_obj_dict(self):
        """测试：获取日志对象的字典格式"""

        token = 't1'
        journal_query = journal.JournalQuery(token)
        assert journal_query.get_obj_dict()['id'] == 1

    def test_get_inst_from_journal(self):
        """测试：获取参数journal_dict的创建实例(operation_str字段内容的字典格式)"""

        token = 't1'
        journal_obj = journal.JournalQuery(token).get_obj_dict()
        inst = journal.JournalQuery.get_inst_from_journal_obj(journal_obj)
        assert inst['new_storage_folder'] == 'folder1'


class TestConsumeJournalsQuery:

    @staticmethod
    def get_consumed_timestamp(token):
        return journal.JournalQuery(token).get_obj_dict()['consumed_timestamp']

    def test_consume(self):
        """测试：消费日志"""
        tokens = ['t1', 't2']

        # 消费前
        consumed_timestamp_1 = self.get_consumed_timestamp('t1')

        # 消费后
        journal.ConsumeJournalsQuery(tokens).consume()
        consumed_timestamp_2 = self.get_consumed_timestamp('t1')

        # 更新前后字段数据不同
        assert consumed_timestamp_2
        assert consumed_timestamp_2 != consumed_timestamp_1

        # # 恢复数据库被修改的字段
        journal.UpdateJournal('t1', 'consumed_timestamp', None).update()


class TestUpdate:

    @staticmethod
    def get_children_idents(token):
        return journal.JournalQuery(token).get_obj_dict()['children_idents']

    def test_update(self):
        """测试：更新数据"""

        token = 't2'
        column_name = 'children_idents'
        new_data = f'[aaa_{random.randint(1, 100)}, bbb_{random.randint(1, 100)}]'

        # 更新前
        children_idents_1 = self.get_children_idents(token)

        # 更新后
        journal.UpdateJournal(token, column_name, new_data).update()
        children_idents_2 = self.get_children_idents(token)

        # 更新前后字段数据不同
        assert children_idents_1 != children_idents_2

        # 恢复数据库被修改的字段
        journal.UpdateJournal(token, 'children_idents', children_idents_1).update()


class TestUnconsumedJournalsQuery:

    def test_unconsumed_journals_query(self):
        """测试：获取未消费日志信息"""

        q = journal.UnconsumedJournalsQuery().journal_dicts()
        assert q[0]['id'] == 1


class TestSnapshotStorageTreeQuery:

    def test_query(self):
        """测试：磁盘快照表查询"""

        tree_ident = 'tree_ident_1'
        q = storage.SnapshotStorageTreeQuery(tree_ident).valid_obj_dicts()
        assert len(q) == 3
        assert {obj['ident'] for obj in q} == {'ident_1', 'ident_2', 'ident_3'}


class TestUpdateSnapshotStorage:

    def test_update(self):
        """测试：更新快照表"""

        ident = 'ident_5'
        column_name = 'file_level_deduplication'
        new_data = 1

        # 查询更新前的数据
        q1 = storage.SnapshotStorageQuery(ident).query().file_level_deduplication
        assert not q1

        # 更新
        storage.SnapshotStorageUpdate(ident, column_name, new_data).update()
        q2 = storage.SnapshotStorageQuery(ident).query().file_level_deduplication
        assert q2

        # 恢复被修改的字段
        storage.SnapshotStorageUpdate(ident, column_name, None).update()


class TestSnapshotStorageAdd:

    def test_add(self):
        """测试：创建新快照

        :remark:
            storage_ident = 'ident_test'
            parent_ident = 'ident_5'
            parent_timestamp = 101010
            storage_type = 'c'
            disk_bytes = 1024
            status = 'c'
            image_path = '/zzz/sss'
            tree_ident = 'tree_ident_2'
        """

        # 创建
        params = ('ident_test', 'ident_5', 101010, 'c', 1024, 'c', '/zzz/sss', 'tree_ident_2')
        storage.SnapshotStorageAdd(*params).add()
        assert storage.SnapshotStorageQuery('ident_test').query()

        # 恢复数据库
        storage.SnapshotStorageDrop('ident_test').drop()
