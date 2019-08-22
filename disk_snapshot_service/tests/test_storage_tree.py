import pytest

from business_logic.storage_tree import tree_operation
from business_logic.storage_tree import tree


class TestCreateTree:

    def test_create_tree_1(self):
        """创建树实例

        :remark:
            真实节点：
                ident_1, ident_2, ident_3
            虚拟节点：
                new_ident_1:nc, new_ident_3:cfq
            树节点的从属关系：
                ident_1 <— ident_2 <— new_ident_3 <— ident_3 <— new_ident_1
        """

        tree_ident = 'tree_ident_1'

        # 快照存储节点生成树
        storage_tree = tree_operation.CreateTree(tree_ident).generate_storage_tree()
        storage_nodes = storage_tree.nodes_by_bfs
        storage_node_idents = [storage_tree.get_ident_by_node(node) for node in storage_nodes]
        assert storage_node_idents == ['ident_1', 'ident_2', 'ident_3']

        # 完整树(包含快照存储节点与虚拟节点)
        complete_tree = tree_operation.CreateTree(tree_ident).generate_complete_tree()
        nodes = complete_tree.nodes_by_bfs
        node_idents = [complete_tree.get_ident_by_node(node) for node in nodes]
        assert node_idents == ['ident_1', 'ident_2', 'new_ident_3', 'ident_3', 'new_ident_1', ]

    def test_create_tree_2(self):
        """创建树实例

        :remark:
            真实节点：
                ident_4, ident_5, ident_6
            虚拟节点：
                new_ident_4:cfc
            树节点的从属关系：
                ident_4 <— ident_5 <— new_ident_4 <— ident_6
        """

        tree_ident = 'tree_ident_2'

        # 完整树(包含快照存储节点与虚拟节点)
        complete_tree = tree_operation.CreateTree(tree_ident).generate_complete_tree()
        nodes = complete_tree.nodes_by_bfs
        node_idents = [complete_tree.get_ident_by_node(node) for node in nodes]
        assert node_idents == ['ident_4', 'ident_5', 'new_ident_4', 'ident_6']

    def test_create_tree_3(self):
        """创建树实例

        :remark:
            虚拟节点：
                new_ident_7:nc
            树节点的从属关系：
                new_ident_7
        """

        tree_ident = 'tree_ident_3'

        # 完整树(包含快照存储节点与虚拟节点)
        complete_tree = tree_operation.CreateTree(tree_ident).generate_complete_tree()
        assert 'new_ident_7' in complete_tree.node_dict

        # 测试node不存在的情况
        with pytest.raises(tree.NodeNotExist):
            node = "xxx"
            complete_tree.get_ident_by_node(node)


class TestOperateTree:

    def test_fetch_storage_for_chain_1(self):
        """获取链所依赖的存储节点

        :remark:
            链式关系:
                ident_1 <— ident_2 <— new_ident_3 <— ident_3 <— new_ident_1
        """

        tree_ident = 'tree_ident_1'
        storage_ident = 'new_ident_1'

        storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
        result = [storage['ident'] for storage in storages]
        assert result == ['ident_1', 'ident_2', 'ident_3']

    def test_fetch_storage_for_chain_2(self):
        """获取链所依赖的存储节点

        :remark:
            链式关系:
                ident_1 <— ident_2 <— new_ident_3
        """

        tree_ident = 'tree_ident_1'
        storage_ident = 'new_ident_3'

        storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
        result = [storage['ident'] for storage in storages]
        assert result == ['ident_1', 'ident_2']

    def test_fetch_storage_for_chain_3(self):
        """获取链所依赖的存储节点

        :remark:
            链式关系:
                ident_4 <— ident_5 <— new_ident_4
        """

        tree_ident = 'tree_ident_2'
        storage_ident = 'new_ident_4'

        storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
        result = [storage['ident'] for storage in storages]
        assert result == ['ident_4', 'ident_5']

    def test_fetch_storage_for_chain_4(self):
        """获取链所依赖的存储节点

        :remark:
            链式关系:
                ident_4 <— ident_5 <— new_ident_4 <— ident_6
        """

        tree_ident = 'tree_ident_2'
        storage_ident = 'ident_6'

        storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
        result = [storage['ident'] for storage in storages]
        assert result == ['ident_4', 'ident_5', 'ident_6']

    def test_fetch_storage_for_chain_5(self):
        """获取链所依赖的存储节点

        :remark:
            链式关系:
                ident_7
        """

        tree_ident = 'tree_ident_3'
        storage_ident = 'ident_7'

        storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
        result = [storage['ident'] for storage in storages]
        assert result == ['ident_7']
