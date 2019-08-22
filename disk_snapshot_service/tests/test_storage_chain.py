import pytest

from business_logic.storage_chain import chain
from business_logic.storage_chain import chain_operation
from business_logic.storage_tree import tree_operation

from business_logic.storage_reference_manager import StorageReferenceManager


def _test_box(tree_ident, storage_ident, chain_class, caller_name, assert_idents, storage_reference_manager):
    storages = tree_operation.FetchStorageForChain(tree_ident, storage_ident).fetch()
    caller_name = caller_name
    chain_class = chain_class

    chain_obj = chain_operation.GenerateChain(
        storage_reference_manager=storage_reference_manager,
        caller_name=caller_name,
        storages_for_chain=storages,
        chain_class=chain_class).acquired_chain()

    key_storages = chain_obj.storages
    key_storage_idents = [storage['ident'] for storage in key_storages]
    assert key_storage_idents == assert_idents

    print(storage_reference_manager)
    chain_obj.release()


class TestStorageChain:

    def test_create_chain_for_r(self):
        """创建read链

        :remark:
            链式关系：
                ident_1 <— ident_2 <— ident_3
        """
        _test_box(
            tree_ident='tree_ident_1',
            storage_ident='ident_3',
            chain_class=chain.StorageChainForRead,
            caller_name='r',
            assert_idents=['ident_1', 'ident_2', 'ident_3'],
            storage_reference_manager=StorageReferenceManager()
        )

    # def test_create_chain_for_w(self):
    #     _test_box(
    #         tree_ident='tree_ident_2',
    #         storage_ident='ident_5',
    #         chain_class=chain.StorageChainForWrite,
    #         caller_name='w',
    #         assert_idents=['ident_4', 'ident_5'],
    #         storage_reference_manager=StorageReferenceManager()
    #     )
    #
    # def test_create_chain_for_rw(self):
    #     _test_box(
    #         tree_ident='tree_ident_2',
    #         storage_ident='ident_6',
    #         chain_class=chain.StorageChainForRW,
    #         caller_name='rw',
    #         assert_idents=['ident_4', 'ident_5'],
    #         storage_reference_manager=StorageReferenceManager()
    #     )
