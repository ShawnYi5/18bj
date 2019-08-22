from business_logic.storage_tree import tree
from business_logic.storage_tree import tree_apply

from data_access.db_operation import journal
from data_access import models as m


class CreateTree(object):
    """创建完整树(虚拟节点+真实节点)"""

    def __init__(self, tree_ident):
        self.tree_ident = tree_ident

    def generate_storage_tree(self):
        return tree.DiskSnapshotStorageTree.create_tree_inst(self.tree_ident)

    def query_unconsumed_create_journals(self):
        return journal.UnconsumedJournalsQuery(self.tree_ident, m.Journal.JOURNAL_CREATE_TYPES).journal_dicts()

    def generate_complete_tree(self):
        storage_tree = self.generate_storage_tree()
        unconsumed_create_journals = self.query_unconsumed_create_journals()
        return tree_apply.ApplyInTree(storage_tree, unconsumed_create_journals).apply()


class FetchNodes(object):
    """从ident节点回溯到根，获取树对象中相关联的节点列表"""

    def __init__(self, tree_obj, ident):
        self.tree_obj = tree_obj
        self.ident = ident

    def get_node_of_ident(self):
        return self.tree_obj.get_node_by_ident(self.ident)

    def fetch(self):
        node_of_ident = self.get_node_of_ident()
        return self._find_node_list_(node_of_ident)

    @staticmethod
    def _find_node_list_(node):
        """从叶子向根寻找，获取树上相关联的节点列表"""

        node_list = list()

        def _get_node_list(_node):
            """递归获取父节点，插入到node_list"""

            if not _node.parent:
                return _node
            node_list.insert(0, _node.parent)
            return _get_node_list(_node.parent)

        if node.parent is None:
            node_list.insert(0, node)

        else:
            node_list.insert(0, node)
            _get_node_list(node)

        return node_list


class GetStorageFromNode(object):
    """获取节点列表中真实存储节点对象"""

    def __init__(self, nodes):
        self.nodes = nodes

    def get(self):
        for node in self.nodes:
            if isinstance(node, tree.NodeFromJournal):
                self.nodes.remove(node)

        return [node.storage for node in self.nodes]


class FetchStorageForChain(object):
    def __init__(self, tree_ident, storage_ident):
        self.tree_ident = tree_ident
        self.storage_ident = storage_ident

    def create_complete_tree(self):
        return CreateTree(self.tree_ident).generate_complete_tree()

    def fetch_nodes_for_chain(self):
        complete_tree = self.create_complete_tree()
        return FetchNodes(complete_tree, self.storage_ident).fetch()

    def fetch(self):
        nodes_for_chain = self.fetch_nodes_for_chain()
        return GetStorageFromNode(nodes_for_chain).get()
