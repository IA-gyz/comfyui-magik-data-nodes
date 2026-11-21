import { app } from '../../scripts/app.js';

const INT_MIN = -2147483648;
const INT_MAX = 2147483647;
const integer = (value, fallback) => {
    const number = Number(value);
    return Number.isFinite(number)
        ? Math.max(INT_MIN, Math.min(INT_MAX, Math.trunc(number)))
        : fallback;
};

app.registerExtension({
    name: "Comfy.IntegerLoop",
    nodeCreated(node) {
        if (node.comfyClass !== "IntegerLoop") return;
        const find = (name) => node.widgets?.find((widget) => widget.name === name);
        const output = find("Output");
        const minimum = find("Min");
        const maximum = find("Max");
        const loop = find("Loop");
        const control = find("Control after Generate");
        if (!output || !minimum || !maximum || !control) return;

        const bounds = () => {
            const a = integer(minimum.value, 0);
            const b = integer(maximum.value, 100);
            return [Math.min(a, b), Math.max(a, b)];
        };
        const refresh = () => {
            const index = node.widgets.indexOf(output);
            if (index >= 0 && Array.isArray(node.widgets_values)) {
                node.widgets_values[index] = output.value;
            }
            node.setDirtyCanvas?.(true, true);
            app.graph?.setDirtyCanvas?.(true, true);
        };
        const updateBounds = () => {
            const [min, max] = bounds();
            output.options ??= {};
            output.options.min = min;
            output.options.max = max;
            output.value = Math.max(min, Math.min(max, integer(output.value, min)));
            refresh();
        };
        for (const widget of [minimum, maximum, output]) {
            const previous = widget.callback;
            widget.callback = function (...args) {
                const result = previous?.apply(this, args);
                updateBounds();
                return result;
            };
        }

        // Runs after prompt serialization, including each item in a queue batch.
        // The queued prompt keeps its value; the widget shows the next value.
        const previousAfterQueued = output.afterQueued;
        output.afterQueued = function (...args) {
            previousAfterQueued?.apply(this, args);
            updateBounds();
            const [min, max] = bounds();
            let next = output.value;
            switch (control.value) {
                case "Increment":
                    next = next < max ? next + 1 : (loop?.value ? min : max);
                    break;
                case "Decrement":
                    next = next > min ? next - 1 : (loop?.value ? max : min);
                    break;
                case "Randomize":
                    next = min + Math.floor(Math.random() * (max - min + 1));
                    break;
            }
            output.value = next;
            output.callback?.call(output, next);
            refresh();
        };

        // Workflow values are restored after nodeCreated.
        const previousConfigure = node.onConfigure;
        node.onConfigure = function (...args) {
            const result = previousConfigure?.apply(this, args);
            updateBounds();
            return result;
        };
        updateBounds();
    },
});
