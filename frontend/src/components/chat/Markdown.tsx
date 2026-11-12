import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders model output as Markdown. Raw HTML is not enabled, so document text cannot inject markup. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="text-sm leading-relaxed [&_li]:ml-5 [&_li]:list-disc [&_ol_li]:list-decimal [&_p]:mb-2 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_table]:my-2 [&_table]:w-full [&_table]:text-xs [&_td]:border [&_td]:border-line [&_td]:px-2 [&_td]:py-1 [&_th]:border [&_th]:border-line [&_th]:bg-canvas [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_blockquote]:border-l-2 [&_blockquote]:pl-2">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
