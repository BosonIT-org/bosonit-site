import * as d3 from 'd3';

export default function initSparklines(selector = '.sparkline, [data-sparkline-id], .microspark') {
  const nodes = Array.from(document.querySelectorAll(selector));
  if (!nodes.length) return;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  nodes.forEach((el, i) => { const id = el.getAttribute('data-sparkline-id') || `spark-${i}`; render(el, id, reduceMotion); });
}

function render(el, id, reduceMotion){
  const W = Math.max(120, el.clientWidth || 160), H = el.clientHeight || 36, P = 4;
  const svg = d3.select(el).append('svg').attr('width', W).attr('height', H);
  const g = svg.append('g').attr('transform', `translate(${P},${P})`);
  const w = W - P*2, h = H - P*2;
  let s = (id.split('').reduce((a,c)=>a+c.charCodeAt(0),0) % 9973) / 9973; const rnd = () => (s = (s*9301+49297)%233280 / 233280);
  const N = 40, base = 0.6 + rnd()*0.2;
  const data = d3.range(N).map((i)=> base + 0.2*Math.sin(i*0.4 + rnd()*0.5) + (rnd()-0.5)*0.1);
  const x = d3.scaleLinear().domain([0, N-1]).range([0, w]);
  const y = d3.scaleLinear().domain([d3.min(data)-0.05, d3.max(data)+0.05]).range([h, 0]);
  const line = d3.line().x((d,i)=>x(i)).y((d)=>y(d)).curve(d3.curveMonotoneX);
  const area = d3.area().x((d,i)=>x(i)).y0(h).y1((d)=>y(d)).curve(d3.curveMonotoneX);
  g.append('path').attr('d', area(data)).attr('fill', 'rgba(76,201,240,0.15)');
  const path = g.append('path').attr('d', line(data)).attr('fill', 'none').attr('stroke', '#4cc9f0').attr('stroke-width', 1.6);
  if (!reduceMotion) {
    const dlen = path.node().getTotalLength();
    path.attr('stroke-dasharray', dlen).attr('stroke-dashoffset', dlen)
        .transition().duration(900).ease(d3.easeCubicOut).attr('stroke-dashoffset', 0);
  }
}

