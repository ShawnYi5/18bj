import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from data_access.db_operation import journal

from data_access import models as m


@pytest.fixture('function')  # function：每个使用到db_session的用例会得到一个新的数据库连接，并且执行迁移
def db_session():
    alembic_cfg = Config(
        'D:\\workspace\\DiskSsnapshotService\\disk_snapshot_service\\data_access\\alembic.ini')  # 指定alembic配置文件，因为单元测试数据库与平时开发时候的数据库的连接uri不同
    command.upgrade(alembic_cfg, 'head')  # 执行alembic迁移，创建表
    engine = create_engine(
        'postgresql+psycopg2://postgres:f@127.0.0.1:21115/disksnapshotservice',
        convert_unicode=True
    )
    # m.Base.metadata.create_all(engine)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    yield session
    # 每个测试用例结束后，会执行以下操作
    # session.close_all()
    # command.downgrade(alembic_cfg, 'base')  # 执行alembic迁移，删除之前创建的表

