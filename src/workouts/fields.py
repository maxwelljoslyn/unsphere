from django import forms
from django.db import models
from django.utils.safestring import mark_safe
from pint import Quantity

from parrot.units import u


class PintField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 100)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if not value:
            return None
        return u(value)

    def to_python(self, value):
        if isinstance(value, Quantity):
            return value
        if not value:
            return None
        return u(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(value)

    def run_validators(self, value):
        # The Python value here is a pint Quantity, but CharField's inherited
        # MaxLengthValidator calls len() on it (which fails). Validate the
        # stored string form instead — that's what the 100-char bound applies to.
        if value is not None:
            value = self.get_prep_value(value)
        super().run_validators(value)


# ---------------------------------------------------------------------------
# Form widgets
# ---------------------------------------------------------------------------


class PintWidget(forms.MultiWidget):
    """[magnitude: number input, unit: text input]"""

    def __init__(self, attrs=None):
        widgets = [
            forms.NumberInput(attrs={"step": "any", "min": "0"}),
            forms.TextInput(attrs={"placeholder": "unit"}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return [None, ""]
        if isinstance(value, Quantity):
            return [float(value.magnitude), str(value.units)]
        try:
            q = u(value)
            return [float(q.magnitude), str(q.units)]
        except Exception:
            return [None, ""]


class PintTimeWidget(forms.MultiWidget):
    """[minutes: number input, seconds: number input] — units are fixed and displayed as labels."""

    def __init__(self, attrs=None):
        widgets = [
            forms.NumberInput(attrs={"min": "0", "step": "1"}),
            forms.NumberInput(attrs={"min": "0", "max": "59", "step": "1"}),
        ]
        super().__init__(widgets, attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if not isinstance(value, list):
            value = self.decompress(value)
        while len(value) < 2:
            value.append(0)
        final_attrs = self.build_attrs(attrs or {})
        id_ = final_attrs.get("id")
        parts = []
        for i, (widget, label) in enumerate(zip(self.widgets, ("min", "sec"))):
            widget_attrs = {**final_attrs, "id": f"{id_}_{i}"} if id_ else final_attrs
            rendered = widget.render(
                f"{name}_{i}", value[i] if value[i] is not None else 0, widget_attrs
            )
            parts.append(f"{rendered} {label}")
        return mark_safe(" &nbsp; ".join(parts))

    def decompress(self, value):
        if not value:
            return [0, 0]
        try:
            total_s = float(
                (value if isinstance(value, Quantity) else u(value))
                .to("second")
                .magnitude
            )
        except Exception:
            return [0, 0]
        return [int(total_s // 60), int(total_s % 60)]


# ---------------------------------------------------------------------------
# Form fields
# ---------------------------------------------------------------------------


class PintFormField(forms.MultiValueField):
    widget = PintWidget

    def __init__(self, *args, **kwargs):
        fields = [
            forms.DecimalField(min_value=0),
            forms.CharField(),
        ]
        kwargs.setdefault("require_all_fields", False)
        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        if not data_list or not data_list[0]:
            return None
        magnitude = data_list[0]
        unit = data_list[1].strip() if len(data_list) > 1 and data_list[1] else ""
        if not unit:
            raise forms.ValidationError("Enter a unit (e.g. 'miles', 'lbs').")
        try:
            return u(f"{magnitude} {unit}")
        except Exception:
            raise forms.ValidationError(
                f"'{unit}' is not a recognized unit. Try 'miles', 'feet', 'lbs', 'kg', etc."
            )


class PintTimeFormField(forms.MultiValueField):
    widget = PintTimeWidget

    def __init__(self, *args, **kwargs):
        fields = [
            forms.IntegerField(min_value=0),
            forms.IntegerField(min_value=0, max_value=59),
        ]
        kwargs.setdefault("require_all_fields", False)
        super().__init__(fields=fields, *args, **kwargs)

    def compress(self, data_list):
        minutes = int(data_list[0] or 0) if data_list else 0
        seconds = int(data_list[1] or 0) if len(data_list) > 1 else 0
        if minutes == 0 and seconds == 0:
            return None
        return u(f"{minutes} min") + u(f"{seconds} s")
