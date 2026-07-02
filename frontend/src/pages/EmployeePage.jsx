import { useMemo, useState } from 'react';
import {
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  Grid,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import ConfirmationNumberOutlinedIcon from '@mui/icons-material/ConfirmationNumberOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ForwardToInboxIcon from '@mui/icons-material/ForwardToInbox';
import TicketForm from '../components/TicketForm';
import FeedbackForm from '../components/FeedbackForm';
import TicketDetail from '../components/TicketDetail';
import StatusChip from '../components/StatusChip';
import { apiErrorMessage } from '../api/client';
import { useUser } from '../context/UserContext';
import {
  useCloseTicket,
  useSubmitFeedback,
  useSubmitTicket,
  useTickets,
} from '../hooks/useTickets';
import { COLORS } from '../theme';

const RESOLVED_STATUSES = ['resolved', 'closed'];
const IN_PROGRESS_STATUSES = ['in_progress', 'routed', 'open'];

// Hardcoded, clearly-labelled examples shown to brand-new employees with zero
// real tickets. These are NEVER counted in the stat cards.
const SAMPLE_TICKETS = [
  {
    id: 'sample-1',
    title: 'Reset my email password',
    category: 'Access',
    status: 'resolved',
    resolution: 'You can reset your own password from the self-service portal at any time.',
    resolution_source: 'auto',
    created_at: '2026-06-24T09:12:00Z',
    isSample: true,
  },
  {
    id: 'sample-2',
    title: 'Request a second monitor',
    category: 'Hardware',
    status: 'resolved',
    resolution: 'Your monitor request was approved and fulfilled by the Facilities team.',
    resolution_source: 'agent',
    created_at: '2026-06-20T14:40:00Z',
    isSample: true,
  },
  {
    id: 'sample-3',
    title: 'VPN keeps disconnecting',
    category: 'Network',
    status: 'resolved',
    resolution: 'Updating the VPN client to the latest version resolved the disconnections.',
    resolution_source: 'duplicate_match',
    created_at: '2026-06-18T08:05:00Z',
    isSample: true,
  },
];

function formatDate(value) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function StatCard({ icon, label, value, color }) {
  return (
    <Card elevation={0} sx={{ height: '100%' }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center">
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              bgcolor: color,
            }}
          >
            {icon}
          </Box>
          <Box>
            <Typography variant="h4" sx={{ lineHeight: 1.1 }}>
              {value}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {label}
            </Typography>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

// Plain-language, employee-safe summary of a freshly-submitted ticket.
// NEVER renders pipeline traces, agent names, confidence, or similarity %.
function ResultPanel({ result, onView }) {
  const { ticket, duplicate_suggestions: suggestions = [] } = result;
  const status = ticket.status;

  const kbTitles = (ticket.kb_sources ?? [])
    .map((s) => s.title)
    .filter(Boolean)
    .join(', ');

  let panel = null;

  if (status === 'resolved' && ['auto', 'duplicate_match'].includes(ticket.resolution_source)) {
    panel = (
      <Alert
        severity="success"
        icon={<AutoAwesomeIcon />}
        sx={{ mt: 2 }}
      >
        <AlertTitle>Resolved automatically</AlertTitle>
        {ticket.resolution && (
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {ticket.resolution}
          </Typography>
        )}
        {ticket.routing_reason && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {ticket.routing_reason}
          </Typography>
        )}
        {kbTitles && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Based on: {kbTitles}
          </Typography>
        )}
      </Alert>
    );
  } else if (status === 'duplicate') {
    panel = (
      <Alert severity="info" icon={<ContentCopyIcon />} sx={{ mt: 2 }}>
        <AlertTitle>Looks like this is already being handled</AlertTitle>
        {ticket.routing_reason && (
          <Typography variant="body2">{ticket.routing_reason}</Typography>
        )}
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          It&apos;s been logged for the team either way.
        </Typography>
        {ticket.duplicate_of_id != null && (
          <Button
            size="small"
            sx={{ mt: 1 }}
            onClick={() => onView?.(ticket.duplicate_of_id)}
          >
            View ticket #{ticket.duplicate_of_id}
          </Button>
        )}
      </Alert>
    );
  } else if (['in_progress', 'routed'].includes(status)) {
    panel = (
      <Alert severity="info" icon={<ForwardToInboxIcon />} sx={{ mt: 2 }}>
        <AlertTitle>Request received</AlertTitle>
        <Typography variant="body2">
          Your request has been sent to the {ticket.department || 'support'} team — an agent
          will follow up.
        </Typography>
        {ticket.routing_reason && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {ticket.routing_reason}
          </Typography>
        )}
      </Alert>
    );
  } else {
    panel = (
      <Alert severity="success" sx={{ mt: 2 }}>
        <AlertTitle>Request submitted</AlertTitle>
        <Typography variant="body2">
          Ticket #{ticket.id} has been logged. You can track it below.
        </Typography>
      </Alert>
    );
  }

  // Soft hint about similar tickets — only when the ticket wasn't merged as a
  // duplicate. No percentages shown.
  const showHints = status !== 'duplicate' && suggestions.length > 0;

  return (
    <>
      {panel}
      {showHints && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <AlertTitle>You have similar tickets:</AlertTitle>
          <Stack spacing={0.5}>
            {suggestions.map((s) => (
              <Box key={s.ticket_id}>
                <Link
                  component="button"
                  type="button"
                  underline="hover"
                  onClick={() => onView?.(s.ticket_id)}
                >
                  #{s.ticket_id} — {s.title}
                </Link>
              </Box>
            ))}
          </Stack>
        </Alert>
      )}
    </>
  );
}

