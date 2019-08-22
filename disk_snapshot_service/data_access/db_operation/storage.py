from data_access.db_operation import session
from data_access import models as m


class SnapshotStorageTreeQuery(object):
    """获取 SnapshotStorageTree"""

    def __init__(self, tree_ident):
        self.tree_ident = tree_ident

    def query_valid_objs(self):
        """获取有效的数据"""

        with session.SessionForRead() as s:
            objs = (s.query(m.SnapshotStorage)
                    .filter(m.SnapshotStorage.tree_ident == self.tree_ident)
                    .filter(m.SnapshotStorage.status.notin_(m.SnapshotStorage.INVALID_STORAGE_STATUS))
                    .all()
                    )
            return objs

    def valid_obj_dicts(self):
        """有效数据字典对象集"""

        return [obj.obj_to_dict() for obj in self.query_valid_objs()]


class SnapshotStorageAdd(object):
    def __init__(self, storage_ident, parent_ident, parent_timestamp, storage_type, disk_bytes, status, image_path,
                 tree_ident):
        self.storage_ident = storage_ident
        self.parent_ident = parent_ident
        self.parent_timestamp = parent_timestamp
        self.type = storage_type
        self.disk_bytes = disk_bytes
        self.status = status
        self.image_path = image_path
        self.tree_ident = tree_ident

    def add(self):
        new_storage_info = m.SnapshotStorage(
            ident=self.storage_ident,
            parent_ident=self.parent_ident,
            parent_timestamp=self.parent_timestamp,
            type=self.type,
            disk_bytes=self.disk_bytes,
            status=self.status,
            image_path=self.image_path,
            tree_ident=self.tree_ident,
        )

        with session.SessionForReadWrite() as s:
            s.add(new_storage_info)
            s.commit()
            new_storage_obj = (s.query(m.SnapshotStorage)
                               .filter(m.SnapshotStorage.ident == self.storage_ident)
                               .first())
            return new_storage_obj.obj_to_dict()


class SnapshotStorageUpdate(object):
    def __init__(self, ident, column_name, new_data):
        self.ident = ident
        self.column_name = column_name  # 更新的字段名
        self.new_data = new_data  # 更新的数据

    def update(self):
        with session.SessionForReadWrite() as s:
            s.query(m.SnapshotStorage).filter(m.SnapshotStorage.ident == self.ident).update(
                {self.column_name: self.new_data})
            s.commit()


class SnapshotStorageDrop(object):
    def __init__(self, storage_ident):
        self.storage_ident = storage_ident

    def drop(self):
        with session.SessionForRead() as s:
            q = s.query(m.SnapshotStorage).filter(m.SnapshotStorage.ident == self.storage_ident).first()
            s.delete(q)
            s.commit()


class SnapshotStorageQuery(object):
    def __init__(self, storage_ident):
        self.storage_ident = storage_ident

    def query(self):
        with session.SessionForRead() as s:
            q = s.query(m.SnapshotStorage).filter(m.SnapshotStorage.ident == self.storage_ident).first()
            return q
