from __future__ import annotations

import os
import typing as t
from glob import glob

import importlib_resources
from tutor import exceptions as tutor_exceptions
from tutor import hooks as tutor_hooks
from tutor.__about__ import __version_suffix__

from . import backends, config
from .__about__ import __version__

# Handle version suffix in main mode, just like tutor core
if __version_suffix__:
    __version__ += "-" + __version_suffix__

PKG = importlib_resources.files("tutorobjectstorage")

# -----------------------------------------------------------------------------
# Object storage for Open edX, with a choice of three backends behind one
# config key, OBJSTORAGE_BACKEND:
#
#   rustfs       A local, self-hosted RustFS server (the default). See
#                backends/rustfs.py. Successor to tutor-rustfs.
#   azure        Azure Blob Storage via rclone's `serve s3` translation
#                layer. See backends/azure.py. Successor to
#                tutor-rclone-gateway. Gated behind
#                OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK - see
#                validate_objstorage_config below and EVALUATION.md.
#   external_s3  Any external S3-compatible provider (AWS S3, GCS, Ceph,
#                a RustFS/MinIO instance elsewhere). See
#                backends/external_s3.py. Reimplements the functionality
#                of tutor-contrib-s3 (https://github.com/cleura/tutor-contrib-s3),
#                an independently maintained plugin this one does not
#                depend on or replace.
#
# This plugin's own ENV_PATCHES loading mirrors tutor-rustfs/
# tutor-rclone-gateway's glob-based pattern, just applied twice: once over
# patches/shared/ (content that applies regardless of backend) and once per
# backend directory (content that is self-guarded with
# `{% if OBJSTORAGE_BACKEND == "<name>" %}` and therefore harmless to
# register even when inactive - Tutor's own ENV_PATCHES mechanism
# concatenates every registration under a given patch name, so an inactive
# backend's guarded-empty contribution simply joins as a blank line).
# -----------------------------------------------------------------------------

# --- config: backend selector, shared keys, then one set per backend -------
tutor_hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("OBJSTORAGE_BACKEND", config.DEFAULT_BACKEND),
        ("OBJSTORAGE_VERSION", __version__),
    ]
    + [(f"OBJSTORAGE_{key}", value) for key, value in config.SHARED_DEFAULTS.items()]
)
tutor_hooks.Filters.CONFIG_UNIQUE.add_items(
    [(f"OBJSTORAGE_{key}", value) for key, value in config.SHARED_UNIQUE.items()]
)
for backend in backends.ALL:
    tutor_hooks.Filters.CONFIG_DEFAULTS.add_items(
        [
            (f"OBJSTORAGE_{backend.name.upper()}_{key}", value)
            for key, value in backend.defaults.items()
        ]
    )
    tutor_hooks.Filters.CONFIG_UNIQUE.add_items(
        [
            (f"OBJSTORAGE_{backend.name.upper()}_{key}", value)
            for key, value in backend.unique.items()
        ]
    )

# --- credential overrides: one central, unconditional registration ---------
# See config.CREDENTIAL_OVERRIDES for why this is NOT backend-conditional.
tutor_hooks.Filters.CONFIG_OVERRIDES.add_items(config.CREDENTIAL_OVERRIDES)

# --- patches: shared fragments (no guard) + one glob per backend -----------
for path in glob(str(PKG / "patches" / "shared" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        tutor_hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read())
        )
for backend in backends.ALL:
    for path in glob(str(PKG / "patches" / backend.name / "*")):
        with open(path, encoding="utf-8") as patch_file:
            tutor_hooks.Filters.ENV_PATCHES.add_item(
                (os.path.basename(path), patch_file.read())
            )

