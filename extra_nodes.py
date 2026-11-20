"""Nodes ported from comfyui-magik-basic-nodes (that pack is deprecated).
Uses the consolidated pack's stricter number() coercion throughout."""
import math
from pathlib import Path

from .nodes import ANY, Base, number


class MagikTypeConvert(Base):
    CATEGORY = 'Magik/Data/Convert'
    DESCRIPTION = 'Convert any scalar to String, Integer, Float or Boolean. Integer rounding: truncate/round/floor/ceil. Padding zero-fills integer strings, including the sign.'
    RETURN_TYPES = (ANY,)
    RETURN_NAMES = ('converted',)

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'value': (ANY,),
            'target': (['String', 'Integer', 'Float', 'Boolean'],),
            'integer_rounding': (['Truncate', 'Round', 'Floor', 'Ceil'],),
            'padding': ('INT', {'default': 1, 'min': 1, 'max': 99}),
        }}

    def execute(self, value, target, integer_rounding='Truncate', padding=1):
        if target == 'String':
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise TypeError('String conversion accepts scalar values only.')
            result = ('true' if value else 'false') if isinstance(value, bool) else str(value)
            if isinstance(value, int) and not isinstance(value, bool):
                result = result.zfill(padding)
        elif target == 'Integer':
            if isinstance(value, (int, bool)):
                result = int(value)
            elif isinstance(value, str) and value.strip().lstrip('+-').isdigit():
                result = int(value.strip())
            else:
                rounding = {'Truncate': int, 'Round': round, 'Floor': math.floor, 'Ceil': math.ceil}
                result = int(rounding[integer_rounding](number(value)))
        elif target == 'Float':
            # The consolidated number() rejects booleans; convert them explicitly.
            result = float(value) if isinstance(value, bool) else number(value)
        elif target == 'Boolean':
            if isinstance(value, bool):
                result = value
            elif isinstance(value, (int, float)):
                result = number(value) != 0
            elif isinstance(value, str):
                text = value.strip().casefold()
                if text in ('true', 'yes', 'on', '1'):
                    result = True
                elif text in ('false', 'no', 'off', '0', ''):
                    result = False
                else:
                    raise ValueError('Boolean text must be true/false, yes/no, on/off, 1/0, or empty.')
            else:
                raise TypeError(f'Cannot convert {type(value).__name__} to Boolean.')
        else:
            raise ValueError(f'Unknown conversion target: {target}')
        return (result,)


class MagikFloat(Base):
    CATEGORY = 'Magik/Data/Math'
    DESCRIPTION = 'Editable float widget with 0.01 increments. Precision rounds the FLOAT output and formats the STRING output with fixed decimals.'
    RETURN_TYPES = ('FLOAT', 'STRING')
    RETURN_NAMES = ('float', 'string')

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'value': ('FLOAT', {'default': 0.0, 'min': -1e100, 'max': 1e100, 'step': 0.01}),
            'precision': ('INT', {'default': 3, 'min': 0, 'max': 12}),
        }}

    def execute(self, value, precision):
        if not math.isfinite(value):
            raise ValueError('Magik Float requires a finite value.')
        value = round(float(value), precision)
        return (value, f'{value:.{precision}f}')


def image_shape(image):
    shape = getattr(image, 'shape', None)
    if shape is None or len(shape) != 4:
        raise ValueError('Expected a ComfyUI IMAGE batch with shape [batch, height, width, channels].')
    batch, height, width, channels = map(int, shape)
    if batch < 0 or min(height, width, channels) <= 0:
        raise ValueError('Invalid image dimensions.')
    return batch, height, width, channels


