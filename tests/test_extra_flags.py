import pytest

from datakit_data.extra_flags import ExtraFlags


@pytest.mark.parametrize("flags", [
    [["dryrun"], ["--dryrun"]],
    [["dryrun", "delete"], ["--dryrun", "--delete"]]
])
def test_boolean_conversion(flags):
    """
    ExtraFlags.convert prefixes each flag name with '--'.
    """
    actual = ExtraFlags.convert(flags[0])
    expected = flags[1]
    assert actual == expected


def test_unsupported_returns_unknown_flags():
    """
    ExtraFlags.unsupported lists flags that the plugin does not act on, preserving order.
    """
    assert ExtraFlags.unsupported(['dryrun', 'delete', 'bogus', 'exclude']) == ['bogus', 'exclude']


def test_unsupported_empty_when_all_known():
    """
    ExtraFlags.unsupported is empty when every flag is supported.
    """
    assert ExtraFlags.unsupported(['dryrun', 'dry-run', 'delete']) == []