export default function EmployeePage() {
  const { user } = useUser();
  const ticketsQuery = useTickets();
  const submit = useSubmitTicket();
  const feedback = useSubmitFeedback();
  const closeTicket = useCloseTicket();

  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);

  const tickets = ticketsQuery.data ?? [];

  const stats = useMemo(() => {
    const total = tickets.length;
    const resolved = tickets.filter((t) => RESOLVED_STATUSES.includes(t.status)).length;
    const inProgress = tickets.filter((t) => IN_PROGRESS_STATUSES.includes(t.status)).length;
    const escalated = tickets.filter((t) => t.status === 'escalated').length;
    return { total, resolved, inProgress, escalated };
  }, [tickets]);

  const sortedTickets = useMemo(
    () =>
      [...tickets].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    [tickets],
  );

  const showSamples = !ticketsQuery.isLoading && !ticketsQuery.isError && tickets.length === 0;
  const rows = showSamples ? SAMPLE_TICKETS : sortedTickets;

  const handleSubmit = (input) => {
    submit.mutate(input, { onSuccess: (res) => setResult(res) });
  };

  // Open a ticket (from a result-panel link) by id, using the loaded list.
  const openById = (id) => {
    const found = tickets.find((t) => t.id === id);
    if (found) setSelected(found);
  };

  const canFeedback = selected && !selected.isSample && ['resolved', 'closed'].includes(selected.status);
  const canClose = selected && !selected.isSample && selected.status === 'resolved';

  return (
    <Box>
      {/* Greeting header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Hi, {user?.full_name || 'there'}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Raise a request and track everything you&apos;ve submitted in one place.
        </Typography>
      </Box>

      {/* Stat cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<ConfirmationNumberOutlinedIcon />}
            label="Total submitted"
            value={stats.total}
            color={COLORS.sidebarBg}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<CheckCircleOutlineIcon />}
            label="Resolved"
            value={stats.resolved}
            color={COLORS.primary}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<HourglassEmptyIcon />}
            label="In progress"
            value={stats.inProgress}
            color={COLORS.warning}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<ReportProblemOutlinedIcon />}
            label="Escalated"
            value={stats.escalated}
            color={COLORS.danger}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Raise a request */}
        <Grid item xs={12} md={5}>
          <TicketForm onSubmit={handleSubmit} submitting={submit.isPending} />
          {submit.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {apiErrorMessage(submit.error)}
            </Alert>
          )}
          {result && <ResultPanel result={result} onView={openById} />}
        </Grid>

        {/* My tickets */}
        <Grid item xs={12} md={7}>
          <Typography variant="h6" gutterBottom>
            My tickets
          </Typography>
          {ticketsQuery.isError ? (
            <Alert severity="error">{apiErrorMessage(ticketsQuery.error)}</Alert>
          ) : rows.length === 0 ? (
            <Paper sx={{ p: 3 }} elevation={0}>
              <Typography color="text.secondary">
                {ticketsQuery.isLoading ? 'Loading…' : 'No tickets yet.'}
              </Typography>
            </Paper>
          ) : (
            <>
              {showSamples && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  You haven&apos;t raised anything yet. Here are a few examples of what a
                  resolved ticket looks like:
                </Typography>
              )}
              <TableContainer component={Paper} elevation={0}>
                <Table size="small" aria-label="my tickets">
                  <TableHead>
                    <TableRow>
                      <TableCell>Ticket #</TableCell>
                      <TableCell>Title</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Created</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((t) => (
                      <TableRow
                        key={t.id}
                        hover
                        selected={selected?.id === t.id}
                        onClick={() => setSelected(t)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{t.isSample ? '—' : t.id}</TableCell>
                        <TableCell sx={{ maxWidth: 280 }}>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <span>{t.title || (t.description ?? '').slice(0, 60)}</span>
                            {t.isSample && (
                              <Chip size="small" label="Example" variant="outlined" />
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell>{t.category ?? '—'}</TableCell>
                        <TableCell>
                          <StatusChip status={t.status} />
                        </TableCell>
                        <TableCell>{formatDate(t.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}
        </Grid>
      </Grid>

      <Dialog open={!!selected} onClose={() => setSelected(null)} maxWidth="sm" fullWidth>
        <DialogContent>
          {selected && (
            <TicketDetail ticket={selected}>
              {selected.isSample ? (
                <Typography variant="body2" color="text.secondary">
                  This is an example ticket to show you what a resolved request looks like.
                </Typography>
              ) : canFeedback ? (
                <FeedbackForm
                  submitting={feedback.isPending}
                  onSubmit={(rating, comment) =>
                    feedback.mutateAsync({ id: selected.id, rating, comment })
                  }
                />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Feedback becomes available once the ticket is resolved or closed.
                </Typography>
              )}
            </TicketDetail>
          )}
        </DialogContent>
        <DialogActions>
          {canClose && selected && (
            <Button
              onClick={() =>
                closeTicket.mutate({ id: selected.id }, { onSuccess: () => setSelected(null) })
              }
              disabled={closeTicket.isPending}
            >
              Close ticket
            </Button>
          )}
          <Button onClick={() => setSelected(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