class MagikLength(Base):
    CATEGORY = 'Magik/Data/Inspect'
    DESCRIPTION = 'Count list elements, text lines, characters, dictionary entries, image batch size or lines in a text file. Auto infers the mode; it never opens files.'
    INPUT_IS_LIST = True
    RETURN_TYPES = ('INT',)
    RETURN_NAMES = ('length',)

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'value': (ANY,),
            'mode': (['Auto', 'Text lines', 'Text characters', 'Text file lines',
                       'List elements', 'Image batch', 'Dictionary entries'],),
            'include_empty_lines': ('BOOLEAN', {'default': True}),
            'encoding': (['utf-8-sig', 'utf-8', 'utf-16', 'latin-1'],),
        }}

    def execute(self, value, mode, include_empty_lines, encoding):
        mode, include_empty_lines, encoding = mode[0], include_empty_lines[0], encoding[0]
        # A single socket value is wrapped by ComfyUI; multi-item execution
        # lists stay lists and a nested Python list stays the payload.
        payload = value[0] if len(value) == 1 else value
        if mode == 'Auto':
            if len(value) != 1:
                mode = 'List elements'
            elif isinstance(payload, str):
                mode = 'Text lines'
            elif isinstance(payload, dict):
                mode = 'Dictionary entries'
            elif hasattr(payload, 'shape') and len(payload.shape) == 4:
                mode = 'Image batch'
            elif isinstance(payload, (list, tuple, set, frozenset)):
                mode = 'List elements'
            else:
                raise ValueError('Magik Length cannot infer this datatype; select a mode.')
        if mode == 'List elements':
            length = len(payload) if isinstance(payload, (list, tuple, set, frozenset)) else len(value)
        elif mode == 'Image batch':
            length = sum(image_shape(image)[0] for image in value)
        elif mode == 'Dictionary entries':
            if not isinstance(payload, dict):
                raise TypeError('Dictionary entries requires a dictionary.')
            length = len(payload)
        elif mode in ('Text lines', 'Text characters', 'Text file lines'):
            if not isinstance(payload, str):
                raise TypeError(f'{mode} requires one string input.')
            if mode == 'Text file lines':
                # Explicit file mode only: Auto never treats text as a path.
                try:
                    with Path(payload).expanduser().open('r', encoding=encoding) as stream:
                        length = sum(1 for line in stream if include_empty_lines or line.strip())
                except (OSError, UnicodeError, ValueError) as exc:
                    raise ValueError(f'Magik Length could not read the text file: {exc}') from exc
            elif mode == 'Text characters':
                length = len(payload)
            else:
                lines = payload.splitlines()
                length = len(lines) if include_empty_lines else sum(bool(line.strip()) for line in lines)
        else:
            raise ValueError(f'Unknown length mode: {mode}')
        return (length,)


class MagikImageInfo(Base):
    CATEGORY = 'Magik/Data/Inspect'
    DESCRIPTION = 'Pass IMAGE through unchanged and report width, height, batch count, channels, aspect ratio, megapixels and a summary. Reads tensor metadata only; no pixel conversion or GPU synchronization.'
    RETURN_TYPES = ('IMAGE', 'INT', 'INT', 'INT', 'INT', 'FLOAT', 'STRING', 'FLOAT', 'STRING')
    RETURN_NAMES = ('image', 'width', 'height', 'batch_count', 'channels',
                    'aspect_ratio', 'aspect_ratio_text', 'megapixels', 'summary')

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'image': ('IMAGE',)}}

    def execute(self, image):
        batch, height, width, channels = image_shape(image)
        divisor = math.gcd(width, height)
        ratio = f'{width // divisor}:{height // divisor}'
        megapixels = width * height / 1_000_000
        summary = (f'{width} × {height} | {ratio} | {megapixels:.3f} MP per image\n'
                   f'Batch: {batch} | Channels: {channels}\n'
                   f'Dtype: {getattr(image, "dtype", "unknown")} | Device: {getattr(image, "device", "unknown")}')
        return (image, width, height, batch, channels, width / height, ratio, megapixels, summary)


NODE_CLASS_MAPPINGS = {c.__name__: c for c in (MagikTypeConvert, MagikFloat, MagikLength, MagikImageInfo)}
NODE_DISPLAY_NAME_MAPPINGS = dict(zip(NODE_CLASS_MAPPINGS,
                                      ('Magik Type Convert', 'Magik Float', 'Magik Length', 'Magik Image Info')))
