import copy
from pprint import pformat as pf
from typing import List, Optional, Type

import pytest
from typing_extensions import ClassVar

from great_expectations.zep.context import get_context
from great_expectations.zep.interfaces import (
    BatchRequest,
    BatchRequestOptions,
    DataAsset,
    Datasource,
)
from great_expectations.zep.metadatasource import MetaDatasource
from great_expectations.zep.sources import _SourceFactories


class DummyDataAsset(DataAsset):
    """Minimal Concrete DataAsset Implementation"""

    def get_batch_request(self, options: Optional[BatchRequestOptions]) -> BatchRequest:
        return BatchRequest("datasource_name", "data_asset_name", options or {})


@pytest.fixture(scope="function")
def context_sources_cleanup() -> _SourceFactories:
    """Return the sources object and reset types/factories on teardown"""
    try:
        # setup
        sources_copy = copy.deepcopy(
            _SourceFactories._SourceFactories__source_factories
        )
        type_lookup_copy = copy.deepcopy(_SourceFactories.type_lookup)
        sources = get_context().sources

        assert (
            "add_datasource" not in sources.factories
        ), "Datasource base class should not be registered as a source factory"

        yield sources
    finally:
        _SourceFactories._SourceFactories__source_factories = sources_copy
        _SourceFactories.type_lookup = type_lookup_copy


@pytest.fixture(scope="function")
def empty_sources(context_sources_cleanup) -> _SourceFactories:
    _SourceFactories._SourceFactories__source_factories.clear()
    _SourceFactories.type_lookup.clear()
    yield context_sources_cleanup


class TestMetaDatasource:
    def test__new__only_registers_expected_number_of_datasources_factories_and_types(
        self, empty_sources: _SourceFactories
    ):
        assert len(empty_sources.factories) == 0
        assert len(empty_sources.type_lookup) == 0

        class MyTestDatasource(Datasource):
            asset_types: ClassVar[List[Type[DataAsset]]] = []

        expected_registrants = 1

        assert len(empty_sources.factories) == expected_registrants
        assert len(empty_sources.type_lookup) == 2 * expected_registrants

    def test__new__registers_sources_factory_method(
        self, context_sources_cleanup: _SourceFactories
    ):
        expected_method_name = "add_my_test"

        ds_factory_method_initial = getattr(
            context_sources_cleanup, expected_method_name, None
        )
        assert ds_factory_method_initial is None, "Check test cleanup"

        class MyTestDatasource(Datasource):
            asset_types: ClassVar[List[Type[DataAsset]]] = []

        ds_factory_method_final = getattr(
            context_sources_cleanup, expected_method_name, None
        )

        assert (
            ds_factory_method_final
        ), f"{MetaDatasource.__name__}.__new__ failed to add `{expected_method_name}()` method"

    def test__new__updates_asset_type_lookup(
        self, context_sources_cleanup: _SourceFactories
    ):
        type_lookup = context_sources_cleanup.type_lookup

        class FooAsset(DummyDataAsset):
            pass

        class BarAsset(DummyDataAsset):
            pass

        class FooBarDatasource(Datasource):
            asset_types = [FooAsset, BarAsset]

        print(f" type_lookup ->\n{pf(type_lookup)}\n")

        asset_types = FooBarDatasource.asset_types
        assert asset_types, "No asset types have been declared"

        registered_type_names = [type_lookup.get(t) for t in asset_types]
        for type_, name in zip(asset_types, registered_type_names):
            print(f"`{type_.__name__}` registered as '{name}'")
            assert name, f"{type.__name__} could not be retrieved"

        assert len(asset_types) == len(registered_type_names)


def test_minimal_ds_to_asset_flow(context_sources_cleanup):
    # 1. Define Datasource & Assets

    class RedAsset(DummyDataAsset):
        pass

    class BlueAsset(DummyDataAsset):
        pass

    class PurpleDatasource(Datasource):
        asset_types = [RedAsset, BlueAsset]

        def __init__(self, name: str) -> None:
            self.name = name
            self.assets = {}

        def add_red_asset(self, asset_name: str) -> RedAsset:
            asset = RedAsset(asset_name)
            self.assets[asset_name] = asset
            return asset

    # 2. Get context
    context = get_context()

    # 3. Add a datasource
    purple_ds: Datasource = context.sources.add_purple("my_ds_name")

    # 4. Add a DataAsset
    red_asset: DataAsset = purple_ds.add_red_asset("my_asset_name")
    assert isinstance(red_asset, RedAsset)

    # 5. Get an asset by name - (method defined in parent `Datasource`)
    assert red_asset is purple_ds.get_asset("my_asset_name")


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "--log-level=DEBUG"])
