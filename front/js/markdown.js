/**
 * Lightweight markdown → HTML renderer for chat bot messages.
 * Supports: bold, italic, bold+italic, inline code, code blocks,
 *           links, unordered/ordered lists, blockquotes, headings, line breaks.
 */
export function renderMarkdown(raw) {
  if (!raw) return '';

  let text = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Fenced code blocks (``` ... ```)
  text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (_m, _lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  text = text.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Bold + Italic
  text = text.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  // Bold
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  // Italic
  text = text.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');

  // Links [text](url)
  text = text.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );

  // Process line-by-line for block elements
  const lines = text.split('\n');
  let result = '';
  let inList = false;
  let listTag = '';

  for (const line of lines) {
    // Headings
    const h3 = line.match(/^###\s+(.+)/);
    const h2 = line.match(/^##\s+(.+)/);
    const h1 = line.match(/^#\s+(.+)/);

    if (h3) {
      if (inList) { result += `</${listTag}>`; inList = false; }
      result += `<h3>${h3[1]}</h3>`;
      continue;
    }
    if (h2) {
      if (inList) { result += `</${listTag}>`; inList = false; }
      result += `<h2>${h2[1]}</h2>`;
      continue;
    }
    if (h1) {
      if (inList) { result += `</${listTag}>`; inList = false; }
      result += `<h1>${h1[1]}</h1>`;
      continue;
    }

    // Blockquote
    const bq = line.match(/^&gt;\s?(.*)/);
    if (bq) {
      if (inList) { result += `</${listTag}>`; inList = false; }
      result += `<blockquote>${bq[1]}</blockquote>`;
      continue;
    }

    // Unordered list
    const ul = line.match(/^\s*[-*]\s+(.+)/);
    if (ul) {
      if (!inList || listTag !== 'ul') {
        if (inList) result += `</${listTag}>`;
        result += '<ul>';
        inList = true;
        listTag = 'ul';
      }
      result += `<li>${ul[1]}</li>`;
      continue;
    }

    // Ordered list
    const ol = line.match(/^\s*\d+\.\s+(.+)/);
    if (ol) {
      if (!inList || listTag !== 'ol') {
        if (inList) result += `</${listTag}>`;
        result += '<ol>';
        inList = true;
        listTag = 'ol';
      }
      result += `<li>${ol[1]}</li>`;
      continue;
    }

    // Regular line / blank
    if (inList) { result += `</${listTag}>`; inList = false; }

    if (line.trim() === '') {
      result += '<br>';
    } else {
      // Skip wrapping if line is already a block element from code-block replacement
      if (line.startsWith('<pre>') || line.startsWith('</pre>')) {
        result += line;
      } else {
        result += `<p>${line}</p>`;
      }
    }
  }

  if (inList) result += `</${listTag}>`;

  // Clean excessive breaks
  result = result.replace(/(<br>\s*){3,}/g, '<br><br>');

  return result;
}
