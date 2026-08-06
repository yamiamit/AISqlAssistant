import { toPng } from "html-to-image";

export async function exportChartAsPng(node: HTMLElement, filename: string) {
  const dataUrl = await toPng(node, { pixelRatio: 2 });
  const link = document.createElement("a");
  link.href = dataUrl;
  link.download = filename;
  link.click();
}
