import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Grid,
  InputAdornment,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import ArticleList from '../components/ArticleList';
import ArticleView from '../components/ArticleView';
import { apiErrorMessage } from '../api/client';
import { useArticles, useCreateArticle, useSearchKB } from '../hooks/useKnowledge';
import { KB_WRITER_ROLES, useUser } from '../context/UserContext';

const CATEGORIES = ['General', 'Password/Access', 'Network', 'Email', 'Hardware', 'Software', 'HR/Payroll', 'Finance/Reimbursement', 'Facilities'];

export default function KnowledgeBasePage() {
  const { role } = useUser();
  const canWrite = role != null && KB_WRITER_ROLES.includes(role);

  const articlesQuery = useArticles();
  const createArticle = useCreateArticle();

  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const searchQuery = useSearchKB(query);

  const [newTitle, setNewTitle] = useState('');
  const [newIssue, setNewIssue] = useState('');
  const [newSolution, setNewSolution] = useState('');
  const [newCategory, setNewCategory] = useState('General');

  const canPublish = newTitle.trim() && newIssue.trim() && newSolution.trim();

  const handleCreate = () => {
    if (!canPublish) return;
    const content = `Issue: ${newIssue.trim()}\n\nSolution: ${newSolution.trim()}`;
    createArticle.mutate(
      { title: newTitle.trim(), content, category: newCategory },
      {
        onSuccess: (a) => {
          setSelected(a);
          setNewTitle('');
          setNewIssue('');
          setNewSolution('');
          setNewCategory('General');
        },
      },
    );
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Knowledge base
      </Typography>

      <TextField
        placeholder="Semantic search the knowledge base…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        fullWidth
        sx={{ mb: 2 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
        inputProps={{ 'aria-label': 'search knowledge base' }}
      />

      {query.trim() && (
        <Paper sx={{ p: 2, mb: 2 }} elevation={1}>
          <Typography variant="subtitle2" gutterBottom>
            Search results
          </Typography>
          {searchQuery.isError && (
            <Alert severity="error">{apiErrorMessage(searchQuery.error)}</Alert>
          )}
          {searchQuery.isLoading && <Typography color="text.secondary">Searching…</Typography>}
          <List dense>
            {(searchQuery.data ?? []).map((r, i) => (
              <ListItem key={i} disableGutters>
                <ListItemText
                  primary={`${r.title} — ${Math.round(r.score * 100)}%`}
                  secondary={r.snippet}
                />
              </ListItem>
            ))}
            {searchQuery.data && searchQuery.data.length === 0 && !searchQuery.isLoading && (
              <Typography color="text.secondary">No matches.</Typography>
            )}
          </List>
        </Paper>
      )}

      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          {articlesQuery.isError ? (
            <Alert severity="error">{apiErrorMessage(articlesQuery.error)}</Alert>
          ) : (
            <ArticleList
              articles={articlesQuery.data ?? []}
              onSelect={setSelected}
              selectedId={selected?.id}
            />
          )}
        </Grid>
        <Grid item xs={12} md={8}>
          <ArticleView article={selected} />

          {canWrite && (
            <Paper sx={{ p: 3, mt: 2 }} elevation={1}>
              <Typography variant="h6" gutterBottom>
                New article
              </Typography>
              <Stack spacing={2}>
                <TextField
                  label="Title"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  fullWidth
                  size="small"
                />
                <TextField
                  select
                  label="Category"
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  sx={{ maxWidth: 260 }}
                  size="small"
                >
                  {CATEGORIES.map((c) => (
                    <MenuItem key={c} value={c}>
                      {c}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="Issue"
                  value={newIssue}
                  onChange={(e) => setNewIssue(e.target.value)}
                  fullWidth
                  size="small"
                  helperText="A short description of the problem"
                />
                <TextField
                  label="Solution"
                  value={newSolution}
                  onChange={(e) => setNewSolution(e.target.value)}
                  multiline
                  minRows={4}
                  fullWidth
                  size="small"
                  helperText="Step-by-step resolution"
                />

                <Divider textAlign="left">
                  <Typography variant="caption" color="text.secondary">
                    Preview
                  </Typography>
                </Divider>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    {newTitle.trim() || 'Untitled article'}
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      size="small"
                      label={newCategory}
                      color="primary"
                      variant="outlined"
                    />
                  </Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Issue
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 2 }}>
                    {newIssue.trim() || '—'}
                  </Typography>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Solution
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {newSolution.trim() || '—'}
                  </Typography>
                </Paper>

                {createArticle.isError && (
                  <Alert severity="error">{apiErrorMessage(createArticle.error)}</Alert>
                )}
                <Box>
                  <Button
                    variant="contained"
                    onClick={handleCreate}
                    disabled={!canPublish || createArticle.isPending}
                  >
                    Publish article
                  </Button>
                </Box>
              </Stack>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
