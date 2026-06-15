from decimal import Decimal

import pytest
from django import forms

from unsphere.units import u
from workouts.fields import (
    DISTANCE_UNITS,
    WEIGHT_UNITS,
    PintFormField,
    PintTimeFormField,
    PintTimeWidget,
    PintWidget,
)


# --- PintFormField ----------------------------------------------------------


def test_pintformfield_compress_valid():
    field = PintFormField(DISTANCE_UNITS, required=False)
    assert field.compress([Decimal("5"), "mile"]) == u("5 miles")


def test_pintformfield_compress_empty_returns_none():
    field = PintFormField(DISTANCE_UNITS, required=False)
    assert field.compress([None, ""]) is None


def test_pintformfield_compress_missing_unit_errors():
    field = PintFormField(DISTANCE_UNITS, required=False)
    with pytest.raises(forms.ValidationError, match="unit"):
        field.compress([Decimal("5"), ""])


def test_pintformfield_compress_disallowed_unit_errors():
    # A weight unit is not selectable on a distance field.
    field = PintFormField(DISTANCE_UNITS, required=False)
    with pytest.raises(forms.ValidationError, match="unit"):
        field.compress([Decimal("5"), "pound"])


def test_pintformfield_choices_match_unit_set():
    distance = PintFormField(DISTANCE_UNITS, required=False)
    assert distance.allowed_units == {"mile", "foot", "kilometer", "meter"}
    weight = PintFormField(WEIGHT_UNITS, required=False)
    assert weight.allowed_units == {"pound", "kilogram"}


def test_pintwidget_decompress_quantity():
    assert PintWidget(DISTANCE_UNITS).decompress(u("3 mile")) == [3.0, "mile"]


def test_pintwidget_decompress_empty():
    assert PintWidget(DISTANCE_UNITS).decompress(None) == [None, ""]


# --- PintTimeFormField ------------------------------------------------------


def test_pinttimefield_compress_valid():
    field = PintTimeFormField(required=False)
    assert field.compress([5, 30]) == u("5 min") + u("30 s")


def test_pinttimefield_compress_zero_returns_none():
    field = PintTimeFormField(required=False)
    assert field.compress([0, 0]) is None


def test_pinttimewidget_decompress_quantity():
    # 5 min 30 s == 330 s
    assert PintTimeWidget().decompress(u("330 second")) == [5, 30]


def test_pinttimewidget_decompress_empty():
    assert PintTimeWidget().decompress(None) == [0, 0]


def test_pinttimewidget_render_is_safe_html():
    from django.utils.safestring import SafeString

    html = PintTimeWidget().render("duration", None, attrs={"id": "id_duration"})
    # Must be marked safe so the template doesn't escape the <input> tags.
    assert isinstance(html, SafeString)
    assert "<input" in html
    assert "&lt;input" not in html
