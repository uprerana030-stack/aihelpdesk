import { useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import ApartmentIcon from '@mui/icons-material/Apartment';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import CelebrationOutlinedIcon from '@mui/icons-material/CelebrationOutlined';
import { apiErrorMessage } from '../api/client';
import { useEscalations, useResolveTicket } from '../hooks/useTickets';
import { COLORS } from '../theme';

const PRIORITY_COLORS = {
  critical: 'error',
  high: 'error',
  urgent: 'error',
  medium: 'warning',
  low: 'default',
};

function priorityColor(priority) {
  return PRIORITY_COLORS[(priority ?? '').toLowerCase()] ?? 'default';
}

// Builds a mailto: link that opens the agent's mail client, pre-filled with a
// friendly draft addressed to the employee about their escalated ticket.
function buildMailto(item) {
  const { ticket, employee_name, employee_email, employee_department } = item;
  const title = ticket.title || `Ticket #${ticket.id}`;
  const subject = `Regarding your ticket #${ticket.id}: ${title}`;
  const team = employee_department || 'support';
  const body = [
    `Hi ${employee_name || 'there'},`,
    '',
    `I'm from the ${team} team and I'm now handling your ticket #${ticket.id} ("${title}").`,
    '',
    "Sorry the earlier automated response didn't fully resolve things. Could you share a bit more detail about what's still going wrong so I can help?",
    '',
    'Thanks,',
    'Support Team',
  ].join('\r\n');
  return `mailto:${encodeURIComponent(employee_email || '')}?subject=${encodeURIComponent(
    subject,
  )}&body=${encodeURIComponent(body)}`;
}

function ContactRow({ icon, children }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Box sx={{ color: 'text.secondary', display: 'flex' }}>{icon}</Box>
      <Typography variant="body2">{children}</Typography>
    </Stack>
  );
}

function EscalationCard({ item, onResolve }) {
  const { ticket, employee_name, employee_email, employee_department, feedback_comment } = item;
  const reason = feedback_comment || ticket.routing_reason || 'Flagged for a human to review.';

  return (
    <Card elevation={0} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" sx={{ mb: 1 }}>
          <Typography variant="h6">Ticket #{ticket.id}</Typography>
          {ticket.category && (
            <Chip size="small" variant="outlined" label={ticket.category} sx={{ textTransform: 'capitalize' }} />
          )}
          {ticket.priority && (
            <Chip
              size="small"
              color={priorityColor(ticket.priority)}
              label={`${ticket.priority} priority`}
              sx={{ textTransform: 'capitalize', fontWeight: 600 }}
            />
          )}
        </Stack>

        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          {ticket.title || 'Untitled request'}
        </Typography>
        {ticket.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
            {ticket.description}
          </Typography>
        )}

        {/* Why this needs a human */}
        <Box
          sx={{
            mt: 2,
            p: 1.5,
            borderRadius: 2,
            bgcolor: 'rgba(182,67,47,0.06)',
            border: `1px solid ${COLORS.cardBorder}`,
          }}
        >
          <Typography variant="caption" color="text.secondary" display="block">
            Why it needs a human
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
            {reason}
          </Typography>
        </Box>

        {/* Employee contact block */}
        <Box sx={{ mt: 2 }}>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
            Employee contact
          </Typography>
          <Stack spacing={0.5}>
            <ContactRow icon={<PersonOutlineIcon fontSize="small" />}>
              {employee_name || 'Unknown'}
            </ContactRow>
            <ContactRow icon={<EmailOutlinedIcon fontSize="small" />}>
              {employee_email || '—'}
            </ContactRow>
            {employee_department && (
              <ContactRow icon={<ApartmentIcon fontSize="small" />}>{employee_department}</ContactRow>
            )}
          </Stack>
        </Box>

        {/* Previously attempted (auto) solution, collapsed for context */}
        {ticket.resolution && (
          <Accordion elevation={0} disableGutters sx={{ mt: 2, '&:before': { display: 'none' }, bgcolor: 'transparent' }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0, minHeight: 0 }}>
              <Typography variant="caption" color="text.secondary">
                Previously attempted solution
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 0, pt: 0 }}>
              <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
                {ticket.resolution}
              </Typography>
            </AccordionDetails>
          </Accordion>
        )}
      </CardContent>

      <Divider />
      <Stack direction="row" spacing={1} sx={{ p: 2 }}>
        <Button
          variant="outlined"
          startIcon={<EmailOutlinedIcon />}
          component="a"
          href={buildMailto(item)}
          disabled={!employee_email}
        >
          Contact employee
        </Button>
        <Button variant="contained" startIcon={<TaskAltIcon />} onClick={() => onResolve(item)}>
          Resolve
        </Button>
      </Stack>
    </Card>
  );
}

