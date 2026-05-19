import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';

import MainLayout from './MainLayout';
import HomePage from './pages/Home/home';
import Login from './pages/Login/login';
import Chat from './pages/Chat/chat';
import NotFound from './pages/NotFound/notfound';
// import Upload from './pages/Upload/upload';
import XmlGenerator from './pages/XmlGenerator/xml-generator';
import { type UserRole } from './types/auth';

const getDefaultRouteForRole = (role: UserRole | null) => {
  if (role === 'superAdmin' || role === 'standard') {
    return '/xml-generator';
  }
  return '/login';
};

type RequireRoleProps = {
  allowedRoles: UserRole[];
};

const RequireRole = ({ allowedRoles }: RequireRoleProps) => {
  const role = (localStorage.getItem('userRole') as UserRole | null) ?? null;

  if (!role || !allowedRoles.includes(role)) {
    return <Navigate to={getDefaultRouteForRole(role)} replace />;
  }

  return <Outlet />;
};

function App() {
  const [userInput, setUserInput] = useState('');

  return (
    <Router>
      <Routes>

        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />

        {/* Routes with Navbar and Layout */}
        <Route element={<RequireRole allowedRoles={['standard', 'superAdmin']} />}>
          <Route element={<MainLayout />}>
            <Route
              path="/home"
              element={<HomePage setUserInput={setUserInput} />}
            />
            <Route
              path="/conversation"
              element={<Chat userInput={userInput} />}
            />
            <Route
              path="/xml-generator"
              element={<XmlGenerator />}
            />
          </Route>
        </Route>

        {/* <Route element={<RequireRole allowedRoles={['superAdmin']} />}>
          <Route element={<MainLayout />}>
            <Route
              path="/upload"
              element={<Upload />}
            />
          </Route>
        </Route> */}

        <Route path="*" element={<NotFound />} />

      </Routes>
    </Router>
  );
}

export default App;
