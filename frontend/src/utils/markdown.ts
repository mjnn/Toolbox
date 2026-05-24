import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

export const renderMarkdown = (source?: string | null): string => {
  return md.render((source || '').trim())
}
