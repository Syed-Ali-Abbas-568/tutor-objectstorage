from .base import Backend

# -----------------------------------------------------------------------------
# RustFS: a local, self-hosted S3-compatible object storage server.
#
# This is a successor to tutor-minio. MinIO was archived upstream, so this
# backend runs RustFS (https://github.com/rustfs/rustfs) instead: a Rust
# reimplementation of the MinIO S3 API that uses the same ports and the same
# bucket policy semantics. Bucket provisioning uses `rc`
# (https://github.com/rustfs/cli), RustFS's own S3-compatible CLI.
#
# This is the default backend (OBJSTORAGE_BACKEND defaults to "rustfs"): it
# is the only one of the three with no external account requirement and a
# production track record, so `tutor plugins enable objectstorage` reproduces
# the standalone tutor-rustfs plugin's zero-config experience exactly.
# -----------------------------------------------------------------------------

BACKEND = Backend(
    name="rustfs",
    defaults={
        # Hostnames. HOST serves the S3 API and must be reachable from
        # learners' browsers, not just from the Open edX containers:
        # presigned download URLs and public asset URLs are generated
        # against it.
        "HOST": "files.{{ LMS_HOST }}",
        "CONSOLE_HOST": "rustfs.{{ LMS_HOST }}",
        # Matches RustFS's own built-in default; changing it here also
        # changes the value passed to the server.
        "REGION": "us-east-1",
        # https://hub.docker.com/r/rustfs/rustfs/tags
        # Pinned to an explicit tag rather than `latest` so that a
        # `tutor local launch` is reproducible and an upstream push can't
        # silently change the object store under a running deployment.
        # Multi-arch (linux/amd64 + linux/arm64).
        "DOCKER_IMAGE": "docker.io/rustfs/rustfs:1.0.0",
        # The RustFS image does not ship a client, so the init/admin job
        # runs from `rc`'s own image, published by the RustFS project at
        # https://hub.docker.com/r/rustfs/rc. Pinned for the same reason
        # as DOCKER_IMAGE above.
        "RC_DOCKER_IMAGE": "docker.io/rustfs/rc:v0.1.36",
        # RustFS containers run as this UID. Passed explicitly to the
        # `user:` directive so one-shot commands don't run as root and
        # leave root-owned files in the data volume. Override if your
        # host's user namespace maps the container user differently
        # (e.g. rootless Docker).
        "UID": 10001,
        "GID": 10001,
    },
    # No per-backend AWS_SECRET_ACCESS_KEY here: all three backends share
    # one generated secret (config.SHARED_UNIQUE) since only one backend's
    # infrastructure is ever actually running at a time - see config.py's
    # CREDENTIAL_OVERRIDES docstring for why a per-backend secret plus a
    # backend-conditional override actually breaks `tutor config save`.
)
