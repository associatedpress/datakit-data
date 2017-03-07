import pytest

from datakit_data.extra_flags import ExtraFlags


@pytest.mark.parametrize("flags", [
    [["dryrun"], ["--dryrun"]],
    [["dryrun", "delete"], ["--dryrun", "--delete"]]
])
def test_boolean_conversion(flags):
    actual = ExtraFlags.convert(flags[0])
    expected = flags[1]
    assert actual == expected
