"use client";

import type { ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

type MarkdownMessageProps = {
  text: string;
};

const components: Components = {
  a: ({ children, href, ...props }: ComponentPropsWithoutRef<"a">) => (
    <a
      className="font-[600] text-brand-500 underline underline-offset-2 break-all"
      href={href}
      rel="noopener noreferrer"
      target="_blank"
      {...props}
    >
      {children}
    </a>
  ),
  blockquote: ({ children, ...props }: ComponentPropsWithoutRef<"blockquote">) => (
    <blockquote
      className="my-2 border-l-2 border-line pl-3 text-[13px] leading-[1.55] text-muted"
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ children, ...props }: ComponentPropsWithoutRef<"code">) => (
    <code
      className="rounded bg-bg px-1 py-0.5 font-mono text-[12.5px] text-ink"
      {...props}
    >
      {children}
    </code>
  ),
  em: ({ children, ...props }: ComponentPropsWithoutRef<"em">) => (
    <em className="italic" {...props}>
      {children}
    </em>
  ),
  h1: ({ children, ...props }: ComponentPropsWithoutRef<"h1">) => (
    <h1 className="mt-2 mb-1 text-[15px] font-[700] leading-[1.35] text-ink first:mt-0" {...props}>
      {children}
    </h1>
  ),
  h2: ({ children, ...props }: ComponentPropsWithoutRef<"h2">) => (
    <h2 className="mt-2 mb-1 text-[14.5px] font-[700] leading-[1.35] text-ink first:mt-0" {...props}>
      {children}
    </h2>
  ),
  h3: ({ children, ...props }: ComponentPropsWithoutRef<"h3">) => (
    <h3 className="mt-2 mb-1 text-[14px] font-[700] leading-[1.35] text-ink first:mt-0" {...props}>
      {children}
    </h3>
  ),
  h4: ({ children, ...props }: ComponentPropsWithoutRef<"h4">) => (
    <h4 className="mt-1.5 mb-0.5 text-[13.5px] font-[700] leading-[1.35] text-ink first:mt-0" {...props}>
      {children}
    </h4>
  ),
  hr: (props: ComponentPropsWithoutRef<"hr">) => (
    <hr className="my-2 border-line" {...props} />
  ),
  li: ({ children, ...props }: ComponentPropsWithoutRef<"li">) => (
    <li className="my-0.5" {...props}>
      {children}
    </li>
  ),
  ol: ({ children, ...props }: ComponentPropsWithoutRef<"ol">) => (
    <ol className="my-1 list-decimal pl-5" {...props}>
      {children}
    </ol>
  ),
  p: ({ children, ...props }: ComponentPropsWithoutRef<"p">) => (
    <p className="m-0 mt-1 first:mt-0" {...props}>
      {children}
    </p>
  ),
  pre: ({ children, ...props }: ComponentPropsWithoutRef<"pre">) => (
    <pre
      className="my-2 overflow-x-auto rounded-lg bg-bg p-2.5 font-mono text-[12.5px] leading-[1.5] text-ink"
      {...props}
    >
      {children}
    </pre>
  ),
  strong: ({ children, ...props }: ComponentPropsWithoutRef<"strong">) => (
    <strong className="font-[700]" {...props}>
      {children}
    </strong>
  ),
  ul: ({ children, ...props }: ComponentPropsWithoutRef<"ul">) => (
    <ul className="my-1 list-disc pl-5" {...props}>
      {children}
    </ul>
  ),
};

export function MarkdownMessage({ text }: MarkdownMessageProps) {
  return <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>;
}
