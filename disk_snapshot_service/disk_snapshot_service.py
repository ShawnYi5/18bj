from business_logic import handle_pool
from business_logic import journal_manager
from business_logic import storage_action
from business_logic import storage_reference_manager
from business_logic.storage_chain import chain
from business_logic.storage_chain import chain_operation
from business_logic.storage_tree import tree
from business_logic.storage_tree import tree_operation
from data_access import models as m
from data_access.db_operation import journal
from data_access.db_operation import storage

storage_reference_manager = storage_reference_manager.StorageReferenceManager()
journal_manager = journal_manager.JournalManager.get_journal_manager()
handle_manager = handle_pool.HandleManager()


class CreateDiskSnapshotStorage(object):
    """创建磁盘快照存储"""

    def __init__(self, handle: str, token: str, trace_debug: str, caller_pid: int):
        """
        :remark:
            禁止直接实例化使用，须使用 create_instance 创建实例
        """

        self._handle = handle
        self._token = token
        self._trace_debug = trace_debug
        self._caller_pid = caller_pid

        self._trace_msg = None

        self._journal_dict = None
        self._normal_create_params = None  # journal.NormalCreateInJournal

        self.journal_manager = journal_manager
        self.storage_reference_manager = storage_reference_manager
        self.handle_manager = handle_manager

    def init(self):
        self._journal_dict = self._consume_journal()
        self._normal_create_params = journal.NormalCreateInJournal(
            journal.generate_create_params_dict(self._journal_dict)
        )
        return self

    def __str__(self):
        return f'query chain for creating new snapshot storage : <{self._normal_create_params.new_ident}>'

    @staticmethod
    def create_instance(handle: str, token: str, trace_debug: str, caller_pid: int):
        instance = CreateDiskSnapshotStorage(handle, token, trace_debug, caller_pid)
        return instance.init()

    @property
    def caller_name(self):
        return self.__str__()

    @property
    def trace_msg(self):
        if not self._trace_msg:
            self._trace_msg = (f'create new_storage:{self.new_ident},PID:{self._caller_pid},'
                               f'trace_debug:{self._trace_debug},_handle:{self._handle}')
        return self._trace_msg

    def _consume_journal(self) -> dict:
        """消费日志

        :return
            包含日志数据的dict
        """

        with self.journal_manager.get_locker(self.trace_msg):
            journal_dict = journal.JournalQuery(self._token).get_obj_dict()
            assert not journal_dict['consumed_timestamp'], f'journal has consumed {self._token}'
            assert journal_dict['operation_type'] == m.Journal.TYPE_NORMAL_CREATE, f'journal type NOT nc {self._token}'
            journal.ConsumeJournalsQuery([self._token, ]).consume()
            return journal_dict

    @property
    def disk_bytes(self) -> int:
        return self._normal_create_params.new_disk_bytes

    @property
    def new_ident(self) -> str:
        return self._normal_create_params.new_ident

    @property
    def is_root_node(self) -> bool:
        if self._normal_create_params.parent_ident:
            return False
        return True

    @property
    def tree_ident(self):
        return self._journal_dict['tree_ident']

    @property
    def parent_ident(self):
        return self._normal_create_params.parent_ident

    def _get_storages_for_chain(self, storage_tree):
        """生成chain所依赖的真实存储节点"""

        if self.is_root_node:
            return None
        else:
            nodes_for_chain = tree_operation.FetchNodes(self.tree_ident,
                                                        self._normal_create_params.parent_ident).fetch()
            storages_for_chain = tree_operation.GetStorageFromNode(nodes_for_chain).get()
            return storages_for_chain

    def _get_image_path(self, storages_for_chain):
        """获取当前普通创建的的文件路径

        :param storages_for_chain:
        :return:image_path
        """
        if self.is_root_node:
            image_path = storage_action.NewRootQcowPath(self._normal_create_params).path()
        else:
            if self._normal_create_params['new_type'] == 'cdp':
                image_path = storage_action.NewCdpImagePath(self._normal_create_params).path()
            else:
                image_path = storage_action.NewQcowPathWithParent(
                    self._normal_create_params, storages_for_chain[-1]).path()
        return image_path

    def _get_unconsumed_create_journals(self):
        """获取：所有未消费的/创建型 日志"""

        return journal.UnconsumedJournalsQuery(tree_ident=self.tree_ident,
                                               journal_types=m.Journal.JOURNAL_CREATE_TYPES).query_insts()

    def _get_relied_storage_obj(self, storages_for_chain):
        """当前创建依赖的真实存储节点"""

        if self.is_root_node:
            parent_storage_obj = None
        else:
            if storages_for_chain:
                parent_storage_obj = storages_for_chain[-1]
            else:
                parent_storage_obj = None
        return parent_storage_obj

    def _create_new_storage_obj(self, relied_storage, image_path):
        """创建新快照点，返回新创建的快照对象"""

        params = (self._normal_create_params['new_ident'],
                  relied_storage['parent_ident'] if relied_storage else None,
                  relied_storage['parent_timestamp'] if relied_storage else None,
                  self._normal_create_params['new_type'],
                  self._normal_create_params['new_disk_bytes'],
                  m.SnapshotStorage.STATUS_CREATING,
                  image_path,
                  self.tree_ident)
        return storage.SnapshotStorageAdd(*params).add()

    def _update_children_parent(self):
        """更新本次创建所关联的子节点的父ident

        :remark:
            该操作的原因：
                ... <— normal_create_1 <— normal_create_2 <— ...
                normal_create_1 为 normal_create_2 的父
                由于某些原因，normal_create_2 先于 normal_create_1 创建
                那么此时创建 normal_create_2 数据库对象时 parent_ident 不是 normal_create_1 的ident
                现在创建了 normal_create_1，应该将 normal_create_2 的 parent_ident 修改为 normal_create_1 的 ident

            更新步骤：
                1 获取当前日志对象的 children_idents 字段
                2 遍历 children_idents 调用快照更新接口，修改 parent_ident 字段
        """

        children_idents = list(self._journal_dict['children_idents'])
        new_ident = self.new_ident
        if children_idents:
            for child_ident in children_idents:
                storage.SnapshotStorageUpdate(child_ident, 'parent_ident', new_ident)

    def _update_parent_journal(self, unconsumed_create_journals):
        """更新父日志表的 children_idents 字段

        :remark:
             该操作的原因：
                ... <— create_inst <— normal_create_2 <— ...
                normal_create_2 的父 create_inst 尚未创建
                normal_create_2 先于 normal_create_2 创建
                create_inst 的创建日志中标记它的子 normal_create_2 先于它被创建

             操作步骤
                1 获取所有未消费的创建日志
                2 遍历创建日志，如果获取到当前创建的父日志，则更新父日志的 children_idents 字段
        """

        if unconsumed_create_journals:
            for j in unconsumed_create_journals:
                inst = journal.JournalQuery.get_inst_from_journal_obj(j)
                inst_ident = inst.new_ident
                if inst_ident == self.parent_ident:
                    parent_journal_token = j['token']
                    children_idents_of_parent_journal = j['children_idents']
                    new_data = str(list(children_idents_of_parent_journal).append(self.new_ident))
                    journal.UpdateJournal(parent_journal_token, 'children_idents', new_data)

    def _get_acquired_chain(self, storages_for_chain, new_storage_obj):
        """创建acquired_chain对象

        :remark:
            创建步骤：
                1 获取链所依赖的存储节点数据库对象 storages_for_chain
                2 创建本次创建行为的快照存储数据库对象 new_storage_obj
                3 将 new_storage_obj 添加到 storages_for_chain
                4 调用链的创建接口
        :return: acquired_chain
        """

        # new_storage_obj 添加到 storages_for_chain
        storages = storages_for_chain.append(new_storage_obj)
        parameter = (self.storage_reference_manager, self.caller_name, storages, chain.StorageChainForRW)
        return chain_operation.GenerateChain(*parameter).acquired_chain   # 生成chain,同时在reference_manager中记录record

    def _generate_handle(self):
        with self.journal_manager.get_locker(self.trace_msg):
            with tree.DiskSnapshotStorageTree.get_locker(self.trace_msg):
                storage_tree = tree_operation.CreateTree(self.tree_ident).generate_complete_tree()
                storages_for_chain = self._get_storages_for_chain(storage_tree)  # 链所依赖的真实存储节点
                image_path = self._get_image_path(storages_for_chain)  # 当前创建的备份路径
                relied_storage_obj = self._get_relied_storage_obj(storages_for_chain)  # 本次创建依赖的真实parent存储节点
                new_storage_obj = self._create_new_storage_obj(relied_storage_obj, image_path)  # 在storage表中创建新增点
                acquired_chain = self._get_acquired_chain(storages_for_chain, new_storage_obj)  # 生成链对象

                unconsumed_create_journals = self._get_unconsumed_create_journals()  # 未消费的创建日志
                self._update_parent_journal(unconsumed_create_journals)  # 更新父日志表的 children_idents 字段
                self._update_children_parent()  # 如果当前普通创建的父为普通创建，则更新父日志表的children字段

                return self.handle_manager.generate_write_handle(acquired_chain, self._handle)

    def _generate_raw_flag(self) -> str:
        return storage_action.DiskSnapshotAction.generate_flag(self._caller_pid, self._trace_debug)

    def execute(self):
        handle_inst = self._generate_handle()
        raw_flag = self._generate_raw_flag()
        handle_inst.raw_handle, handle_inst.ice_endpoint = (
            storage_action.DiskSnapshotAction.create_disk_snapshot(handle_inst.storage_chain,
                                                                   self._normal_create_params.new_disk_bytes,
                                                                   raw_flag))

        return {'raw_handle': handle_inst.raw_handle, 'ice_endpoint': handle_inst.ice_endpoint}


