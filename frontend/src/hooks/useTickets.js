import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  closeTicket,
  escalateTicket,
  getAudit,
  getTicket,
  listEscalations,
  listTickets,
  resolveTicket,
  submitFeedback,
  submitTicket,
} from '../api/tickets';

const TICKETS_KEY = ['tickets'];
const ESCALATIONS_KEY = ['escalations'];

export function useTickets() {
  return useQuery({ queryKey: TICKETS_KEY, queryFn: listTickets });
}

export function useEscalations() {
  return useQuery({ queryKey: ESCALATIONS_KEY, queryFn: listEscalations });
}

export function useTicket(id) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => getTicket(id),
    enabled: id != null,
  });
}

export function useTicketAudit(id) {
  return useQuery({
    queryKey: ['ticket-audit', id],
    queryFn: () => getAudit(id),
    enabled: id != null,
  });
}

export function useSubmitTicket() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input) => submitTicket(input),
    onSuccess: () => qc.invalidateQueries({ queryKey: TICKETS_KEY }),
  });
}

function useTicketLifecycleMutation(fn) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TICKETS_KEY });
      qc.invalidateQueries({ queryKey: ['ticket'] });
      qc.invalidateQueries({ queryKey: ESCALATIONS_KEY });
    },
  });
}

export function useResolveTicket() {
  return useTicketLifecycleMutation((args) =>
    resolveTicket(args.id, args.resolution),
  );
}

export function useEscalateTicket() {
  return useTicketLifecycleMutation((args) =>
    escalateTicket(args.id, args.target, args.note),
  );
}

export function useCloseTicket() {
  return useTicketLifecycleMutation((args) => closeTicket(args.id));
}

export function useSubmitFeedback() {
  const qc = useQueryClient();
  // mutationFn returns the feedback response ({ escalated, status, ... }) so
  // callers can read `data` in onSuccess / the returned mutation result.
  return useMutation({
    mutationFn: (args) => submitFeedback(args.id, args.rating, args.comment),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: TICKETS_KEY });
      qc.invalidateQueries({ queryKey: ESCALATIONS_KEY });
    },
  });
}
