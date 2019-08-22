from basic_library import xlogging

from business_logic import storage_action as sc
from business_logic import journal_manager as jm
from business_logic import handle_pool as hp
from business_logic.storage_tree import tree as st
from business_logic import storage_action as sa
from business_logic import storage_chain as sc
from business_logic import storage_reference_manager as srm
from data_access import models as m

_logger = xlogging.getLogger(__name__)

storage_reference_manager = srm.StorageReferenceManager()
journal_manager = jm.JournalManager.get_journal_manager()
handle_manager = hp.HandleManager()


class CreateDiskSnapshotStorage(object):
    """创建磁盘快照存储"""

    def __init__(self, handle: str, token: str, trace_debug: str, caller_pid: int):
        self.token = token
        self.caller_pid = caller_pid
        self.trace_debug = trace_debug
        self.handle = handle

        self.journal_obj = None  # 当前日志对象
        self.normal_create_inst = None  # 当前普通创建实例
        self.tree_ident = None  # 从当前日志对象获取的树标志符

        self.name = self  # 当前接口的行为描述信息
        self.journal_manager = journal_manager
        self.storage_reference_manager = storage_reference_manager
        self.handle_manager = handle_manager
        self.trace_msg = 'create new_storage:{},PID:{},trace_debug:{},handle:{}'.format(self._new_ident,
                                                                                        caller_pid,
                                                                                        trace_debug,
                                                                                        handle
                                                                                        )

    def __str__(self):
        return f'query chain for creating new snapshot storage : <{self.normal_create_inst.new_ident}>'

    def _generate_raw_flag(self) -> str:
        """生成action需要的flag"""

        return sa.DiskSnapshotAction.generate_flag(self.trace_debug, self.caller_pid)

    @property
    def _disk_bytes(self):

        return self.normal_create_inst.new_disk_bytes

    @property
    def _new_ident(self) -> str:
        """快照节点ident"""

        return self.normal_create_inst.new_ident

    @property
    def _new_disk_bytes(self) -> int:
        """磁盘快照存储所描述的磁盘大小"""

        return self.normal_create_inst.new_disk_bytes

    @property
    def _is_cdp_type(self) -> bool:
        """是否是CDP磁盘快照类型"""

        if self.normal_create_inst.new_type == 'CDP':
            return True
        return False

    @property
    def _is_qcow_type(self) -> bool:

        if self.normal_create_inst.new_type == 'QCOW':
            return True
        return False

    @property
    def _is_root_node(self) -> bool:
        """是否是根节点"""

        if self.normal_create_inst.parent_ident:
            return False
        return True

    @property
    def normal_create_journal_obj_of_parent(self):
        """获取父节为普通创建时的日志对象

        :return: parent_journal_obj or None
        """

        assert not self._is_root_node
        parent_ident = self.normal_create_inst.parent_ident
        unconsumed_normal_create_journals = self.journal_manager.query_unconsumed_normal_create_journals(
            self.tree_ident)

        if unconsumed_normal_create_journals:
            parent_journal_obj = None
            for journal_obj in unconsumed_normal_create_journals:
                inst = self.journal_manager.get_inst(journal_obj)
                ident = inst.new_ident
                if ident == parent_ident:
                    parent_journal_obj = journal_obj
                else:
                    parent_journal_obj = None
            return parent_journal_obj

    def update_journal(self):
        """如果父为普通创建，则更新父日志表的children字段

        :remark:
            更新规则：将本次创建的 ident 添加到父日志表的 children 字段中
        """

        normal_create_journal_obj_of_parent = self.normal_create_journal_obj_of_parent
        if normal_create_journal_obj_of_parent:
            children_idents = str(list(normal_create_journal_obj_of_parent['children_idents']).append(
                self.normal_create_inst.new_ident))
            self.journal_manager.update_children(normal_create_journal_obj_of_parent, children_idents)

    @property
    def _folder(self):
        """文件路径"""

        return self.normal_create_inst.new_storage_folder

    @staticmethod
    def _parent_storage_obj(storage_obj_list_for_chain):
        """当前普通创建依赖的真实存储节点"""

        return storage_obj_list_for_chain[-1] if storage_obj_list_for_chain else None

    @staticmethod
    def _acquire_storage_chain(storage_chain, new_storage_obj):
        """申请快照存储链资源引用"""

        storage_chain.insert_tail(new_storage_obj)
        return storage_chain.acquire()

    def _create_new_storage_obj(self, image_path, parent_storage_obj):
        """创建新快照的存储对象并返回该对象(dict)"""

        return db.SnapshotStorageQuery.create_snapshot_storage(
            self.normal_create_inst,
            image_path,
            parent_storage_obj,
            self.tree_ident
        )

    def update_parent_of_children(self):
        """更新当前普通创建所关联子节点的parent_ident"""

        children_idents = list(self.journal_obj['children_idents'])
        new_ident = self.normal_create_inst.new_ident
        if children_idents:
            for child_ident in children_idents:
                db.SnapshotStorageQuery.update_parent_ident(new_ident, child_ident)

    @property
    def _nodes_for_chain(self):
        """生成链所依赖节点的有序列表(包含真实节点和虚拟节点，根节点index为 0)"""

        # 创建实例列表(有序、未消费)，更新消费状态
        create_insts = self.journal_manager.query_unconsumed_create_insts(self.tree_ident)

        # 实例化树对象
        storage_tree = st.DiskSnapshotStorageTree.create_tree_inst(self.tree_ident)

        # 创建实例列表应用到树，得到完整的树
        complete_tree = st.DiskSnapshotStorageTree.apply_create_insts(storage_tree, create_insts)

        # 生成链所依赖节点的有序列表(包含真实节点和虚拟节点，根节点index为 0)
        node_list_for_chain = st.DiskSnapshotStorageTree.get_node_list_for_chain(
            complete_tree,
            self.normal_create_inst)

        return node_list_for_chain

    def _generate_handle(self):
        with self.journal_manager.get_locker(self.trace_msg):

            # 当前日志对象
            self.journal_obj = self.journal_manager.get_journal_obj(self.token)
            assert self.journal_obj['operation_type'] == m.Journal.TYPE_NORMAL_CREATE

            self.normal_create_inst = self.journal_manager.get_inst(self.journal_obj)  # 当前普通创建实例
            self.tree_ident = self.journal_manager.get_tree_ident(self.journal_obj)  # 从当前日志对象获取的树标志符

            with st.DiskSnapshotStorageTree.get_locker(self.trace_msg):

                if self._is_root_node:
                    assert self._is_qcow_type
                    image_path = sa.NewRootQcowPath(self.normal_create_inst).path()

                    parent_storage_obj = None  # 当前普通创建依赖的真实父节点不存在
                    new_storage_obj = self._create_new_storage_obj(image_path, parent_storage_obj)
                    storage_chain = st.DiskSnapshotStorageTree.generate_chain_for_rw(
                        create_inst=self.normal_create_inst,
                        storage_reference_manager=storage_reference_manager,
                        caller_name=self.name
                    )

                else:
                    # 生成链所依赖的有序节点列表
                    node_list_for_chain = self._nodes_for_chain

                    # 当前普通创建依赖的真实存储节点列表
                    storage_obj_list_for_chain = st.DiskSnapshotStorageTree.get_storage_obj_list(
                        node_list_for_chain)

                    # 当前普通创建依赖的真实父节点
                    parent_storage_obj = self._parent_storage_obj(storage_obj_list_for_chain)

                    storage_chain = st.DiskSnapshotStorageTree.generate_chain_for_rw(
                        create_inst=self.normal_create_inst,
                        storage_obj_list=storage_obj_list_for_chain,
                        storage_reference_manager=storage_reference_manager,
                        caller_name=self.name
                    )

                    if self._is_cdp_type:
                        image_path = sa.NewCdpImagePath(self.normal_create_inst).path()

                    else:
                        image_path = sa.NewQcowPathWithParent(self.normal_create_inst,
                                                              storage_obj_list_for_chain[-1]).path()

                    new_storage_obj = self._create_new_storage_obj(image_path, parent_storage_obj)

                # 更新当前普通创建所关联子节点的parent_ident
                self.update_parent_of_children()

                # 如果当前普通创建的父为普通创建，则更新父日志表的children字段
                self.update_parent_children()

                acquired_storage_chain = self._acquire_storage_chain(storage_chain, new_storage_obj)
                return self.handle_manager.generate_write_handle(acquired_storage_chain, self.handle)

    def execute(self):
        handle_inst = self._generate_handle()

        # flag 为不超过255字符的字符串，表明调用者的身份，格式为 "PiD十六进制pid 模块名|创建原因"
        raw_flag = self._generate_raw_flag()

        # long create(ImageSnapshotIdent ident, ImageSnapshotIdents lastSnapshot, long diskByteSize, string flag)
        handle_inst.raw_handle, handle_inst.ice_endpoint = \
            sa.DiskSnapshotAction.create_disk_snapshot(handle_inst.storage_chain, self._disk_bytes, raw_flag)

        return {'raw_handle': handle_inst.raw_handle, 'ice_endpoint': handle_inst.ice_endpoint}


