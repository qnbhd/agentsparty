'use client';

import { useEffect, useRef } from 'react';

/* One full-screen triangle covers the viewport with a single draw call; the
 * fragment shader below does all the work. */
const TRIANGLE = new Float32Array([-1, -1, 3, -1, -1, 3]);

const VERTEX_SHADER = `attribute vec2 p; void main(){ gl_Position = vec4(p,0.,1.); }`;

/* Domain-warped fbm: `q` warps the field, `r` warps it again, and the third
 * sample is ramped through four stops of the project's lime.
 *
 * The stops are steps 950 through 500 of the brand ramp in `global.css`,
 * converted to sRGB. Step 400 - the loudest lime the project owns - is
 * deliberately absent: it belongs to the primary call to action alone, so the
 * one thing worth clicking is the one thing brighter than the field.
 *
 * Four octaves rather than six, and time scaled well below the rate that
 * reads as motion. A field with visible turbulence is wallpaper; this one is
 * meant to be noticed only on the second look. */
const FRAGMENT_SHADER = `
precision highp float;
uniform vec2 res; uniform float t;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
float noise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash(i), hash(i+vec2(1,0)), u.x), mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), u.x), u.y);
}
float fbm(vec2 p){
  float v = 0.0, a = 0.5;
  for(int i=0;i<4;i++){ v += a*noise(p); p = p*2.02 + vec2(1.7,9.2); a *= 0.5; }
  return v;
}
void main(){
  vec2 uv = (gl_FragCoord.xy - 0.5*res) / res.y;
  float tt = t*0.02;
  vec2 q = vec2(fbm(uv*1.6 + vec2(0.0, tt)), fbm(uv*1.6 + vec2(5.2,1.3) - tt));
  vec2 r = vec2(fbm(uv*1.9 + 3.0*q + vec2(1.7,9.2) + 0.15*tt), fbm(uv*1.9 + 3.0*q + vec2(8.3,2.8) - 0.12*tt));
  float f = fbm(uv*1.5 + 3.2*r);
  float m = clamp(f*1.6 - 0.55, 0.0, 1.0);
  vec3 c0 = vec3(0.128,0.154,0.050);
  vec3 c1 = vec3(0.216,0.263,0.033);
  vec3 c2 = vec3(0.437,0.522,0.097);
  vec3 c3 = vec3(0.681,0.807,0.202);
  vec3 col = mix(c0, c1, smoothstep(0.05,0.45,m));
  col = mix(col, c2, smoothstep(0.42,0.72,m));
  col = mix(col, c3, smoothstep(0.68,0.95,m) * (0.30 + 0.30*length(r)));
  col += 0.045 * c3 * pow(clamp(length(q),0.0,1.0), 3.0);
  float vig = smoothstep(1.45, 0.25, length(uv*vec2(0.85,1.0)));
  col *= mix(0.42, 1.0, vig);
  col += (hash(gl_FragCoord.xy + t) - 0.5) * 0.02;
  gl_FragColor = vec4(col, 1.0);
}`;

/* Shown when the browser has no WebGL context to give — the field's own
 * palette, minus the motion. */
const FALLBACK =
  'radial-gradient(120% 90% at 60% 40%, oklch(58% 0.13 121), oklch(22% 0.032 199))';

/* A still frame taken from a moment the field composes well, so a
 * reduced-motion visitor gets the picture rather than its first instant.
 * Tracks the shader's own time scale: this is the second at which `tt`
 * reaches 0.54, the point the composition was chosen at. */
const STILL_AT_SECONDS = 27;

/* Retina pixels cost fill rate on a shader this heavy and buy little on a
 * field with no edges, so the buffer stops short of the real ratio. */
const MAX_PIXEL_RATIO = 1.75;

type DrawFrame = (seconds: number) => void;

function compile(gl: WebGLRenderingContext, type: number, source: string): WebGLShader {
  const shader = gl.createShader(type)!;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  return shader;
}

/* Links the program and uploads the geometry once, then hands back the only
 * capability the caller needs: drawing the field at a point in time. */
function createRenderer(gl: WebGLRenderingContext): DrawFrame {
  const program = gl.createProgram()!;
  gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
  gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
  gl.linkProgram(program);
  gl.useProgram(program);

  gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
  gl.bufferData(gl.ARRAY_BUFFER, TRIANGLE, gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, 'p');
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const resolution = gl.getUniformLocation(program, 'res');
  const elapsed = gl.getUniformLocation(program, 't');

  return (seconds) => {
    gl.uniform2f(resolution, gl.drawingBufferWidth, gl.drawingBufferHeight);
    gl.uniform1f(elapsed, seconds);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };
}

export function HeroShader() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext('webgl', { antialias: false, alpha: false });
    if (!gl) {
      canvas.style.background = FALLBACK;
      return;
    }

    // match the drawing buffer to the element's box:
    const draw = createRenderer(gl);
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const fit = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO);
      canvas.width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
      canvas.height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
      gl.viewport(0, 0, canvas.width, canvas.height);
      if (still) draw(STILL_AT_SECONDS);
    };
    fit();
    window.addEventListener('resize', fit);

    // animate, unless the visitor asked for stillness:
    const start = performance.now();
    let frame = 0;
    const loop = () => {
      draw((performance.now() - start) / 1000);
      frame = requestAnimationFrame(loop);
    };
    if (!still) loop();

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', fit);
    };
  }, []);

  return <canvas ref={canvasRef} className="agentsparty-hero-canvas" aria-hidden />;
}
