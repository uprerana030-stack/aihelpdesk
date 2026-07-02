import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
} from '@mui/material';
import ConfirmationNumberOutlinedIcon from '@mui/icons-material/ConfirmationNumberOutlined';
import SupportAgentOutlinedIcon from '@mui/icons-material/SupportAgentOutlined';
import InsightsOutlinedIcon from '@mui/icons-material/InsightsOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import StorageOutlinedIcon from '@mui/icons-material/StorageOutlined';
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined';
import { useLocation, useNavigate } from 'react-router-dom';
import { AGENT_ROLES, KB_WRITER_ROLES, MANAGER_ROLES, useUser } from '../context/UserContext';
import { COLORS } from '../theme';

const DRAWER_WIDTH = 240;

// Roles that may see the Knowledge Base: agents, managers, and KB writers — but NOT plain employees.
const KB_ROLES = Array.from(new Set([...AGENT_ROLES, ...MANAGER_ROLES, ...KB_WRITER_ROLES]));

// The manual team = agents + managers (no plain employees, no KB-only admins).
const MANUAL_TEAM_ROLES = Array.from(new Set([...AGENT_ROLES, ...MANAGER_ROLES]));

const NAV_ITEMS = [
  { label: 'My Tickets', path: '/employee', icon: <ConfirmationNumberOutlinedIcon />, roles: ['employee'] },
  { label: 'Agent Queue', path: '/agent', icon: <SupportAgentOutlinedIcon />, roles: AGENT_ROLES },
  { label: 'Escalations', path: '/escalations', icon: <ReportProblemOutlinedIcon />, roles: MANUAL_TEAM_ROLES },
  { label: 'Analytics', path: '/manager', icon: <InsightsOutlinedIcon />, roles: MANAGER_ROLES },
  { label: 'Database', path: '/database', icon: <StorageOutlinedIcon />, roles: MANAGER_ROLES },
  { label: 'Knowledge Base', path: '/kb', icon: <MenuBookOutlinedIcon />, roles: KB_ROLES },
];

export default function Sidebar() {
  const { role } = useUser();
  const navigate = useNavigate();
  const location = useLocation();

  const visible = NAV_ITEMS.filter(
    (item) => !item.roles || (role != null && item.roles.includes(role)),
  );

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: COLORS.sidebarBg,
          color: '#CFE3DE',
          borderRight: 'none',
        },
      }}
    >
      <Toolbar />
      <List>
        {visible.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => navigate(item.path)}
            sx={{
              color: '#CFE3DE',
              '& .MuiListItemIcon-root': { color: 'inherit', minWidth: 40 },
              '&.Mui-selected': {
                bgcolor: 'rgba(23,165,137,0.15)',
                borderLeft: `3px solid ${COLORS.sidebarActive}`,
                color: '#FFFFFF',
              },
              '&.Mui-selected .MuiListItemIcon-root': { color: COLORS.sidebarActive },
              '&.Mui-selected:hover': { bgcolor: 'rgba(23,165,137,0.22)' },
              '&:hover': { bgcolor: 'rgba(255,255,255,0.06)' },
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </Drawer>
  );
}
