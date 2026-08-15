'use client';

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent,
} from 'react';

const CELL_SIZE = 44;

type GridCell = {
  index: number;
  marked: boolean;
  filled: boolean;
  delay: string;
};

type GridState = {
  columns: number;
  rows: number;
  cells: GridCell[];
};

function buildCells(width: number, height: number, top: number, bottom: number): GridState {
  const columns = Math.max(1, Math.floor(width / CELL_SIZE));
  const rows = Math.ceil(height / CELL_SIZE);
  const firstRow = Math.ceil(top / CELL_SIZE);
  const lastRow = Math.floor(bottom / CELL_SIZE);
  let seed = 20260809;

  function random() {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  }

  const marks = new Map<number, { fill: number; delay: string }>();
  const band = Math.max(0, lastRow - firstRow);
  const walks = band > 0 ? Math.max(3, Math.round((columns * band) / 26)) : 0;

  for (let walk = 0; walk < walks; walk += 1) {
    let column = Math.floor(random() * columns);
    let row = firstRow + Math.floor(random() * band);
    const length = 3 + Math.floor(random() * 6);

    for (let step = 0; step < length; step += 1) {
      if (column >= 0 && column < columns && row >= firstRow && row < lastRow) {
        const index = row * columns + column;
        const fill = random() < 0.28 ? 0.12 + random() * 0.2 : 0;
        if (!marks.has(index) || fill) {
          marks.set(index, {
            fill,
            delay: `${(walk * 0.35 + step * 0.12).toFixed(2)}s`,
          });
        }
      }

      const direction = random();
      if (direction < 0.4) column += 1;
      else if (direction < 0.62) column -= 1;
      else if (direction < 0.84) row += 1;
      else row -= 1;
    }
  }

  const cells = Array.from({ length: columns * rows }, (_, index) => {
    const mark = marks.get(index);
    return {
      index,
      marked: Boolean(mark),
      filled: (mark?.fill ?? 0) > 0,
      delay: mark?.delay ?? '0s',
    };
  });

  return { columns, rows, cells };
}

export function CubeField() {
  const field = useRef<HTMLDivElement>(null);
  const [grid, setGrid] = useState<GridState>({ columns: 1, rows: 1, cells: [] });

  useEffect(() => {
    const element = field.current;
    const hero = element?.closest<HTMLElement>('.agentsparty-hero');
    const header = hero?.querySelector<HTMLElement>('.agentsparty-hero-header');
    const demo = hero?.querySelector<HTMLElement>('.agentsparty-hero-demo');
    if (!element || !hero || !header || !demo) return;
    const heroElement = hero;
    const headerElement = header;
    const demoElement = demo;

    function rebuild() {
      const heroBox = heroElement.getBoundingClientRect();
      const headerBox = headerElement.getBoundingClientRect();
      const demoBox = demoElement.getBoundingClientRect();
      setGrid(
        buildCells(
          heroElement.clientWidth,
          heroElement.clientHeight,
          headerBox.bottom - heroBox.top + 12,
          demoBox.top - heroBox.top - 12,
        ),
      );
    }

    const observer = new ResizeObserver(rebuild);
    observer.observe(heroElement);
    rebuild();
    return () => observer.disconnect();
  }, []);

  function flash(event: PointerEvent<HTMLDivElement>) {
    if (!grid.cells.length) return;
    const box = event.currentTarget.getBoundingClientRect();
    const column = Math.floor((event.clientX - box.left) / CELL_SIZE);
    const row = Math.floor((event.clientY - box.top) / CELL_SIZE);
    if (column < 0 || column >= grid.columns || row < 0 || row >= grid.rows) return;

    const indices = [
      row * grid.columns + column,
      row * grid.columns + column - 1,
      row * grid.columns + column + 1,
      (row - 1) * grid.columns + column,
      (row + 1) * grid.columns + column,
    ];
    indices.forEach((index) => {
      const cell = event.currentTarget.querySelector(`[data-index="${index}"]`);
      if (!cell) return;
      cell.classList.remove('is-hot');
      requestAnimationFrame(() => cell.classList.add('is-hot'));
      window.setTimeout(() => cell.classList.remove('is-hot'), 900);
    });
  }

  return (
    <div className="agentsparty-grid-layer" aria-hidden>
      <div className="agentsparty-aurora">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div
        ref={field}
        className="agentsparty-field"
        onPointerMove={flash}
        style={
          {
            '--agentsparty-columns': grid.columns,
            '--agentsparty-grid-width': `${grid.columns * CELL_SIZE}px`,
            '--agentsparty-grid-height': `${grid.rows * CELL_SIZE}px`,
          } as CSSProperties
        }
      >
        {grid.cells.map(({ index, marked, filled, delay }) => (
          <span
            key={index}
            data-index={index}
            className={`agentsparty-cell${marked ? ' is-marked' : ''}${filled ? ' is-filled' : ''}`}
            style={{ '--agentsparty-delay': delay } as CSSProperties}
          />
        ))}
      </div>
    </div>
  );
}
