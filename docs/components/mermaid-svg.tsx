/** Build-time rendered Mermaid SVG embedded into static HTML. */
export function MermaidSvg({ svg }: { svg: string }) {
  return (
    <div
      className="agentsparty-mermaid my-4 overflow-x-auto"
      role="img"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
