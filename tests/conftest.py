"""Shared fixtures.

Drives Tutor's real plugin-discovery/loading pipeline (CORE_READY +
plugins.load_all), not a mock - so a break in how Tutor discovers this
plugin shows up here rather than only at `tutor local launch`. Mirrors the
conftest.py shape already proven in tutor-rustfs and tutor-rclone-gateway,
generalized over three backends instead of one.
"""

from __future__ import annotations

import glob
import os
import tempfile
import typing as t

import pytest
from tutor import config as tutor_config
from tutor import env as tutor_env
from tutor import hooks as tutor_hooks
from tutor import plugins

PATCHES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tutorobjectstorage",
    "patches",
)

BACKENDS = ("rustfs", "azure", "external_s3")


def patch_names() -> list[str]:
    names: set[str] = set()
    for sub in ("shared", *BACKENDS):
        for path in glob.glob(os.path.join(PATCHES_DIR, sub, "*")):
            names.add(os.path.basename(path))
    return sorted(names)


def read_patch(name: str) -> str:
    for sub in ("shared", *BACKENDS):
        path = os.path.join(PATCHES_DIR, sub, name)
        if os.path.isfile(path):
            return open(path, encoding="utf-8").read()
    raise FileNotFoundError(name)


@pytest.fixture(scope="session", autouse=True)
def _loaded_plugin() -> None:
    tutor_hooks.Actions.CORE_READY.do()
    assert "objectstorage" in plugins.iter_installed()
    plugins.load_all(["objectstorage"])


def load_fresh_config(**user_values: t.Any) -> dict[str, t.Any]:
    """Load a fully-rendered config from a brand-new root, seeded with
    `user_values` as if they were already saved in config.yml.

    This is deliberately NOT "load one config, then mutate+re-render it
    for a different backend": CONFIG_OVERRIDES (OPENEDX_AWS_ACCESS_KEY/
    _SECRET_ACCESS_KEY) and PLUGINS-derived CONFIG_DEFAULTS
    (OBJSTORAGE_DISCOVERY_BUCKET_NAME) are only rendered ONCE by
    render_full() - by the time a value is a plain string with no Jinja
    tags left, re-running render_full() on it is a no-op regardless of
    what else changed in the dict. Writing the desired values into
    config.yml *before* the first load_full() call (exactly how a real
    `tutor config save --set ...` on a fresh root works) is what makes
    every derived value - including these - correctly reflect the chosen
    backend from the first render pass.
    """
    with tempfile.TemporaryDirectory() as root:
        if user_values:
            with open(os.path.join(root, "config.yml"), "w", encoding="utf-8") as f:
                import yaml

                yaml.safe_dump(user_values, f)
        return tutor_config.load_full(root)


def render_for_backend(
    base_config: dict[str, t.Any], backend: str, **overrides: t.Any
) -> dict[str, t.Any]:
    """Load a fresh config with OBJSTORAGE_BACKEND set to `backend` from the
    start (see load_fresh_config). `base_config` is accepted for fixture-
    dependency ordering only and is otherwise unused - every call here
    loads its own independent, from-scratch config.

    OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK defaults to True here so that tests
    not specifically about the risk gate aren't tripped by it; tests that
    care about the gate override it back to False explicitly.
    """
    del base_config
    user_values: dict[str, t.Any] = {
        "OBJSTORAGE_BACKEND": backend,
        "OBJSTORAGE_AZURE_ACKNOWLEDGE_RISK": True,
    }
    user_values.update(overrides)
    return load_fresh_config(**user_values)


def render_bypassing_config_loaded(**user_values: t.Any) -> dict[str, t.Any]:
    """Render a config WITHOUT ever firing Actions.CONFIG_LOADED.

    Only use this to test the Jinja-level `and OBJSTORAGE_AZURE_ACKNOWLEDGE_
    RISK` guards on the Azure patches in isolation - i.e. to simulate "what
    if validate_objstorage_config's hard-fail didn't run" (an offline
    template-rendering code path, or a future caller that renders patches
    without going through tutor_config.load_full()). Every other test
    should use render_for_backend()/load_fresh_config(), which exercises
    the real, full load_full() pipeline including this plugin's own
    CONFIG_LOADED validation - matching what an actual `tutor` command does.
    """
    cfg: dict[str, t.Any] = dict(user_values)
    tutor_config.update_with_base(cfg)
    tutor_config.update_with_defaults(cfg)
    tutor_config.render_full(cfg)
    return cfg


@pytest.fixture(scope="session")
def base_config() -> dict[str, t.Any]:
    return load_fresh_config()


@pytest.fixture(scope="session")
def config_by_backend(base_config: dict[str, t.Any]) -> dict[str, dict[str, t.Any]]:
    return {backend: render_for_backend(base_config, backend) for backend in BACKENDS}


@pytest.fixture(scope="session")
def config(config_by_backend: dict[str, dict[str, t.Any]]) -> dict[str, t.Any]:
    """The default-backend (rustfs) config, for backend-agnostic tests."""
    return config_by_backend["rustfs"]


@pytest.fixture(scope="session")
def renderer_by_backend(
    config_by_backend: dict[str, dict[str, t.Any]],
) -> dict[str, tutor_env.Renderer]:
    return {
        backend: tutor_env.Renderer(cfg) for backend, cfg in config_by_backend.items()
    }


@pytest.fixture(scope="session")
def renderer(renderer_by_backend: dict[str, tutor_env.Renderer]) -> tutor_env.Renderer:
    return renderer_by_backend["rustfs"]


@pytest.fixture(scope="session")
def rendered_by_backend(
    renderer_by_backend: dict[str, tutor_env.Renderer],
) -> dict[str, dict[str, str]]:
    return {
        backend: {name: renderer.patch(name) for name in patch_names()}
        for backend, renderer in renderer_by_backend.items()
    }


@pytest.fixture(scope="session")
def rendered(rendered_by_backend: dict[str, dict[str, str]]) -> dict[str, str]:
    return rendered_by_backend["rustfs"]


def init_scripts_for(renderer: tutor_env.Renderer) -> dict[str, str]:
    """Render every registered init-task script, keyed by backend name.

    All three backends register under the same service name
    (config.INIT_SERVICE_NAME = "objectstorage"), so this renders each
    registered script in turn and returns them indexed positionally -
    callers that need a specific backend's script should instead render
    templates/objectstorage/tasks/objectstorage/<name>.sh directly via
    read_task_script() below.
    """
    scripts = {}
    for i, (_service, script) in enumerate(
        tutor_hooks.Filters.CLI_DO_INIT_TASKS.iterate()
    ):
        scripts[str(i)] = renderer.render_str(script)
    return scripts


TASKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tutorobjectstorage",
    "templates",
    "objectstorage",
    "tasks",
    "objectstorage",
)


def read_task_script(backend: str) -> str:
    return open(os.path.join(TASKS_DIR, f"{backend}.sh"), encoding="utf-8").read()
