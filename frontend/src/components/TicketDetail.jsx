import { Box, Chip, Divider, Grid, Link, Paper, Stack, Typography } from '@mui/material';
import StatusChip from './StatusChip';
import { AGENT_ROLES, MANAGER_ROLES, useUser } from '../context/UserContext';

function resolutionSourceLabel(ticket) {
  switch (ticket.resolution_source) {
    case 'auto':
      return 'Resolved automatically from the Knowledge Base';
    case 'duplicate_match':
    case 'duplicate':
      return 'Resolved from a matching earlier ticket';
    case 'agent':
      return 'Resolved by a support agent';
    default:
      return 'Resolution';
  }
}

function resolutionSourceChip(source) {
  switch (source) {
    case 'auto':
      return 'Auto-resolved';
    case 'duplicate_match':
    case 'duplicate':
      return 'Matched earlier ticket';
    case 'agent':
      return 'Agent';
    default:
      return 'Resolution';
  }
}

function resolutionSourceColor(source) {
  switch (source) {
    case 'auto':
      return 'success';
    case 'duplicate_match':
    case 'duplicate':
      return 'info';
    default:
      return 'default';
  }
}

function Field({ label, value }) {
  return (
    <Grid item xs={6} sm={4}>
      <Typography variant="caption" color="text.secondary" display="block">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
        {value ?? '—'}
      </Typography>
    </Grid>
  );
}

export default function TicketDetail({ ticket, children }) {
  const { role } = useUser();
  // "Staff" = agents & managers see the fuller internal detail. Everyone else
  // (plain employees, KB writers, etc.) gets the safe, plain-language view.
  const isStaff = AGENT_ROLES.includes(role) || MANAGER_ROLES.includes(role);

  return (
    <Paper sx={{ p: 3 }} elevation={0}>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h6">
          #{ticket.id} — {ticket.title || 'Untitled'}
        </Typography>
        <StatusChip status={ticket.status} />
      </Stack>

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Field label="Category" value={ticket.category} />
        <Field label="Priority" value={ticket.priority} />
        <Field label="Department" value={ticket.department} />
        {isStaff && (
          <>
            <Field label="Intent" value={ticket.intent} />
            <Field
              label="Confidence"
              value={`${Math.round((ticket.confidence ?? 0) * 100)}%`}
            />
            <Field
              label="Assigned agent"
              value={ticket.assigned_agent_id ? `#${ticket.assigned_agent_id}` : 'Unassigned'}
            />
          </>
        )}
      </Grid>

      <Typography variant="caption" color="text.secondary" display="block">
        Description
      </Typography>
      <Typography variant="body2" sx={{ mb: 2, whiteSpace: 'pre-wrap' }}>
        {ticket.description}
      </Typography>

      {ticket.resolution && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            {resolutionSourceLabel(ticket)}{' '}
            <Chip
              size="small"
              label={resolutionSourceChip(ticket.resolution_source)}
              color={resolutionSourceColor(ticket.resolution_source)}
            />
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {ticket.resolution}
          </Typography>
          {ticket.kb_sources && ticket.kb_sources.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {isStaff ? 'Sources:' : 'Based on:'}
              </Typography>{' '}
              {ticket.kb_sources.map((s, i) => (
                <Link key={i} component="span" sx={{ mr: 1 }} underline="hover">
                  {String(s.title ?? `Source ${i + 1}`)}
                  {/* KB match scores are internal — only staff see them. */}
                  {isStaff && s.score != null ? ` (${Math.round(s.score * 100)}%)` : ''}
                </Link>
              ))}
            </Box>
          )}
        </>
      )}

      {isStaff && ticket.escalation_target && (
        <Box sx={{ mt: 2 }}>
          <Chip color="error" size="small" label={`Escalated to ${ticket.escalation_target}`} />
        </Box>
      )}

      {children && (
        <>
          <Divider sx={{ my: 2 }} />
          {children}
        </>
      )}
    </Paper>
  );
}
