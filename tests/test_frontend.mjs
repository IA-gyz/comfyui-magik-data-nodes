import fs from 'node:fs';
import assert from 'node:assert/strict';
let extension;
globalThis.app = { registerExtension: e => extension = e };
const source = fs.readFileSync(new URL('../web/magik_data.js', import.meta.url), 'utf8').replace("import { app } from '../../scripts/app.js';", 'const app = globalThis.app;');
await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
class Node {
    constructor(flow) {
        this.inputs=[];this.properties={};this.widgets=flow?[{name:'input_count',value:2}]:[];
    }
    addInput(name,type) {this.inputs.push({name,type,link:null});}
    removeInput(i) {this.inputs.splice(i,1);}
    addWidget(type,name,value,callback,options) {this.widgets.push({type,name,value,callback,options});}
    setDirtyCanvas() {}
}
for (const [name, flow] of [['MagikControlFlow',true],['MagikBoolean',false]]) {
    class TestNode extends Node {}
    await extension.beforeRegisterNodeDef(TestNode,{name});
    const node=new TestNode(flow);
    node.onNodeCreated();
    if (flow) {
        assert.equal(node.inputs.length,4);
        const count=node.widgets[0];count.value=4;count.callback();
        assert.equal(node.inputs.length,8);
        node.inputs.find(i=>i.name==='branch_3').link=1;
        count.value=2;count.callback();assert.equal(count.value,4);
        node.inputs.find(i=>i.name==='branch_3').link=null;
        count.value=2;count.callback();assert.equal(node.inputs.length,4);
        node.onConfigure();assert.equal(node.inputs.length,4);
    } else {
        node.widgets[0].callback();node.widgets[0].callback();
        assert.equal(node.inputs.length,2);
        node.inputs[1].link=1;node.widgets[1].callback();assert.equal(node.inputs.length,2);
        node.inputs[1].link=null;node.widgets[1].callback();assert.equal(node.inputs.length,1);
        node.onConfigure();assert.equal(node.inputs.length,1);
    }
}
console.log('Frontend: socket creation, connected-socket protection and reconfiguration passed.');
