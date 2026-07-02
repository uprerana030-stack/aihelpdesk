import client from './client';

// "Lite login": validates the password only to establish identity + role. The
// returned token is not used for API auth (endpoints are public).
export async function login(email, password) {
  const { data } = await client.post('/auth/login', { email, password });
  return data;
}

export async function register({ email, full_name, password, department, role_name }) {
  const { data } = await client.post('/auth/register', {
    email,
    full_name,
    password,
    department,
    role_name: role_name || 'employee',
  });
  return data;
}

export async function listUsers() {
  const { data } = await client.get('/auth/users');
  return data;
}

export async function me() {
  const { data } = await client.get('/auth/me');
  return data;
}
