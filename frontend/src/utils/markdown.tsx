import React from 'react';

/**
 * Safe, zero-HTML-injection Markdown renderer.
 * Converts structured markdown into React JSX nodes directly.
 * Never uses dangerouslySetInnerHTML, completely preventing XSS.
 */

interface InlineProps {
  text: string;
}

export const SafeInlineText: React.FC<InlineProps> = ({ text }) => {
  // Parse inline code `code` and bold **bold**
  const parts: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(
        <code key={match.index} className="inline-code">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(
        <strong key={match.index} className="bold-text">
          {token.slice(2, -2)}
        </strong>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return <>{parts.length > 0 ? parts : text}</>;
};

interface SafeMarkdownProps {
  content?: string | null;
  className?: string;
}

export const SafeMarkdown: React.FC<SafeMarkdownProps> = ({ content, className = '' }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];
  let inList = false;
  let listItems: string[] = [];

  const flushList = (key: number) => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`ul-${key}`} className="markdown-list">
          {listItems.map((item, idx) => (
            <li key={idx}>
              <SafeInlineText text={item} />
            </li>
          ))}
        </ul>
      );
      listItems = [];
      inList = false;
    }
  };

  const flushCodeBlock = (key: number) => {
    if (codeBlockLines.length > 0) {
      elements.push(
        <pre key={`pre-${key}`} className="markdown-pre">
          <code>{codeBlockLines.join('\n')}</code>
        </pre>
      );
      codeBlockLines = [];
    }
  };

  lines.forEach((line, index) => {
    // Code block boundaries
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock(index);
        inCodeBlock = false;
      } else {
        if (inList) flushList(index);
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      return;
    }

    const trimmed = line.trim();

    // List items
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      inList = true;
      listItems.push(trimmed.slice(2));
      return;
    } else if (inList) {
      flushList(index);
    }

    // Blank lines
    if (!trimmed) {
      return;
    }

    // Headings
    if (trimmed.startsWith('#### ')) {
      elements.push(
        <h5 key={index} className="markdown-h5">
          <SafeInlineText text={trimmed.slice(5)} />
        </h5>
      );
    } else if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={index} className="markdown-h4">
          <SafeInlineText text={trimmed.slice(4)} />
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={index} className="markdown-h3">
          <SafeInlineText text={trimmed.slice(3)} />
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={index} className="markdown-h2">
          <SafeInlineText text={trimmed.slice(2)} />
        </h2>
      );
    } else if (trimmed.startsWith('> ')) {
      elements.push(
        <blockquote key={index} className="markdown-blockquote">
          <SafeInlineText text={trimmed.slice(2)} />
        </blockquote>
      );
    } else {
      elements.push(
        <p key={index} className="markdown-p">
          <SafeInlineText text={line} />
        </p>
      );
    }
  });

  if (inCodeBlock) {
    flushCodeBlock(lines.length);
  }
  if (inList) {
    flushList(lines.length);
  }

  return <div className={`safe-markdown ${className}`}>{elements}</div>;
};
