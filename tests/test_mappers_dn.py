# -*- coding: utf-8 -*-
import pytest


def test_dn_mapper_removed_import():
    with pytest.raises(ModuleNotFoundError):
        __import__("services.mappers.datanewton")


def test_dn_mapper_removed_usage():
    with pytest.raises(ModuleNotFoundError):
        __import__("services.providers.datanewton")


def test_dn_finance_removed():
    with pytest.raises(ModuleNotFoundError):
        __import__("services.mappers.datanewton")


