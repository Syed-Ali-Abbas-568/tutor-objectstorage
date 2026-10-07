Migrating to tutor-objectstorage
=================================

``tutor-objectstorage`` supersedes two previously separate plugins,
``tutor-rustfs`` and ``tutor-rclone-gateway``. Both predecessors' service
names, bind-mount paths, and PVC names are kept **identical** in this
plugin, so migrating is a config-key rename, not a data migration: no new
volume, no new chown dance, no re-upload.

Tutor itself has no built-in mechanism for renaming a plugin's own config
keys (confirmed by reading ``tutor/config.py``: the only rename support is a
fixed, non-extensible list for Tutor core's *own* historical renames), so
this has to be a documented manual step — the recipes below are copy-pasteable,
not a script you run blind.

.. warning::

   **Copy your existing generated secret across explicitly — do not skip
   this.** ``CONFIG_UNIQUE`` values are only generated if the key is
   **absent**. If you let the new plugin generate a fresh
   ``OBJSTORAGE_AWS_SECRET_ACCESS_KEY`` instead of copying your old one
   across, the object storage server will still work (it just restarts with
   a new credential), but any presigned URLs computed with the old secret
   become invalid immediately, and any client or script that had the old
   secret hardcoded will start failing with ``SignatureDoesNotMatch``.

From ``tutor-rustfs``
----------------------

::

    # 1. Capture the old plugin's values first.
    tutor config printvalue RUSTFS_BUCKET_NAME
    tutor config printvalue RUSTFS_FILE_UPLOAD_BUCKET_NAME
    tutor config printvalue RUSTFS_VIDEO_UPLOAD_BUCKET_NAME
    tutor config printvalue RUSTFS_GRADES_BUCKET_NAME
    tutor config printvalue RUSTFS_OPENEDX_LEARNING_BUCKET_NAME
    tutor config printvalue RUSTFS_QUERYSTRING_AUTH
    tutor config printvalue RUSTFS_HOST
    tutor config printvalue RUSTFS_CONSOLE_HOST
    tutor config printvalue RUSTFS_REGION
    tutor config printvalue RUSTFS_DOCKER_IMAGE
    tutor config printvalue RUSTFS_RC_DOCKER_IMAGE
    tutor config printvalue RUSTFS_UID
    tutor config printvalue RUSTFS_GID
    tutor config printvalue RUSTFS_AWS_SECRET_ACCESS_KEY

    # 2. Swap the plugin.
    pip install tutor-objectstorage
    tutor plugins disable rustfs
    tutor plugins enable objectstorage
    pip uninstall tutor-rustfs   # optional, once you've confirmed the new plugin works

    # 3. Re-apply the captured values under the new names. Bucket names and
    #    QUERYSTRING_AUTH lose the RUSTFS_ infix (they're shared across all
    #    three backends now); everything else becomes OBJSTORAGE_RUSTFS_*.
    #    Use the actual values you printed in step 1 below, not these
    #    examples.
    tutor config save \
        --set OBJSTORAGE_BACKEND=rustfs \
        --set OBJSTORAGE_BUCKET_NAME=openedx \
        --set OBJSTORAGE_FILE_UPLOAD_BUCKET_NAME=openedxuploads \
        --set OBJSTORAGE_VIDEO_UPLOAD_BUCKET_NAME=openedxvideos \
        --set OBJSTORAGE_GRADES_BUCKET_NAME=openedxgrades \
        --set OBJSTORAGE_OPENEDX_LEARNING_BUCKET_NAME=openedxlearning \
        --set OBJSTORAGE_QUERYSTRING_AUTH=true \
        --set OBJSTORAGE_RUSTFS_HOST=files.example.com \
        --set OBJSTORAGE_RUSTFS_CONSOLE_HOST=rustfs.example.com \
        --set OBJSTORAGE_RUSTFS_REGION=us-east-1 \
        --set OBJSTORAGE_RUSTFS_DOCKER_IMAGE=docker.io/rustfs/rustfs:1.0.0 \
        --set OBJSTORAGE_RUSTFS_RC_DOCKER_IMAGE=docker.io/rustfs/rc:v0.1.36 \
        --set OBJSTORAGE_RUSTFS_UID=10001 \
        --set OBJSTORAGE_RUSTFS_GID=10001 \
        --set OBJSTORAGE_AWS_SECRET_ACCESS_KEY=<your captured RUSTFS_AWS_SECRET_ACCESS_KEY>

    # 4. Confirm the secret matches BEFORE relaunching.
    tutor config printvalue OPENEDX_AWS_SECRET_ACCESS_KEY
    # Compare against the RUSTFS_AWS_SECRET_ACCESS_KEY you printed in step 1.

    tutor local launch   # reuses the existing `rustfs` bind-mounted volume unchanged

``RUSTFS_DISCOVERY_BUCKET_NAME`` has no separate step: it's computed from
whether the ``discovery`` plugin is enabled, exactly as before, just now
under the shared ``OBJSTORAGE_DISCOVERY_BUCKET_NAME`` name.

From ``tutor-rclone-gateway``
-------------------------------

Same shape as above, with one new, mandatory step this plugin didn't have
before: you must explicitly accept the known multipart-upload risk (see
``EVALUATION.md``) as a second, separate setting. This migration is
lower-risk on the data side than the ``rustfs`` migration above — all
object data lives in Azure itself, not a local volume, so there's no
"reuse the same volume" concern at all; only the init job's own identity
changes (see below), and that job is stateless and disposable.

::

    # 1. Capture the old plugin's values first.
    tutor config printvalue RCLONEGW_BUCKET_NAME
    tutor config printvalue RCLONEGW_FILE_UPLOAD_BUCKET_NAME
    tutor config printvalue RCLONEGW_VIDEO_UPLOAD_BUCKET_NAME
    tutor config printvalue RCLONEGW_GRADES_BUCKET_NAME
    tutor config printvalue RCLONEGW_OPENEDX_LEARNING_BUCKET_NAME
    tutor config printvalue RCLONEGW_QUERYSTRING_AUTH
    tutor config printvalue RCLONEGW_HOST
    tutor config printvalue RCLONEGW_REGION
    tutor config printvalue RCLONEGW_DOCKER_IMAGE
    tutor config printvalue RCLONEGW_UID
    tutor config printvalue RCLONEGW_GID
    tutor config printvalue RCLONEGW_AZURE_ACCOUNT
    tutor config printvalue RCLONEGW_AZURE_ACCOUNT_KEY
    tutor config printvalue RCLONEGW_AZURE_ENDPOINT
    tutor config printvalue RCLONEGW_AZURITE_DOCKER_IMAGE
    tutor config printvalue RCLONEGW_AWS_SECRET_ACCESS_KEY

    # 2. Swap the plugin.
    pip install tutor-objectstorage
    tutor plugins disable rclonegateway
    tutor plugins enable objectstorage
    pip uninstall tutor-rclone-gateway   # optional, once confirmed working

    # 3. Re-apply the captured values, PLUS the new mandatory risk
    #    acknowledgment. Use your own printed values, not these examples.
    tutor config save \
        --set OBJSTORAGE_BACKEND=azure \
        --set OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK=true \
        --set OBJSTORAGE_BUCKET_NAME=openedx \
        --set OBJSTORAGE_FILE_UPLOAD_BUCKET_NAME=openedxuploads \
        --set OBJSTORAGE_VIDEO_UPLOAD_BUCKET_NAME=openedxvideos \
        --set OBJSTORAGE_GRADES_BUCKET_NAME=openedxgrades \
        --set OBJSTORAGE_OPENEDX_LEARNING_BUCKET_NAME=openedxlearning \
        --set OBJSTORAGE_QUERYSTRING_AUTH=true \
        --set OBJSTORAGE_AZURE_HOST=files.example.com \
        --set OBJSTORAGE_AZURE_REGION=us-east-1 \
        --set OBJSTORAGE_AZURE_DOCKER_IMAGE=docker.io/rclone/rclone:1.75.1 \
        --set OBJSTORAGE_AZURE_UID=1009 \
        --set OBJSTORAGE_AZURE_GID=1009 \
        --set OBJSTORAGE_AZURE_ACCOUNT=<your captured value> \
        --set OBJSTORAGE_AZURE_ACCOUNT_KEY=<your captured value> \
        --set OBJSTORAGE_AZURE_ENDPOINT=<your captured value> \
        --set OBJSTORAGE_AZURITE_DOCKER_IMAGE=mcr.microsoft.com/azure-storage/azurite:3.37.0 \
        --set OBJSTORAGE_AWS_SECRET_ACCESS_KEY=<your captured RCLONEGW_AWS_SECRET_ACCESS_KEY>

    # 4. Confirm the secret matches, then launch.
    tutor config printvalue OPENEDX_AWS_SECRET_ACCESS_KEY
    tutor local launch

**What changes under the hood, harmlessly**: the init job's service name
moves from ``rclonegw-job`` to ``objectstorage-job`` (this plugin's init
task is now registered under the same name as the plugin itself, for every
backend — see the Unreleased changelog entry for why). Since that job only
runs ``rclone mkdir`` against Azure and holds no state of its own, this
rename has no data consequence; it just means ``tutor local do init
--limit=`` now takes the plugin name ``objectstorage``, not
``rclonegateway``.

From ``tutor-contrib-s3`` (optional — not a required migration)
-------------------------------------------------------------------

``tutor-contrib-s3`` is an independently maintained plugin and is not
superseded by this one — nothing requires you to move off it. If you want
to anyway, for the convenience of one unified plugin across your whole
Open edX footprint, the key mapping is:

.. list-table::
   :header-rows: 1

   * - ``tutor-contrib-s3`` key
     - ``tutor-objectstorage`` key
   * - ``S3_HOST``
     - ``OBJSTORAGE_EXTERNAL_S3_ENDPOINT_HOST``
   * - ``S3_PORT``
     - ``OBJSTORAGE_EXTERNAL_S3_PORT``
   * - ``S3_REGION``
     - ``OBJSTORAGE_EXTERNAL_S3_REGION``
   * - ``S3_USE_SSL``
     - ``OBJSTORAGE_EXTERNAL_S3_USE_SSL``
   * - ``S3_STORAGE_BUCKET``
     - ``OBJSTORAGE_BUCKET_NAME`` (shared across all backends now)
   * - ``S3_FILE_UPLOAD_BUCKET``
     - ``OBJSTORAGE_FILE_UPLOAD_BUCKET_NAME`` (shared)
   * - ``S3_GRADE_BUCKET``
     - ``OBJSTORAGE_GRADES_BUCKET_NAME`` (shared)
   * - ``S3_PROFILE_IMAGE_BUCKET``
     - ``OBJSTORAGE_EXTERNAL_S3_PROFILE_IMAGE_BUCKET`` (same empty-means-
       local-filesystem behavior; defaults to the shared bucket instead of
       empty)
   * - ``S3_PROFILE_IMAGE_CUSTOM_DOMAIN``
     - ``OBJSTORAGE_EXTERNAL_S3_PROFILE_IMAGE_CUSTOM_DOMAIN``
   * - ``S3_ADDRESSING_STYLE``
     - ``OBJSTORAGE_EXTERNAL_S3_ADDRESSING_STYLE``
   * - ``S3_CUSTOM_DOMAIN``
     - ``OBJSTORAGE_EXTERNAL_S3_CUSTOM_DOMAIN``
   * - ``OPENEDX_AWS_ACCESS_KEY`` / ``OPENEDX_AWS_SECRET_ACCESS_KEY``
     - Same names, still set by hand — this plugin's ``external_s3``
       backend contributes nothing to them either, exactly like
       ``tutor-contrib-s3``.

**This is a real behavior change, not just a rename**: this plugin's
bucket model is the fuller 6-bucket one (adds video-upload and
openedx-learning buckets, which ``tutor-contrib-s3`` never had), so you'll
need to create 2 more buckets. ``S3_SIGNATURE_VERSION``,
``S3_DEFAULT_ACL``, and ``S3_REQUEST_CHECKSUM_CALCULATION`` are no longer
configurable — they're hardcoded to the same values ``tutor-contrib-s3``
already defaults to (``s3v4``, unset/``None``, ``when_required``), so this
should be a no-op for anyone who never changed them away from the default.
