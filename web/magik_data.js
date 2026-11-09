import { app } from '../../scripts/app.js';

app.registerExtension({
    name: 'Magik.DataNodes',
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (!['MagikBoolean', 'MagikControlFlow'].includes(nodeData.name)) return;
        const original = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            original?.apply(this, arguments);
            const node = this;
            const flow = nodeData.name === 'MagikControlFlow';
            const rebuild = () => {
                const count = flow ? Math.max(2, Math.min(128, Number(node.widgets.find(w => w.name === 'input_count')?.value ?? 2))) : (node.properties.extra_inputs ?? 0);
                const desired = new Map();
                for (let i = 0; i < count; i++) {
                    if (flow) {
                        desired.set(`condition_${i}`, 'BOOLEAN');
                        desired.set(`branch_${i}`, '*');
                    } else desired.set(`item_${i}`, '*');
                }
                // Never discard a connected socket when reducing the count.
                const pattern = flow ? /^(condition|branch)_\d+$/ : /^item_\d+$/;
                for (let i = (node.inputs?.length ?? 0) - 1; i >= 0; i--) {
                    const input = node.inputs[i];
                    if (pattern.test(input.name) && !desired.has(input.name) && input.link == null) node.removeInput(i);
                }
                for (const [name, type] of desired) {
                    if (!node.inputs?.some(input => input.name === name)) node.addInput(name, type);
                }
                node.setDirtyCanvas(true, true);
            };
            if (flow) {
                const widget = node.widgets.find(w => w.name === 'input_count');
                const previous = widget.callback;
                widget.callback = function () {
                    previous?.apply(this, arguments);
                    // Keep count consistent with retained connected sockets.
                    const highest = Math.max(-1, ...(node.inputs ?? []).filter(i => /^(condition|branch)_\d+$/.test(i.name) && i.link != null).map(i => Number(i.name.split('_')[1])));
                    widget.value = Math.max(widget.value, highest + 1);
                    rebuild();
                };
            } else {
                node.properties ??= {};
                node.properties.extra_inputs ??= 0;
                node.addWidget('button', 'Add operand', null, () => {
                    node.properties.extra_inputs = Math.min(128, node.properties.extra_inputs + 1);
                    rebuild();
                }, { serialize: false });
                node.addWidget('button', 'Remove operand', null, () => {
                    const last = node.inputs?.find(i => i.name === `item_${node.properties.extra_inputs - 1}`);
                    if (last?.link != null) return;
                    node.properties.extra_inputs = Math.max(0, node.properties.extra_inputs - 1);
                    rebuild();
                }, { serialize: false });
            }
            const configure = node.onConfigure;
            node.onConfigure = function () {
                configure?.apply(this, arguments);
                rebuild();
            };
            rebuild();
        };
    }
});
