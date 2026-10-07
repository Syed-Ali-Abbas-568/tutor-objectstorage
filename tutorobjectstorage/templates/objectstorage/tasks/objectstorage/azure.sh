{% if OBJSTORAGE_BACKEND == "azure" and OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK %}
# Provision Azure Blob containers behind the rclone gateway.
#
# Unlike RustFS's `rc` client, this talks straight to Azure over the
# `azureblob:` remote (not through either `rclone serve s3` process), and
# there is no bucket-policy step: anonymous read access to the public
# bucket is a property of the two-process gateway topology (see
# local-docker-compose-services and the caddyfile patch), not a flag set
# on the bucket itself. `rclone mkdir` is idempotent against an
# already-existing container, so this task is safe to re-run.
rclone mkdir azureblob:{{ OBJSTORAGE_BUCKET_NAME }}
rclone mkdir azureblob:{{ OBJSTORAGE_FILE_UPLOAD_BUCKET_NAME }}
rclone mkdir azureblob:{{ OBJSTORAGE_VIDEO_UPLOAD_BUCKET_NAME }}
rclone mkdir azureblob:{{ OBJSTORAGE_GRADES_BUCKET_NAME }}
rclone mkdir azureblob:{{ OBJSTORAGE_OPENEDX_LEARNING_BUCKET_NAME }}

{% if OBJSTORAGE_DISCOVERY_BUCKET_NAME %}
rclone mkdir azureblob:{{ OBJSTORAGE_DISCOVERY_BUCKET_NAME }}
{% endif %}
{% endif %}
