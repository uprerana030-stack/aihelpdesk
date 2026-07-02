import client from './client';

export async function submitTicket(input) {
  const form = new FormData();
  form.append('description', input.description);
  form.append('title', input.title ?? '');
  if (input.file) form.append('attachment', input.file);
  const { data } = await client.post('/tickets', form);
  return data;
}

export async function listTickets() {
  const { data } = await client.get('/tickets');
  return data;
}

export async function getTicket(id) {
  const { data } = await client.get(`/tickets/${id}`);
  return data;
}

export async function resolveTicket(id, resolution) {
  const { data } = await client.post(`/tickets/${id}/resolve`, { resolution });
  return data;
}

export async function escalateTicket(id, target, note) {
  const { data } = await client.post(`/tickets/${id}/escalate`, { target, note });
  return data;
}

export async function closeTicket(id) {
  const { data } = await client.post(`/tickets/${id}/close`);
  return data;
}

export async function submitFeedback(id, rating, comment) {
  const { data } = await client.post(`/tickets/${id}/feedback`, { rating, comment });
  return data;
}

export async function listEscalations() {
  const { data } = await client.get('/tickets/escalations');
  return data;
}

export async function getAudit(id) {
  const { data } = await client.get(`/tickets/${id}/audit`);
  return data;
}
