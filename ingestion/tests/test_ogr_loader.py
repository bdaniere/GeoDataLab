import subprocess

import pytest

from core.models import DestinationConfig, SourceData
from loaders.geographic import ogr_loader
from loaders.geographic.ogr_loader import OgrLoader


@pytest.fixture
def docker_env(tmp_path, monkeypatch):
    module_path = tmp_path / "ingestion" / "loaders" / "geographic" / "ogr_loader.py"
    monkeypatch.setattr(ogr_loader, "__file__", str(module_path))
    for name in (
        "POSTGRES_HOST",
        "POSTGIS_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    env_path = tmp_path / "docker" / ".env"
    env_path.parent.mkdir()
    return env_path


def test_database_environment_uses_docker_variables(docker_env, monkeypatch):
    docker_env.write_text(
        "POSTGRES_USER=file_user\n"
        "POSTGRES_PASSWORD=file_password\n"
        "POSTGRES_DB=file_db\n"
        "POSTGIS_PORT=5423\n"
    )
    monkeypatch.setenv("POSTGRES_USER", "environment_user")
    monkeypatch.setenv("UNRELATED_VARIABLE", "preserved")

    environment = OgrLoader()._get_database_environment()

    assert environment["PGHOST"] == "localhost"
    assert environment["PGPORT"] == "5423"
    assert environment["PGDATABASE"] == "file_db"
    assert environment["PGUSER"] == "environment_user"
    assert environment["PGPASSWORD"] == "file_password"
    assert environment["UNRELATED_VARIABLE"] == "preserved"


def test_database_environment_uses_configured_host_and_default_port(
    docker_env, monkeypatch
):
    docker_env.write_text(
        "POSTGRES_USER=user\nPOSTGRES_PASSWORD=password\nPOSTGRES_DB=db\n"
    )
    monkeypatch.setenv("POSTGRES_HOST", "database")

    environment = OgrLoader()._get_database_environment()

    assert environment["PGHOST"] == "database"
    assert environment["PGPORT"] == "5432"


def test_database_environment_uses_host_from_docker_file(docker_env):
    docker_env.write_text(
        "POSTGRES_HOST=database\n"
        "POSTGRES_USER=user\nPOSTGRES_PASSWORD=password\nPOSTGRES_DB=db\n"
    )

    environment = OgrLoader()._get_database_environment()

    assert environment["PGHOST"] == "database"


def test_database_environment_reports_missing_file(docker_env):
    with pytest.raises(FileNotFoundError, match="Environment file not found"):
        OgrLoader()._get_database_environment()


def test_database_environment_reports_missing_or_empty_variables(docker_env):
    docker_env.write_text("POSTGRES_USER=user\nPOSTGRES_PASSWORD=\n")

    with pytest.raises(ValueError) as error:
        OgrLoader()._get_database_environment()

    assert "POSTGRES_DB" in str(error.value)
    assert "POSTGRES_PASSWORD" in str(error.value)


@pytest.mark.parametrize("variable", ["POSTGRES_HOST", "POSTGIS_PORT"])
def test_database_environment_reports_empty_host_or_port(docker_env, variable):
    docker_env.write_text(
        "POSTGRES_USER=user\nPOSTGRES_PASSWORD=password\nPOSTGRES_DB=db\n"
        f"{variable}=\n"
    )

    with pytest.raises(ValueError, match=variable):
        OgrLoader()._get_database_environment()


def test_load_passes_database_environment_to_ogr2ogr(docker_env, tmp_path, monkeypatch):
    docker_env.write_text(
        "POSTGRES_USER=user\nPOSTGRES_PASSWORD=password\n"
        "POSTGRES_DB=db\nPOSTGIS_PORT=5423\n"
    )
    source_path = tmp_path / "source.gpkg"
    source_path.touch()
    source = SourceData("source", "local", source_path)
    destination = DestinationConfig("postgis", "raw_data", "features")
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs["env"])
        return subprocess.CompletedProcess(command, 0, stdout="loaded", stderr="")

    monkeypatch.setattr(ogr_loader.subprocess, "run", fake_run)

    result = OgrLoader().load(source, destination)

    assert result.success
    assert captured["PGHOST"] == "localhost"
    assert captured["PGPORT"] == "5423"
    assert captured["PGDATABASE"] == "db"
    assert captured["PGUSER"] == "user"
    assert captured["PGPASSWORD"] == "password"
