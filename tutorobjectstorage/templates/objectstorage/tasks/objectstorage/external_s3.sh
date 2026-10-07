{% if OBJSTORAGE_BACKEND == "external_s3" %}
# This backend provisions nothing automatically: different S3-compatible
# providers have genuinely different ACL/CLI semantics, so - matching
# tutor-contrib-s3's existing philosophy - buckets are assumed to already
# exist, created and access-controlled out-of-band by the operator. See
# the README's "Using an external S3-compatible provider" section.
#
# This is a visible, documented no-op rather than silence: without an
# explicit message here, `tutor local do init`'s own output would
# otherwise look like something failed to run rather than like a
# deliberate design choice.
echo "objectstorage: OBJSTORAGE_BACKEND=external_s3, so no buckets are provisioned automatically."
echo "Create these yourself before Open edX writes to them:"
echo "  - {{ OBJSTORAGE_BUCKET_NAME }}"
echo "  - {{ OBJSTORAGE_FILE_UPLOAD_BUCKET_NAME }}"
echo "  - {{ OBJSTORAGE_VIDEO_UPLOAD_BUCKET_NAME }}"
echo "  - {{ OBJSTORAGE_GRADES_BUCKET_NAME }}"
echo "  - {{ OBJSTORAGE_OPENEDX_LEARNING_BUCKET_NAME }}"
{% if OBJSTORAGE_DISCOVERY_BUCKET_NAME %}
echo "  - {{ OBJSTORAGE_DISCOVERY_BUCKET_NAME }}"
{% endif %}
echo "See the tutor-objectstorage README's external_s3 setup section."
{% endif %}
