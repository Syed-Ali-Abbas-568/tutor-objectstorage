from . import azure, external_s3, rustfs
from .base import Backend

ALL: tuple[Backend, ...] = (rustfs.BACKEND, azure.BACKEND, external_s3.BACKEND)

__all__ = ["ALL", "Backend"]
