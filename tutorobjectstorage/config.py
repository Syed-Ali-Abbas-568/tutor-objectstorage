from __future__ import annotations

import typing as t

# The service/task name shared by every backend's init-task contribution
# (see plugin.py). Matches the plugin's own Tutor entry-point name
# ("objectstorage") on purpose: the standalone tutor-rclone-gateway plugin
# registered its init task under a *different* name than its own plugin
# name ("rclonegw" vs. "rclonegateway"), which meant `tutor local do init
# --limit=rclonegw` silently matched nothing. Keeping these identical here
# removes that trap instead of reproducing it under a new name.
INIT_SERVICE_NAME = "objectstorage"

BACKEND_CHOICES = ("rustfs", "azure", "external_s3")
DEFAULT_BACKEND = "rustfs"

# Shared config, unprefixed suffixes (plugin.py adds the OBJSTORAGE_ prefix).
# These are "shared" rather than backend-private because the same value is
# safely portable across a backend switch - see the plan's namespacing rule.
# Bucket names deliberately use the fuller 6-bucket rustfs/rclone-gateway
# model for all three backends, including external_s3 (which otherwise has
# a narrower model under tutor-contrib-s3 today) - see the feature-parity
# checklist in the project plan for the reasoning and the one real cost
# (two more buckets to provision when coming from tutor-contrib-s3).
SHARED_DEFAULTS: dict[str, t.Any] = {
    "BUCKET_NAME": "openedx",
    "FILE_UPLOAD_BUCKET_NAME": "openedxuploads",
    "VIDEO_UPLOAD_BUCKET_NAME": "openedxvideos",
    "GRADES_BUCKET_NAME": "openedxgrades",
    "OPENEDX_LEARNING_BUCKET_NAME": "openedxlearning",
    "DISCOVERY_BUCKET_NAME": "{% if 'discovery' in PLUGINS %}discoveryuploads{% endif %}",  # noqa: E501
    "QUERYSTRING_AUTH": True,
}

# One shared generated secret, not one per backend. This is deliberate, not
# a missed opportunity for backend-isolation: only one backend's
# infrastructure is ever actually running at a time, so there is nothing to
# isolate, and a single CONFIG_UNIQUE key here sidesteps a real Tutor-core
# constraint that a per-backend, OBJSTORAGE_BACKEND-conditional dispatch
# cannot satisfy (see CREDENTIAL_OVERRIDES below for the full explanation).
SHARED_UNIQUE: dict[str, t.Any] = {
    "AWS_SECRET_ACCESS_KEY": "{{ 24|random_string }}",
}

# The OPENEDX_AWS_ACCESS_KEY / OPENEDX_AWS_SECRET_ACCESS_KEY overrides are
# global, unprefixed Tutor-core settings every consumer reads directly
# (Open edX, xqueue, discovery, and tutor-contrib-s3 today).
#
# These are deliberately NOT conditioned on OBJSTORAGE_BACKEND, even though
# only the rustfs/azure backends actually want a generated secret (external_s3
# wants these two left for the operator to set by hand). An earlier version
# of this plugin tried exactly that - a `{% if OBJSTORAGE_BACKEND == "rustfs"
# %}...{% elif == "azure" %}...{% else %}""{% endif %}` dispatch - and it
# broke `tutor config save` outright: CONFIG_OVERRIDES are rendered during
# tutor_config.load_minimal(), which Tutor core calls *before* plugin
# CONFIG_DEFAULTS (including OBJSTORAGE_BACKEND itself) are merged in, so
# referencing OBJSTORAGE_BACKEND here raises "is undefined" on literally
# every `tutor config save`. Worse than a crash: papering over the crash
# (e.g. with a `| default(...)` filter) would still be wrong, because
# load_minimal()'s rendered result gets persisted into config.yml as a
# literal value on the very first save - permanently freezing in whatever
# the fallback branch picked, regardless of which backend the operator
# actually chose, with no later re-evaluation. CONFIG_UNIQUE values (like
# SHARED_UNIQUE above) do NOT have this problem - they're merged in earlier,
# at get_base() time, specifically so they're available when overrides
# render - which is exactly why this stays a plain reference to one shared
# CONFIG_UNIQUE key instead of a backend-conditional expression.
#
# external_s3 operators: set these two yourself, e.g.
#   tutor config save --set OPENEDX_AWS_ACCESS_KEY=... \
#                     --set OPENEDX_AWS_SECRET_ACCESS_KEY=...
# after enabling this plugin - see the README.
CREDENTIAL_OVERRIDES: list[tuple[str, str]] = [
    ("OPENEDX_AWS_ACCESS_KEY", "openedx"),
    ("OPENEDX_AWS_SECRET_ACCESS_KEY", "{{ OBJSTORAGE_AWS_SECRET_ACCESS_KEY }}"),
]
