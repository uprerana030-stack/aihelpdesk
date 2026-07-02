import { useState } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import ThumbUpAltIcon from '@mui/icons-material/ThumbUpAlt';
import ThumbDownAltIcon from '@mui/icons-material/ThumbDownAlt';

// `onSubmit(rating, comment)` should return the feedback response (or a promise
// resolving to it) so we can tell the employee whether the ticket was escalated.
export default function FeedbackForm({ onSubmit, submitting = false }) {
  const [rating, setRating] = useState(null);
  const [comment, setComment] = useState('');
  const [done, setDone] = useState(null); // feedback response after a successful submit

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (rating == null) return;
    const result = await onSubmit(rating, comment.trim());
    setDone({ rating, escalated: !!result?.escalated });
    setComment('');
    setRating(null);
  };

  if (done) {
    if (done.rating === 0 && done.escalated) {
      return (
        <Alert severity="info" icon={<ThumbDownAltIcon fontSize="small" />}>
          <AlertTitle>Thanks for letting us know</AlertTitle>
          Since this didn&apos;t resolve your issue, we&apos;ve escalated it to our support
          team — an agent will contact you by email shortly.
        </Alert>
      );
    }
    return (
      <Alert severity="success" icon={<ThumbUpAltIcon fontSize="small" />}>
        Thanks for your feedback!
      </Alert>
    );
  }

  return (
    <Box component="form" onSubmit={handleSubmit}>
      <Typography variant="subtitle2" gutterBottom>
        Was this resolution helpful?
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
        <ToggleButtonGroup
          exclusive
          value={rating}
          onChange={(_, val) => setRating(val)}
          aria-label="rating"
          size="small"
        >
          <ToggleButton value={1} aria-label="helpful" color="success">
            <ThumbUpAltIcon fontSize="small" sx={{ mr: 0.5 }} /> Yes
          </ToggleButton>
          <ToggleButton value={0} aria-label="not helpful" color="error">
            <ThumbDownAltIcon fontSize="small" sx={{ mr: 0.5 }} /> No
          </ToggleButton>
        </ToggleButtonGroup>
        <TextField
          size="small"
          label="Comment (optional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          fullWidth
          inputProps={{ 'aria-label': 'comment' }}
        />
        <Button type="submit" variant="contained" disabled={rating == null || submitting}>
          {submitting ? 'Sending…' : 'Send feedback'}
        </Button>
      </Stack>
    </Box>
  );
}
