from .base import Backend

# -----------------------------------------------------------------------------
# Azure Blob Storage via rclone's `serve s3` translation layer.
#
# MinIO used to offer a "gateway" mode that translated the S3 API onto
# external backends, including Azure Blob Storage (which has no S3 API of
# its own). MinIO deprecated gateway mode in 2022; RustFS, its replacement,
# never had one. This backend evaluates rclone (https://rclone.org) as a
# replacement for that lost capability: Open edX keeps talking to a plain S3
# endpoint, and `rclone serve s3` translates onto an `azureblob:` remote
# behind it.
#
# rclone's own documentation labels `serve s3` "Experimental", and this is
# genuinely a different category of thing than the rustfs backend: that one
# runs a native S3-compatible storage *engine*; this one runs a *translation
# layer* in front of a backend that was never designed to speak S3. This
# plugin's own live conformance suite reproducibly hangs `rclone serve s3` -
# a livelocked process, pinned CPU, zero network progress, no self-recovery -
# when multipart upload parts arrive out of ascending order (a pattern the
# S3 API explicitly permits) once the upload crosses roughly 300 MiB. See
# EVALUATION.md before relying on this backend for real course data. This is
# why OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK exists and defaults to false - see
# plugin.py's validate_objstorage_config.
#
# Defaults point at Azurite, Microsoft's free local Azure Storage emulator,
# so `tutor local launch` works with no real Azure account. Override
# OBJSTORAGE_AZURE_ACCOUNT / _ACCOUNT_KEY / _ENDPOINT together to point at a
# real Azure Storage account instead; see the README.
# -----------------------------------------------------------------------------

BACKEND = Backend(
    name="azure",
    defaults={
        "HOST": "files.{{ LMS_HOST }}",
        "REGION": "us-east-1",
        # https://hub.docker.com/r/rclone/rclone/tags
        # Hard-pinned to an exact tag, never a floating range: this
        # backend's multipart-upload testing (see EVALUATION.md) is only
        # valid for the exact version tested. 1.75.1 fixes CVE-2026-88045,
        # an unauthenticated memory-exhaustion DoS in the multipart upload
        # path - never go below it. Bump deliberately, and re-run the live
        # conformance suite against the new tag before adopting it.
        "DOCKER_IMAGE": "docker.io/rclone/rclone:1.75.1",
        # The image creates a non-root `rclone` user at this UID/GID but
        # does not switch to it by default; we do so explicitly. Unlike
        # RustFS there is no bind-mounted data directory, so there is no
        # chown-before-first-start step tied to this value.
        "UID": 1009,
        "GID": 1009,
        # Azure Blob Storage backend. These three defaults point at the
        # bundled Azurite emulator for local testing with no real Azure
        # account. Azurite's account name and key are fixed, publicly
        # documented constants - not secrets - the same for every Azurite
        # install everywhere. Override all three together for a real Azure
        # Storage account; see the README before doing so.
        "ACCOUNT": "devstoreaccount1",
        "ACCOUNT_KEY": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",  # noqa: E501
        "ENDPOINT": "http://azurite:10000/devstoreaccount1",
        # https://mcr.microsoft.com/en-us/artifact/mar/azure-storage/azurite/tags
        "AZURITE_DOCKER_IMAGE": "mcr.microsoft.com/azure-storage/azurite:3.37.0",
        # The explicit second opt-in required before this backend's
        # infrastructure will render at all. See plugin.py.
        "ACKNOWLEDGE_RISK": False,
    },
    # No per-backend AWS_SECRET_ACCESS_KEY here: see rustfs.py's comment -
    # all three backends share one generated secret (config.SHARED_UNIQUE).
    requires_ack_key="OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK",
)
