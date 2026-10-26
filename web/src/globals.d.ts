// Allow importing CSS files as side-effects (e.g. maplibre-gl.css, reactflow/dist/style.css)
declare module '*.css' {
  const content: Record<string, string>;
  export default content;
}
