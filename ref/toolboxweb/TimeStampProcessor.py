from datetime import datetime
from enum import Enum


class TimestampType(Enum):
    s = 's'
    ms = 'ms'


def timestamp_now(timestamp_type: TimestampType):
    timestamp = datetime.now().timestamp()
    if timestamp_type == TimestampType.ms:
        timestamp = timestamp * 1000
    return int(timestamp)