# --- init tasks: one shared service name, one script per backend -----------
# Confirmed from tutor/commands/jobs.py: CLI_DO_INIT_TASKS supports multiple
# independent registrations under one service name (Tutor core itself does
# this for "lms") - each runs as its own job invocation, not one pre-joined
# script. So every backend contributes its own self-guarded script, exactly
# mirroring the patches convention above.
_TASKS_DIR = PKG / "templates" / "objectstorage" / "tasks" / "objectstorage"
for backend in backends.ALL:
    script_path = _TASKS_DIR / f"{backend.name}.sh"
    if script_path.is_file():
        tutor_hooks.Filters.CLI_DO_INIT_TASKS.add_item(
            (config.INIT_SERVICE_NAME, script_path.read_text(encoding="utf-8")),
            priority=tutor_hooks.priorities.HIGH,
        )

# Add the "templates" folder as a template root
tutor_hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(str(PKG / "templates"))


LEGACY_CONFLICTING_PLUGINS = ("minio", "rustfs", "rclonegateway", "s3")


@tutor_hooks.Actions.PLUGIN_LOADED.add()
def check_plugin_conflict(plugin_name: str) -> None:
    """Refuse to run alongside tutor-minio or a legacy predecessor plugin.

    This does not vary by OBJSTORAGE_BACKEND: every backend claims
    STORAGES["default"] identically, so the conflict is unconditional
    regardless of which backend is active. "rustfs" and "rclonegateway" are
    this plugin's own direct predecessors (see MIGRATING.rst); "s3" is
    tutor-contrib-s3's registered Tutor plugin name - a third-party plugin
    this one does not depend on, but enabling both would still collide on
    STORAGES["default"].
    """
    if plugin_name in LEGACY_CONFLICTING_PLUGINS:
        raise tutor_exceptions.TutorError(
            f"The '{plugin_name}' and 'objectstorage' plugins cannot be "
            "enabled at the same time: they both configure Open edX's "
            "default object storage.\n"
            f"    tutor plugins disable {plugin_name}\n"
            "If you are migrating from tutor-rustfs or tutor-rclone-gateway, "
            "see MIGRATING.rst."
        )


@tutor_hooks.Actions.CONFIG_LOADED.add()
def validate_objstorage_config(cfg: dict[str, t.Any]) -> None:
    """Validate OBJSTORAGE_BACKEND and enforce the Azure risk gate.

    Fires on every tutor command that loads config (confirmed from
    tutor/config.py: CONFIG_LOADED fires at the end of every load_full()
    call, not only at plugin-enable time), so flipping OBJSTORAGE_BACKEND to
    "azure" later via `tutor config save --set` on an already-running
    deployment gets the same hard failure on the very next command.

    This is a hard failure, not a silent no-op, because the alternative -
    Django settings configured, infrastructure silently absent - is worse:
    it produces a deployment where every upload fails with no error
    pointing at the actual cause. The Jinja-level
    `and OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK` guards on every Azure patch are
    a second, independent layer underneath this one: they're what makes
    "no Azure infra renders without the flag" observable to offline
    template-rendering tests, which call Renderer.render_str() directly and
    so never go through this CONFIG_LOADED action at all.
    """
    backend_name = cfg.get("OBJSTORAGE_BACKEND")
    if backend_name not in config.BACKEND_CHOICES:
        raise tutor_exceptions.TutorError(
            f"OBJSTORAGE_BACKEND is {backend_name!r}; it must be one of "
            f"{config.BACKEND_CHOICES}."
        )
    for backend in backends.ALL:
        if (
            backend.requires_ack_key
            and backend_name == backend.name
            and not cfg.get(backend.requires_ack_key)
        ):
            raise tutor_exceptions.TutorError(
                f"OBJSTORAGE_BACKEND is '{backend.name}', but "
                f"{backend.requires_ack_key} is not set. The Azure/rclone "
                "backend has a confirmed livelock on out-of-order multipart "
                "upload parts past ~300MiB (see EVALUATION.md) and is not "
                "yet considered safe for production course content. Read "
                "it, then:\n"
                f"    tutor config save --set {backend.requires_ack_key}=true"
            )
