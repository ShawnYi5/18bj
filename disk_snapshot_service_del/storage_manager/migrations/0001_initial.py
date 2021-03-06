# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-04-03 14:24
from __future__ import unicode_literals

import basic_library.xfield
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DiskSnapshot',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('disk_index', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='DiskSnapshotLocator',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('locator_ident', models.CharField(max_length=40, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='DiskSnapshotStorage',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('storage_type', models.PositiveSmallIntegerField(choices=[(1, 'CDP'), (2, 'QCOW')])),
                ('storage_status', models.PositiveSmallIntegerField(choices=[(1, 'creating'), (2, 'data_writing'), (3, 'hashing'), (4, 'storage'), (5, 'exception'), (6, 'recycling'), (7, 'recycled')])),
                ('disk_snapshot_storage_ident', models.CharField(max_length=40, unique=True)),
                ('disk_bytes', models.BigIntegerField()),
                ('image_path', models.CharField(max_length=128)),
                ('full_hash_path', models.CharField(max_length=128, null=True)),
                ('inc_hash_path', models.CharField(max_length=128, null=True)),
                ('storage_begin_timestamp', basic_library.xfield.TimestampField(decimal_places=6, max_digits=20)),
                ('storage_end_timestamp', basic_library.xfield.TimestampField(decimal_places=6, max_digits=20)),
                ('parent_timestamp', basic_library.xfield.TimestampField(decimal_places=6, max_digits=20, null=True)),
                ('inc_raw_data_bytes', models.BigIntegerField(default=-1)),
                ('file_level_deduplication', models.BooleanField()),
                ('locator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshot_storages', to='storage_manager.DiskSnapshotLocator')),
                ('parent_snapshot', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children_snapshots', to='storage_manager.DiskSnapshotStorage')),
            ],
        ),
        migrations.CreateModel(
            name='DiskSnapshotStorageRoot',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('root_uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('hash_type', models.PositiveSmallIntegerField(choices=[(1, 'NO_HASH'), (2, 'MD4CRC32')])),
                ('root_valid', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Host',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('host_ident', models.CharField(max_length=40, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='HostSnapshot',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('host_snapshot_ident', models.CharField(max_length=40, unique=True)),
                ('host_snapshot_valid', models.BooleanField(default=True)),
                ('host_snapshot_type', models.PositiveSmallIntegerField(choices=[(1, 'normal'), (2, 'cdp')])),
                ('host_snapshot_begin_timestamp', basic_library.xfield.TimestampField(decimal_places=6, max_digits=20)),
                ('host_snapshot_end_timestamp', basic_library.xfield.TimestampField(decimal_places=6, max_digits=20)),
                ('host_snapshot_task_info', models.TextField(default='{}')),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='host_snapshots', to='storage_manager.Host')),
            ],
        ),
        migrations.CreateModel(
            name='SourceDisk',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('disk_native_guid', models.CharField(max_length=40)),
                ('agent_disk_ident', models.CharField(max_length=40)),
                ('disk_display_name', models.CharField(max_length=128)),
                ('disk_bytes', models.BigIntegerField()),
                ('boot_device', models.BooleanField()),
                ('os_device', models.BooleanField()),
                ('bmf_device', models.BooleanField()),
                ('partition_type', models.PositiveSmallIntegerField(choices=[(1, 'MBR'), (2, 'GBT'), (3, 'RAW')])),
                ('host', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='source_disks', to='storage_manager.Host')),
            ],
        ),
        migrations.AddField(
            model_name='disksnapshotstorage',
            name='source_disk',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshot_storages', to='storage_manager.SourceDisk'),
        ),
        migrations.AddField(
            model_name='disksnapshotstorage',
            name='storage_root',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshot_storages', to='storage_manager.DiskSnapshotStorageRoot'),
        ),
        migrations.AddField(
            model_name='disksnapshot',
            name='host_snapshot',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshots', to='storage_manager.HostSnapshot'),
        ),
        migrations.AddField(
            model_name='disksnapshot',
            name='locator',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshots', to='storage_manager.DiskSnapshotLocator'),
        ),
        migrations.AddField(
            model_name='disksnapshot',
            name='source_disk',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='disk_snapshots', to='storage_manager.SourceDisk'),
        ),
        migrations.AddIndex(
            model_name='sourcedisk',
            index=models.Index(fields=['disk_native_guid'], name='storage_man_disk_na_573667_idx'),
        ),
        migrations.AddIndex(
            model_name='sourcedisk',
            index=models.Index(fields=['agent_disk_ident'], name='storage_man_agent_d_6a8bbb_idx'),
        ),
        migrations.AddIndex(
            model_name='hostsnapshot',
            index=models.Index(fields=['host_snapshot_begin_timestamp'], name='storage_man_host_sn_a61a5b_idx'),
        ),
        migrations.AddIndex(
            model_name='hostsnapshot',
            index=models.Index(fields=['host_snapshot_end_timestamp'], name='storage_man_host_sn_689ed8_idx'),
        ),
        migrations.AddIndex(
            model_name='disksnapshotstorage',
            index=models.Index(fields=['image_path'], name='storage_man_image_p_a5c70b_idx'),
        ),
    ]
