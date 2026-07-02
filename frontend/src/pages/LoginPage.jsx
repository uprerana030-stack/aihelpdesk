import { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Divider,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import SupportAgentIcon from '@mui/icons-material/SupportAgent';
import PersonAddAltIcon from '@mui/icons-material/PersonAddAlt';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { login, register } from '../api/auth';
import { apiErrorMessage } from '../api/client';
import { homePathForRole, useUser } from '../context/UserContext';
import { useUsers } from '../hooks/useAnalytics';

const DEMO_PASSWORD = 'Password123';
const DEPARTMENTS = ['IT', 'HR', 'Finance', 'Facilities', 'General'];

export default function LoginPage() {
  const { setUser } = useUser();
  const navigate = useNavigate();
  const usersQuery = useUsers();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState(DEMO_PASSWORD);

  const [showRegister, setShowRegister] = useState(false);
  const [regFullName, setRegFullName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regDepartment, setRegDepartment] = useState('');

  const goHome = (user) => {
    setUser(user);
    navigate(homePathForRole(user.role_name), { replace: true });
  };

  const loginMutation = useMutation({
    mutationFn: () => login(email.trim(), password),
    onSuccess: (res) => {
      const known = usersQuery.data?.find((u) => u.email === res.email);
      const user =
        known ?? {
          id: 0,
          email: res.email,
          full_name: res.full_name,
          role_name: res.role,
        };
      goHome(user);
    },
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      register({
        email: regEmail.trim(),
        full_name: regFullName.trim(),
        department: regDepartment || undefined,
        role_name: 'employee',
      }),
    onSuccess: (u) => {
      goHome({
        id: u.id,
        email: u.email,
        full_name: u.full_name,
        role_name: u.role_name,
        department: u.department,
      });
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    loginMutation.mutate();
  };

  const handleRegister = (e) => {
    e.preventDefault();
    if (!regEmail.trim() || !regFullName.trim()) return;
    registerMutation.mutate();
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 10 }}>
      <Paper sx={{ p: 4 }} elevation={3}>
        <Stack alignItems="center" spacing={1} sx={{ mb: 3 }}>
          <SupportAgentIcon color="primary" sx={{ fontSize: 44 }} />
          <Typography variant="h5">AI Helpdesk Router</Typography>
          <Typography variant="body2" color="text.secondary">
            Sign in to choose your persona view
          </Typography>
        </Stack>

        {!showRegister ? (
          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={2}>
              <TextField
                select
                label="Demo user"
                value={usersQuery.data?.some((u) => u.email === email) ? email : ''}
                onChange={(e) => {
                  setEmail(e.target.value);
                  setPassword(DEMO_PASSWORD);
                }}
                helperText={
                  usersQuery.isError
                    ? 'Could not load users — is the backend running & seeded?'
                    : 'Pick a seeded demo user, or type an email below.'
                }
                disabled={usersQuery.isLoading}
                fullWidth
              >
                {(usersQuery.data ?? []).map((u) => (
                  <MenuItem key={u.id} value={u.email}>
                    {u.full_name || u.email} — {String(u.role_name).replace(/_/g, ' ')}
                    {u.department ? ` (${u.department})` : ''}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                label="Email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                fullWidth
                inputProps={{ 'aria-label': 'email' }}
              />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                fullWidth
                helperText={`Seeded demo password: ${DEMO_PASSWORD}`}
                inputProps={{ 'aria-label': 'password' }}
              />

              {loginMutation.isError && (
                <Alert severity="error">{apiErrorMessage(loginMutation.error)}</Alert>
              )}

              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? 'Signing in…' : 'Sign in'}
              </Button>
            </Stack>

            <Divider sx={{ my: 3 }}>New to the helpdesk?</Divider>

            <Button
              fullWidth
              variant="outlined"
              size="large"
              startIcon={<PersonAddAltIcon />}
              onClick={() => {
                setRegEmail(email.trim());
                setShowRegister(true);
              }}
            >
              New employee? Register here
            </Button>
          </Box>
        ) : (
          <Box component="form" onSubmit={handleRegister}>
            <Stack spacing={2}>
              <Typography variant="subtitle1">Register as a new employee</Typography>
              <Typography variant="body2" color="text.secondary">
                No password needed — we&apos;ll sign you straight in.
              </Typography>
              <TextField
                label="Full name"
                value={regFullName}
                onChange={(e) => setRegFullName(e.target.value)}
                required
                fullWidth
                autoFocus
              />
              <TextField
                label="Work email"
                type="email"
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
                fullWidth
              />
              <TextField
                select
                label="Department"
                value={regDepartment}
                onChange={(e) => setRegDepartment(e.target.value)}
                helperText="Optional"
                fullWidth
              >
                <MenuItem value="">
                  <em>None</em>
                </MenuItem>
                {DEPARTMENTS.map((d) => (
                  <MenuItem key={d} value={d}>
                    {d}
                  </MenuItem>
                ))}
              </TextField>

              {registerMutation.isError && (
                <Alert severity="error">{apiErrorMessage(registerMutation.error)}</Alert>
              )}

              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={
                  registerMutation.isPending || !regEmail.trim() || !regFullName.trim()
                }
              >
                {registerMutation.isPending ? 'Creating account…' : 'Register & continue'}
              </Button>
              <Button
                variant="text"
                onClick={() => setShowRegister(false)}
                disabled={registerMutation.isPending}
              >
                Back to sign in
              </Button>
            </Stack>
          </Box>
        )}
      </Paper>
    </Container>
  );
}