class CloseDiskSnapshotStorage(object):
    """关闭磁盘快照"""

    def __init__(self, handle: str):
        self.handle = handle
        self.handle_manager = handle_manager

    def execute(self):
        handle_inst = self.handle_manager.cache.pop(self.handle)
        if not handle_inst:
            raise HandleNotExist(f'_handle ({handle_inst}) not exists')

        # if create_handle:
        #     pass
        # else: # open_handle
        #     pass

        storage_action.DiskSnapshotAction.close_disk_snapshot(handle_inst.raw_handle, handle_inst.ice_endpoint)
        handle_inst.storage_chain.release()


class HandleNotExist(Exception):
    pass


class OpenDiskSnapshotStorage(object):
    def __init__(self, storage_ident: str, tree_ident, caller_pid: int, trace_debug: str, handle: str, timestamp=None):
        self.trace_debug = trace_debug
        self.tree_ident = tree_ident
        self.caller_pid = caller_pid
        self.handle = handle
        self.timestamp = timestamp
        self.storage_ident = storage_ident

        self.journal_manager = journal_manager
        self.handle_manager = handle_manager
        self.storage_reference_manager = storage_reference_manager

    def __str__(self):
        return f'query chain for opening snapshot storage : <{self.storage_ident}>'

    @property
    def caller_name(self):
        return self

    @property
    def _trace_msg(self) -> str:
        params = (self.storage_ident, self.caller_pid, self.trace_debug, self.handle)
        return 'open storage:{},PID:{},trace_debug:{},_handle:{}'.format(*params)

    def _generate_complete_tree(self):
        """生成完整树对象(真实存储节点 + 虚拟节点)

        :return:tree_obj
        """
        return tree_operation.CreateTree(self.tree_ident).generate_complete_tree()

    def parent_ident(self, complete_tree_obj):
        node = complete_tree_obj.get_node_by_ident(self.storage_ident)
        parent_node = node.parent
        parent_ident = complete_tree_obj.get_ident_by_node(parent_node)
        return parent_ident

    @property
    def _storages_for_chain(self):
        return tree_operation.FetchStorageForChain(self.tree_ident, self.parent_ident).fetch()

    def _acquired_chain(self):
        return chain_operation.GenerateChain(self.storage_reference_manager,
                                             self.caller_name,
                                             self._storages_for_chain,
                                             chain.StorageChainForRead,
                                             self.timestamp).acquired_chain

    def _generate_raw_flag(self) -> str:
        return storage_action.DiskSnapshotAction.generate_flag(self.trace_debug, self.caller_pid)

    def _generate_handle(self):
        with self.journal_manager.get_locker(self._trace_msg):
            with tree.DiskSnapshotStorageTree.get_locker(self._trace_msg):
                acquired_chain = self._acquired_chain()
                return self.handle_manager.generate_read_handle(acquired_chain, self.handle)

    def execute(self):
        handle_inst = self._generate_handle()
        raw_flag = self._generate_raw_flag()
        handle_inst.raw_handle, handle_inst.ice_endpoint = storage_action.DiskSnapshotAction.open_disk_snapshot(
            handle_inst.storage_chain, raw_flag)
        return {'raw_handle': handle_inst.raw_handle, 'ice_endpoint': handle_inst.ice_endpoint}
