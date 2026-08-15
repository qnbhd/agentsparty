/**
 * A plain terminal surface: program output and interactive prompts, not code.
 * Flat and muted so it reads as a result, not as another block to type from.
 */
export function Terminal({ value }: { value: string }) {
  return <pre className="ap-terminal">{value}</pre>;
}