class CloseDiskSnapshotStorage(object):

    def __init__(self, handle: str):
        self.handle = handle

    def execute(self):
        handle_inst = self.handle_manager.pop(self.handle)
        if not handle_inst:
            raise 'xxxxx'

        # if create_handle:
        #     pass
        # else: # open_handle
        #     pass

        sa.DiskSnapshotAction.close_disk_snapshot(handle_inst.raw_handle, handle_inst.ice_endpoint)

        handle_inst.storage_chain.release()


class OpenDiskSnapshotStorage(object):

    def __init__(self, storage_ident: str, tree_ident, caller_pid: int, trace_debug: str, handle: str, timestamp=None):
        self.trace_debug = trace_debug
        self.tree_ident = tree_ident
        self.caller_pid = caller_pid
        self.timestamp = timestamp
        self.storage_ident = storage_ident

        self.journal_manager = journal_manager
        self.trace_msg = 'create - '.format(storage_ident, caller_pid, trace_debug, handle)

    def _generate_raw_flag(self) -> str:
        """生成action需要的flag"""

        return sa.DiskSnapshotAction.generate_flag(self.trace_debug, self.caller_pid)

    def _generate_handle(self):
        with self.journal_manager.get_locker(self.trace_msg):
            self.normal_create_info, tree_ident = self.journal_manager.fetch_normal_create_inst(self.storage_ident)
            journal_infos = self.journal_manager.fetch_infos(tree_ident)

            with st.DiskSnapshotStorageTree.get_locker(self.trace_msg):
                storage_tree = st.DiskSnapshotStorageTree.create_tree_inst(tree_ident)
                storage_tree.apply_create_infos(journal_infos)

                storage_chain = storage_tree.generate_chain_for_read(
                    self.storage_ident, self.timestamp, sc.StorageChainForRead).acquire()

                return handle_manager.generate_read_handle(storage_chain, self)

    def execute(self):
        handle_inst = self._generate_handle()

        raw_flag = self._generate_raw_flag()

        # long open(ImageSnapshotIdents ident, string flag)
        # flag 为不超过255字符的字符串，表明调用者的身份，格式为 "PiD十六进制pid 模块名|打开原因"
        handle_inst.raw_handle, handle_inst.ice_endpoint = sa.DiskSnapshotAction.open_disk_snapshot(
            handle_inst.storage_chain,
            raw_flag
        )

        return {'raw_handle': handle_inst.raw_handle, 'ice_endpoint': handle_inst.ice_endpoint}
