# Magik Data Nodes — 1.2.0

Ten consolidated ComfyUI custom nodes, implemented independently with Python's
standard library. No pip packages, original pack, network access or expression eval required.

As of 1.1.0 this pack absorbs the deprecated comfyui-magik-basic-nodes
and as of 1.2.0 the deprecated comfyui-magik-integer-loop. As before: the four
As before: the four
unique basic nodes are included unchanged, and the unique features of basic's
overlapping nodes have been folded into their consolidated counterparts. Remove
the old basic and integer-loop packs before installing: basic registered
colliding node IDs (`MagikBoolean`, `MagikCompare`), and both packs would register
`IntegerLoop` twice.

## Install

Extract `magik_data_nodes` into `~/Apps/comfyui/custom_nodes/`, restart ComfyUI,
then refresh the browser. Find the nodes under **Magik / Data**
(Convert, Math and Inspect subcategories for the ported utilities).
Keep this folder as a standalone custom node pack. Existing Magik nodes with the
same registration IDs must be removed or renamed before installation to avoid
registration collisions.

## Nodes

### Magik Boolean

AND, NAND, OR, NOR, NOT, XOR, XNOR and VALUE. `a` and `b` are Boolean widgets;
`a_input` and `b_input` override them when connected. Strict mode requires actual
booleans. Generic mode uses Python truthiness (zero, empty containers, None and
empty text are false; the text "False" is true). Tensor/array truth ambiguity
raises an actionable error rather than silently reducing the input.

Add/remove operand buttons provide up to 128 extra inputs. AND/OR and inverted
variants combine all operands. XOR uses odd parity; XNOR uses even parity.
NOT and VALUE use only A. Outputs: result, inverse, int (0/1) and string
(false/true). The int/string outputs replace Magik Basic Nodes' boolean emitter;
this fully supersedes basic's Magik Logic as well.

### Magik Compare

Modes: Values, String, Length, Is null, In range. Relations `==`, `!=`, `<`,
`<=`, `>`, `>=`, plus `contains`, `starts with` and `ends with` (String mode only,
ported from Magik Basic Nodes).

