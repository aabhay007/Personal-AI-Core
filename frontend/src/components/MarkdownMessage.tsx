'use client';

import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface MarkdownMessageProps {
  content: string;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  // If content is empty
  if (!content) return null;

  // Split by code blocks ```
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const elements: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    const textBefore = content.slice(lastIndex, match.index);
    if (textBefore) {
      elements.push(<TextSection key={`text-${lastIndex}`} text={textBefore} />);
    }

    const language = match[1] || 'text';
    const code = match[2];
    elements.push(
      <CodeBlock key={`code-${match.index}`} language={language} code={code} />
    );

    lastIndex = match.index + match[0].length;
  }

  const remainingText = content.slice(lastIndex);
  if (remainingText) {
    elements.push(<TextSection key={`text-${lastIndex}`} text={remainingText} />);
  }

  return <div className="space-y-2 text-xs leading-relaxed text-zinc-200">{elements}</div>;
}

function TextSection({ text }: { text: string }) {
  const lines = text.split('\n');

  return (
    <div className="space-y-1.5">
      {lines.map((line, idx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // Heading 3: ###
        if (trimmed.startsWith('### ')) {
          return (
            <h4 key={idx} className="font-semibold text-sm text-zinc-100 pt-2 pb-0.5">
              {formatInlineStyles(trimmed.slice(4))}
            </h4>
          );
        }

        // Heading 2: ##
        if (trimmed.startsWith('## ')) {
          return (
            <h3 key={idx} className="font-semibold text-base text-zinc-100 pt-2.5 pb-1">
              {formatInlineStyles(trimmed.slice(3))}
            </h3>
          );
        }

        // Heading 1: #
        if (trimmed.startsWith('# ')) {
          return (
            <h2 key={idx} className="font-bold text-lg text-white pt-3 pb-1">
              {formatInlineStyles(trimmed.slice(2))}
            </h2>
          );
        }

        // Bullet list item: - or *
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 mt-1.5 shrink-0" />
              <span className="flex-1">{formatInlineStyles(trimmed.slice(2))}</span>
            </div>
          );
        }

        // Numbered list: e.g. 1.
        const numMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="font-semibold text-indigo-400 shrink-0 min-w-4 text-[11px]">
                {numMatch[1]}.
              </span>
              <span className="flex-1">{formatInlineStyles(numMatch[2])}</span>
            </div>
          );
        }

        // Standard paragraph
        return (
          <p key={idx} className="leading-relaxed">
            {formatInlineStyles(line)}
          </p>
        );
      })}
    </div>
  );
}

function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <div className="my-2.5 rounded-xl border border-white/[0.08] bg-zinc-950/90 overflow-hidden font-mono text-[11px] shadow-lg">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-white/[0.03] border-b border-white/[0.06] text-zinc-400 text-[10px]">
        <span className="uppercase tracking-wider font-semibold text-zinc-300">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-zinc-400 hover:text-white transition-colors cursor-pointer px-2 py-0.5 rounded hover:bg-white/[0.05]"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="text-emerald-400 font-sans">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span className="font-sans">Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3 overflow-x-auto text-zinc-200 leading-relaxed">
        <pre>{code}</pre>
      </div>
    </div>
  );
}

function formatInlineStyles(text: string): React.ReactNode[] {
  // Matches **bold** and `code`
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  let lastIdx = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index));
    }
    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={`b-${match.index}`} className="font-semibold text-white">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code
          key={`c-${match.index}`}
          className="px-1.5 py-0.5 rounded bg-zinc-800/80 border border-zinc-700/60 font-mono text-[11px] text-violet-300"
        >
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIdx = match.index + token.length;
  }

  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx));
  }

  return parts;
}
