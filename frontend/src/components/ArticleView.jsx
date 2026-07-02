import { Box, Chip, Divider, Paper, Typography } from '@mui/material';

// Parse the canonical KB content format:
//   "Issue: <text>\n\nSolution: <text>"
// Returns { issue, solution } when it matches, otherwise null.
export function parseArticleContent(content) {
  if (typeof content !== 'string') return null;
  const match = content.match(/^\s*Issue:\s*([\s\S]*?)\n\s*\nSolution:\s*([\s\S]*)$/);
  if (!match) return null;
  return { issue: match[1].trim(), solution: match[2].trim() };
}

export default function ArticleView({ article }) {
  if (!article) {
    return (
      <Paper sx={{ p: 3, height: '100%' }} elevation={1}>
        <Typography color="text.secondary">Select an article to read it.</Typography>
      </Paper>
    );
  }

  const parsed = parseArticleContent(article.content);

  return (
    <Paper sx={{ p: 3 }} elevation={1}>
      <Typography variant="h5" gutterBottom>
        {article.title}
      </Typography>
      <Box sx={{ mb: 2 }}>
        <Chip size="small" label={article.category} color="primary" variant="outlined" />
      </Box>
      <Divider sx={{ mb: 2 }} />
      {parsed ? (
        <>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Issue
          </Typography>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, mb: 2 }}>
            {parsed.issue}
          </Typography>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Solution
          </Typography>
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
            {parsed.solution}
          </Typography>
        </>
      ) : (
        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
          {article.content}
        </Typography>
      )}
    </Paper>
  );
}