- Values uses Python structural equality/order; incompatible types raise errors.
  When both sides are numeric and a tolerance greater than zero is set, numbers
  within the tolerance count as equal: inclusive relations include them and
  strict relations exclude them (replaces basic's Number mode).
- String uses text widgets, optionally overridden by connected A/B strings.
  Case-insensitive comparison uses Unicode casefolding.
- Length compares `len(a)` against the length widget. A value with no length
  returns false and actual_length=-1.
- Is null tests `a is None`.
- In range uses A and individually inclusive/exclusive minimum/maximum bounds.
  Reversed bounds raise an error.

Outputs: result, inverse, actual_length (-1 outside Length mode).

### Magik Control Flow

- **if/else:** condition selects if_true or if_false.
- **if/elif/else:** evaluates connected condition_0, condition_1, ... in order;
  returns the first matching branch_N, otherwise default. The condition widget
  is used only by if/else and gate/routing modes.
- **switch/case:** zero-based select chooses branch_N; out-of-range or an
  unconnected branch selects default. A connected branch returning None stays None.
- **continue if not empty:** blocks an empty execution list or a falsy value;
  otherwise passes it through. A list containing 0/False is nonempty and passes.
- **continue flow:** condition=false blocks downstream without requesting value.
- **flow select:** sends value to the true or false output and blocks the other.
- **force calculation:** marks this node as changed for every queue execution.
  This does not invalidate ComfyUI's cached upstream computations. The original
  pack's “force calculation” also cannot guarantee ancestor recalculation.
- **force execution order:** requests dependency before value. This orders their
  evaluation when they are not already requested elsewhere; it cannot serialize
  independent consumers elsewhere in the workflow. Result passes value through.
- **is connected:** inspects the graph's value link without evaluating its source;
  a link returning None still counts as connected.

input_count configures 2–128 numbered branch/condition pairs. The frontend
preserves connected sockets when reducing the count. Unused sockets remain
lazy. Branch selection requests only the selected branch and preceding conditions.

Outputs: result / true, false, is_connected (the value socket's link state).
The false output is blocked except in flow select. is connected also places its
Boolean result on the first output. Optional message is shown by ComfyUI when
blocking; empty means silent. This node is an output node so it can anchor
execution. Entire Comfy execution lists pass through intact, including empty
lists; the selector and condition controls use their first mapped value.

### Magik Maths

add, subtract, multiply, divide, divide (zero safe), floor divide, modulus,
power, round, plus average, negate, clamp and map range (ported from
Magik Basic Nodes). Connected A/B override a_value/b_value. Numeric strings are
accepted; booleans and nonfinite values are rejected. Round uses Python's
round-to-even rule with the digits widget. Safe division uses zero_fallback
only when B is zero. Ordinary divide raises on zero.

Clamp uses minimum/maximum and accepts reversed bounds. Map range maps A from
minimum…maximum to output_minimum…output_maximum, supports descending ranges,
and optionally clamps to the input range; equal input bounds raise an error.
Other operations ignore the range widgets.

Outputs: result (preserves integer arithmetic), FLOAT and INT. INT truncates
toward zero; integer precision is preserved on result (FLOAT can lose precision).
Complex results and overflowing/nonfinite conversions raise errors. Exponents
are limited to magnitude 10000 to prevent accidental enormous power operations.

### Magik Math Const&Functions

abs, acos, asin, atan, atan2, ceil, cos, degrees, e, exp, floor, log, log10,
max, min, pi, radians, sin, sqrt and tan.

Connected A/B override numeric widgets. atan2 uses A=y and B=x. log uses base.
Unit selects degrees/radians for trig input and inverse trig output. degrees
always converts radians to degrees; radians always converts degrees to radians.
e and pi use full Python precision and request no connected operands.
Domain errors (negative square root, invalid logarithm, etc.) raise errors;
tangent rejects angles where abs(cos(angle)) < 1e-10.

Outputs: result, FLOAT and INT (truncates toward zero).

### Magik Type Convert

Convert any scalar to String, Integer, Float or Boolean (Magik/Data/Convert).
The converted socket is wildcard so it can connect to the selected target type:
choose a target matching the receiving input.

Integer rounding: Truncate (toward zero), Round (ties to even), Floor, Ceil.
Exact integer strings preserve precision. String conversion accepts scalars and
None; padding applies to integer inputs, includes the sign, and never truncates.
Boolean text explicitly parses true/false, yes/no, on/off, 1/0, or empty; numeric
zero is false and other finite numbers are true. Booleans convert to 1.0/0.0
for Float. Invalid conversions stop with an error. These are scalar utilities;
use Magik Show Any to inspect tensors and objects.

### Magik Float

Editable float with 0.01 arrow increments (Magik/Data/Math). Precision (0–12)
rounds the FLOAT output and formats the STRING output with fixed decimal places.
Python ties-to-even rounding applies. Controls persist through normal workflow
serialization.

### Magik Length

Auto: text → line count; dictionary → entries; IMAGE tensor → batch count;
Python containers/ComfyUI execution lists → element count (Magik/Data/Inspect).
Auto never opens files. Select Text file lines to read a local UTF-8/UTF-16/Latin-1
file by path; files are streamed. Paths refer to the ComfyUI server machine.
Supports character counts and optional exclusion of blank/whitespace-only lines.
Empty text is 0 lines; a final newline terminates the last line without adding
an extra line. File mode follows standard text-file newline conventions (LF,
CRLF, CR). Text lines additionally recognizes Python splitlines Unicode
separators. Characters are Unicode code points. ComfyUI list mapping is disabled
on this node so it counts complete execution lists.

### Magik Image Info

Passes IMAGE through unchanged and outputs width, height, batch count, channels,
numeric width/height ratio, reduced ratio text, megapixels per image, and a
summary including dtype/device (Magik/Data/Inspect). Reads tensor metadata
only, without pixel conversion or GPU synchronization. Expects the standard
ComfyUI IMAGE layout [batch, height, width, channels].

## Validation

Run from the pack folder:

```
python -m unittest discover -s tests -v
node tests/test_frontend.mjs
```

Tests cover truth tables, generic/strict typing, comparison boundaries,
tolerance and text relations, arithmetic and all 20 functions, the ported
clamp/map-range operations, lazy branch requests, blockers, connection
detection, list-level execution, dependency ordering, the four ported nodes,
registration (9 nodes), and frontend socket creation/restoration. ComfyUI's
blocker is stubbed for standalone tests; a live ComfyUI/browser integration test
is still required on your installation.


### Magik Integer Loop

Editable integer widget, clamped to Min/Max on every execution; reversed
bounds are swapped. **Control after Generate** is handled by the frontend
(web/integer_loop.js): between queued prompts the Output widget shows Fixed,
Increment, Decrement or Randomize within the bounds; Loop wraps at the bounds
instead of pinning. The queued prompt keeps the value it was serialized with.
Works like a KSampler seed control for any integer input. Node ID is
`IntegerLoop` (kept from the original pack so the frontend keeps matching).
