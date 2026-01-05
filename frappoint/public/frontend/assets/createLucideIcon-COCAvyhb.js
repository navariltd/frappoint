var $=Object.defineProperty,L=Object.defineProperties;var j=Object.getOwnPropertyDescriptors;var n=Object.getOwnPropertySymbols;var p=Object.prototype.hasOwnProperty,C=Object.prototype.propertyIsEnumerable;var g=(t,e,r)=>e in t?$(t,e,{enumerable:!0,configurable:!0,writable:!0,value:r}):t[e]=r,s=(t,e)=>{for(var r in e||(e={}))p.call(e,r)&&g(t,r,e[r]);if(n)for(var r of n(e))C.call(e,r)&&g(t,r,e[r]);return t},l=(t,e)=>L(t,j(e));var f=(t,e)=>{var r={};for(var o in t)p.call(t,o)&&e.indexOf(o)<0&&(r[o]=t[o]);if(t!=null&&n)for(var o of n(t))e.indexOf(o)<0&&C.call(t,o)&&(r[o]=t[o]);return r};import{G as u}from"./index-DfkK5Zd4.js";/**
 * @license lucide-vue-next v0.554.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const k=t=>t.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase(),B=t=>t.replace(/^([A-Z])|[\s-_]+(\w)/g,(e,r,o)=>o?o.toUpperCase():r.toLowerCase()),I=t=>{const e=B(t);return e.charAt(0).toUpperCase()+e.slice(1)},U=(...t)=>t.filter((e,r,o)=>!!e&&e.trim()!==""&&o.indexOf(e)===r).join(" ").trim(),v=t=>t==="";/**
 * @license lucide-vue-next v0.554.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */var c={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"};/**
 * @license lucide-vue-next v0.554.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Z=(y,{slots:h})=>{var m=y,{name:t,iconNode:e,absoluteStrokeWidth:r,"absolute-stroke-width":o,strokeWidth:i,"stroke-width":w,size:a=c.width,color:x=c.stroke}=m,d=f(m,["name","iconNode","absoluteStrokeWidth","absolute-stroke-width","strokeWidth","stroke-width","size","color"]);return u("svg",l(s(s({},c),d),{width:a,height:a,stroke:x,"stroke-width":v(r)||v(o)||r===!0||o===!0?Number(i||w||c["stroke-width"])*24/Number(a):i||w||c["stroke-width"],class:U("lucide",d.class,...t?[`lucide-${k(I(t))}-icon`,`lucide-${k(t)}`]:["lucide-icon"])}),[...e.map(A=>u(...A)),...h.default?[h.default()]:[]])};/**
 * @license lucide-vue-next v0.554.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const O=(t,e)=>(r,{slots:o,attrs:i})=>u(Z,l(s(s({},i),r),{iconNode:e,name:t}),o);export{O as c};
//# sourceMappingURL=createLucideIcon-COCAvyhb.js.map
