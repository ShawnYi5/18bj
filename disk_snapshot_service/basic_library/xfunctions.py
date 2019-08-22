import decimal
import time

import arrow
from dateutil import tz


def convert_timestamp_float_to_decimal(timestamp: float) -> decimal.Decimal:
    return decimal.Decimal(f'{timestamp:.06f}')


def current_timestamp() -> decimal.Decimal:
    return convert_timestamp_float_to_decimal(time.time())


def humanize_timestamp(timestamp: decimal.Decimal, empty_str='') -> str:
    """格式化时间戳为人可读的描述"""
    if not timestamp:
        return empty_str

    return arrow.Arrow.fromtimestamp(timestamp, tz.tzlocal()).format('YYYY-MM-DD HH:mm:ss.SSSSSS')
