# z3c.form support for native color widget <input type="color" />, which is
# supported in recent Chrome/Firefox http://caniuse.com/#feat=input-color

from z3c.form import widget
from z3c.form.browser import text
from z3c.form.interfaces import IWidget
from zope.interface import implementsOnly


class INativeColorInput(IWidget):
    """Marker interface for native color input"""


class NativeColorInput(text.TextWidget):
    """Native HTML5 input type color"""

    implementsOnly(INativeColorInput)


def NativeColorFieldWidget(field, request):
    """Field widget factory for NativeColorInput"""
    return widget.FieldWidget(field, NativeColorInput(request))

