import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { useState, useEffect } from 'react';
import MainLayout from './MainLayout';
import Login from './pages/Login/login';
import NotFound from './pages/NotFound/notfound';
// import Upload from './pages/Upload/upload';
import XmlGenerator from './pages/XmlGenerator/xml-generator';
import CtrGenerator from './pages/CTRGenerator/ctr-generator';
import Rcoa from './pages/Rcoa/rcoa';
import PermissionRoute from './components/Auth/PermissionRoute';
// import { type UserRole } from './types/auth';

// const getDefaultRouteForRole = (role: UserRole | null) => {
//   if (role === 'superAdmin' || role === 'standard') {
//     return '/xml-generator';
//   }
//   return '/login';
// };

// type RequireRoleProps = {
//   allowedRoles: UserRole[];
// };

// const RequireRole = ({ allowedRoles }: RequireRoleProps) => {
//   const role = (localStorage.getItem('userRole') as UserRole | null) ?? null;

//   if (!role || !allowedRoles.includes(role)) {
//     return <Navigate to={getDefaultRouteForRole(role)} replace />;
//   }

//   return <Outlet />;
// };

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));
  // const token = localStorage.getItem("token");
  useEffect(() => {
    const handleStorage = () => {
      setToken(localStorage.getItem("token"));
    };
    window.addEventListener('storage', handleStorage);

    const interval = setInterval(() => {
      const current = localStorage.getItem("token");
      if (current !== token){
        setToken(current);
      }
    }, 500);

    return () => {
      window.removeEventListener('storage', handleStorage);
      clearInterval(interval);
    };
  }, [token]);

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/login" element={<Login />} />

        <Route element={<MainLayout />}>
          <Route
            path="/rcoa"
            element={
              <PermissionRoute permission="RCOA">
                <Rcoa />
              </PermissionRoute>
            }
          />
          
          <Route
            path="/xml-generator"
            element={
              <PermissionRoute permission="STR">
                <XmlGenerator />
              </PermissionRoute>
            }
          />
          <Route
            path="/ctr-generator"
            element={
              <PermissionRoute permission="CTR">
                <CtrGenerator />
              </PermissionRoute>
            }
          />
        </Route>
        
        

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Router>
  );
}

//   return (
//     <Router>
//       <Routes>

//         <Route path="/" element={<Login />} />
//         <Route path="/login" element={<Login />} />

//         {/* Routes with Navbar and Layout */}

//         {/* <Route element={<RequireRole allowedRoles={['standard', 'superAdmin']} />}> */}
//         <Route element={<MainLayout />}>
//           <Route
//             path="/xml-generator"
//             element={
//               <PermissionRoute permission="STR">
//                 <XmlGenerator />
//                </PermissionRoute>
//             }
//           />
//           <Route
//             path="/ctr-generator"
//             element={
//               <PermissionRoute permission="CTR">
//                 <CtrGenerator />
//               </PermissionRoute>
//             }
//           />
//         </Route>
//         {/* <Route element={<RequireRole allowedRoles={['superAdmin']} />}>
//           <Route element={<MainLayout />}>
//             <Route
//               path="/upload"
//               element={<Upload />}
//             />
//           </Route>
//         </Route> */}

//         <Route path="*" element={<NotFound />} />

//       </Routes>
//     </Router>
//   );
// }

export default App;
