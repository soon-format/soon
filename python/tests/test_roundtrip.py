"""Property-based round-trip guarantee: decode(encode(x)) == x, always."""

from hypothesis import given, settings
from hypothesis import strategies as st

from soon_format import decode, encode

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**53), max_value=2**53)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=40),
    lambda children: st.lists(children, max_size=8)
    | st.dictionaries(st.text(max_size=20), children, max_size=8),
    max_leaves=60,
)

# Nested-shaped data: the format's sweet spot, exercised heavily.
records = st.lists(
    st.fixed_dictionaries(
        {"id": st.integers(), "name": st.text(max_size=20)},
        optional={
            "tags": st.lists(st.text(max_size=8), max_size=4),
            "meta": st.dictionaries(st.text(max_size=8), st.integers(), max_size=4),
            "children": st.lists(
                st.fixed_dictionaries({"k": st.text(max_size=8), "v": st.integers()}),
                max_size=3,
            ),
        },
    ),
    max_size=10,
)


@settings(max_examples=300, deadline=None)
@given(json_values)
def test_roundtrip_arbitrary_json(value):
    for mode in ("auto", "soon"):
        assert decode(encode(value, mode=mode)) == value


@settings(max_examples=300, deadline=None)
@given(records)
def test_roundtrip_shaped_records(rows):
    value = {"rows": rows}
    for mode in ("auto", "soon"):
        assert decode(encode(value, mode=mode)) == value
