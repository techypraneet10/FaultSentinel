import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SafeMarkdown, SafeInlineText } from '../utils/markdown';

describe('SafeMarkdown & Security Tests', () => {
  it('renders headings cleanly', () => {
    const md = '# Main Header\n## Section Header\n### Sub Section';
    render(<SafeMarkdown content={md} />);

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Main Header');
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Section Header');
    expect(screen.getByRole('heading', { level: 4 })).toHaveTextContent('Sub Section');
  });

  it('renders bullet lists', () => {
    const md = '- Item One\n- Item Two\n- Item Three';
    render(<SafeMarkdown content={md} />);

    expect(screen.getByText('Item One')).toBeInTheDocument();
    expect(screen.getByText('Item Two')).toBeInTheDocument();
    expect(screen.getByText('Item Three')).toBeInTheDocument();
  });

  it('renders code blocks and inline code', () => {
    const md = '```\nconst x = 42;\n```\nHere is `inline_code`.';
    render(<SafeMarkdown content={md} />);

    expect(screen.getByText('const x = 42;')).toBeInTheDocument();
    expect(screen.getByText('inline_code')).toHaveClass('inline-code');
  });

  it('renders blockquotes', () => {
    const md = '> Quoted statement from log context';
    render(<SafeMarkdown content={md} />);

    expect(screen.getByText('Quoted statement from log context')).toBeInTheDocument();
  });

  it('does NOT execute script tags or inject dangerous HTML', () => {
    const maliciousInput = '<script>window.pwned=true;</script><img src="x" onerror="alert(1)">';
    render(<SafeMarkdown content={maliciousInput} />);

    // In jsdom, if rendered as plain text rather than dangerouslySetInnerHTML,
    // there should be NO script element or image element with error handler.
    const scripts = document.querySelectorAll('script');
    const dangerousScripts = Array.from(scripts).filter((s) => s.textContent?.includes('window.pwned'));
    expect(dangerousScripts.length).toBe(0);

    // Text is safely rendered as plain text string
    expect(screen.getByText(maliciousInput)).toBeInTheDocument();
  });

  it('handles null and empty input safely', () => {
    const { container } = render(<SafeMarkdown content={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders bold inline text', () => {
    render(<SafeInlineText text="This is **strongly** formatted." />);
    expect(screen.getByText('strongly')).toHaveClass('bold-text');
  });
});