export default function EscalationsPage() {
  const escalationsQuery = useEscalations();
  const resolve = useResolveTicket();

  const [active, setActive] = useState(null); // escalation item being resolved
  const [resolution, setResolution] = useState('');

  const items = useMemo(() => escalationsQuery.data ?? [], [escalationsQuery.data]);

  const openResolve = (item) => {
    setActive(item);
    setResolution('');
  };
  const closeResolve = () => setActive(null);

  const submitResolve = () => {
    if (!active || !resolution.trim()) return;
    resolve.mutate(
      { id: active.ticket.id, resolution: resolution.trim() },
      { onSuccess: closeResolve },
    );
  };

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <ReportProblemOutlinedIcon sx={{ color: COLORS.danger }} />
          <Typography variant="h4">Escalations — Manual Team</Typography>
        </Stack>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          Tickets that need a human. Contact the employee and resolve.
        </Typography>
      </Box>

      {escalationsQuery.isError ? (
        <Alert severity="error">{apiErrorMessage(escalationsQuery.error)}</Alert>
      ) : escalationsQuery.isLoading ? (
        <Paper sx={{ p: 3 }} elevation={0}>
          <Typography color="text.secondary">Loading escalations…</Typography>
        </Paper>
      ) : items.length === 0 ? (
        <Paper sx={{ p: 5, textAlign: 'center' }} elevation={0}>
          <CelebrationOutlinedIcon sx={{ fontSize: 48, color: COLORS.primary }} />
          <Typography variant="h6" sx={{ mt: 1 }}>
            No escalations right now
          </Typography>
          <Typography variant="body2" color="text.secondary">
            The AI is handling things — nothing needs a human at the moment.
          </Typography>
        </Paper>
      ) : (
        <>
          <Typography variant="subtitle1" sx={{ mb: 2, fontWeight: 600 }}>
            {items.length} open escalation{items.length === 1 ? '' : 's'}
          </Typography>
          <Grid container spacing={2}>
            {items.map((item) => (
              <Grid item xs={12} md={6} key={item.ticket.id}>
                <EscalationCard item={item} onResolve={openResolve} />
              </Grid>
            ))}
          </Grid>
        </>
      )}

      <Dialog open={!!active} onClose={closeResolve} maxWidth="sm" fullWidth>
        <DialogTitle>
          Resolve ticket {active ? `#${active.ticket.id}` : ''}
        </DialogTitle>
        <DialogContent>
          {active && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {active.ticket.title}
            </Typography>
          )}
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={4}
            label="Resolution"
            placeholder="Explain how this was resolved for the employee…"
            value={resolution}
            onChange={(e) => setResolution(e.target.value)}
            inputProps={{ 'aria-label': 'resolution' }}
          />
          {resolve.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {apiErrorMessage(resolve.error)}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeResolve}>Cancel</Button>
          <Button
            variant="contained"
            onClick={submitResolve}
            disabled={!resolution.trim() || resolve.isPending}
          >
            {resolve.isPending ? 'Resolving…' : 'Resolve'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
