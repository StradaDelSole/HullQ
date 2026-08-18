import hullq.cli
import hullq.domain
import hullq.research
import hullq.sources
import hullq.storage
from hullq import __version__


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_stage2_package_namespaces_import() -> None:
    modules = (
        hullq.cli,
        hullq.domain,
        hullq.research,
        hullq.sources,
        hullq.storage,
    )
    assert all(module.__name__.startswith("hullq.") for module in modules)
