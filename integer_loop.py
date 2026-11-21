"""Magik Integer Loop, ported unchanged from the comfyui-magik-integer-loop pack
(deprecated). The node ID and widget names are kept identical so the existing
frontend behaviour (bounds clamping and Control after Generate) still matches."""
from .nodes import Base


class IntegerLoop(Base):
    CATEGORY = 'Magik/Data'
    DESCRIPTION = 'Editable integer clamped to Min/Max. Control after Generate (frontend) increments, decrements or randomizes the widget between queued prompts; Loop wraps at the bounds. Reversed bounds are swapped.'
    RETURN_TYPES = ('INT',)
    RETURN_NAMES = ('Int',)
    INPUT_IS_LIST = False

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'Output': ('INT', {'default': 0, 'min': -2147483648, 'max': 2147483647, 'step': 1}),
            'Min': ('INT', {'default': 0, 'min': -2147483648, 'max': 2147483647, 'step': 1}),
            'Max': ('INT', {'default': 100, 'min': -2147483648, 'max': 2147483647, 'step': 1}),
            'Loop': ('BOOLEAN', {'default': True}),
            'Control after Generate': (['Fixed', 'Increment', 'Decrement', 'Randomize'],),
        }}

    def execute(self, Output, Min, Max, Loop, **kwargs):
        if Min > Max:
            Min, Max = Max, Min
        return (max(Min, min(Max, Output)),)


# Kept as registration 'IntegerLoop': the web extension keys on the node class.
NODE_CLASS_MAPPINGS = {'IntegerLoop': IntegerLoop}
NODE_DISPLAY_NAME_MAPPINGS = {'IntegerLoop': 'Magik Integer Loop'}
