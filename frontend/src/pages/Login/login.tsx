import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaEnvelope, FaLock } from 'react-icons/fa';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { setAuthSession } from '../../services/authPermissions';
import { getDefaultRouteForPermissions } from '../../services/authPermissions';

import loginImage from '../../assets/images/login-image.jpg';
import logo from '../../assets/images/ubl-logo.png';
import { loginUser } from '../../services/authService';

const Login = () => {


    const [username, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState<{ username?: string; password?: string }>({});
    const navigate = useNavigate();


    useEffect(() => {
        const timer = setTimeout(() => {
            const usernameInput = document.querySelector('input[name="username"]') as HTMLInputElement;
            const passwordInput = document.querySelector('input[name="password"]') as HTMLInputElement;


            if (usernameInput?.value) setEmail(usernameInput.value);
            if (passwordInput?.value) setEmail(passwordInput.value);
            
        }, 500);
        return () => clearTimeout(timer);
    }, []);
    
    const validateField = (name: 'username' | 'password', value: string) => {
        let error = '';
        switch (name) {
            case 'username':
                if (!value) {
                    error = 'Username is required.';
                // } else if (!/\S+@\S+\.\S+/.test(value)) {
                //     error = 'Please enter a valid username address.';
                }
                break;
            case 'password':
                if (!value) {
                    error = 'Password is required.';
                }
                break;
            default:
                break;
        }
        setErrors((prevErrors) => ({ ...prevErrors, [name]: error }));
        return !error;
    };

    const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        
        // const isEmailValid = validateField('username', username);
    
        const form = e.currentTarget;
        const usernameValue = (form.elements.namedItem('username') as HTMLInputElement)?.value || username;
        const passwordValue = (form.elements.namedItem('password') as HTMLInputElement)?.value || password;

        const isPasswordValid = validateField('password', passwordValue);
        
        if ( isPasswordValid) {
            try {
                setIsSubmitting(true);
                const trimmedEmail = usernameValue.trim();
              
                const response = await loginUser({ username: trimmedEmail, password:passwordValue });
                

                if (response.access_token){
                    const permissions = response.permissions

                    setAuthSession(response.access_token, permissions);
                    toast.success('Login successful!', {
                        position: 'top-center',
                        autoClose: 1500,
                    });

                    setTimeout(() => {
                        navigate(getDefaultRouteForPermissions(permissions));
                    }, 2);
                
                    localStorage.setItem('token', response.access_token)
                    if (response.refresh_token) {
                        localStorage.setItem('refresh_token', response.refresh_token)
                    }
                    window.dispatchEvent(new Event('storage'));
                    toast.success('Login successful!', {
                        position: 'top-center',
                        autoClose: 1500,
                    });
                    
             
                    if (!permissions)
                    {
                        toast.error('No permissions found.', {
                            position: 'top-center',
                            autoClose: 3000,
                        });
                        setIsSubmitting(false)
                    }
                    // if (permissions.length > 1){
                    //     console.log(`IN PERMISSIONS GREATER THAN 1`)
                    //     setTimeout(() => {
                    //         navigate('/xml-generator');
                    //     }, 2);
                    // }
                    // else {
                    //     if ("CTR" in permissions){
                    //         setTimeout(() => {
                    //             navigate('/ctr-generator');
                    //         }, 2);
                    //     }
                    //     else if ("STR" in permissions){
                    //         setTimeout(() => {
                    //             navigate('/xml-generator');
                    //         }, 2);
                    //     }
                    // }
                } else {
                    toast.error('Invalid username or password.', {
                        position: 'top-center',
                        autoClose: 3000,
                    });
                    setIsSubmitting(false)
                }
            } catch (error) {
                // Show ONE generic message regardless of the failure reason.
                // Distinguishing "Invalid Credentials" (401) from "Not
                // Authorized" (403) told an attacker which usernames exist.
                const status = (error as { response?: { status?: number } }).response?.status;
                if (status === 429) {
                    toast.error('Too many attempts. Please wait and try again.', {
                        position: 'top-center',
                        autoClose: 3000,
                    });
                } else {
                    toast.error('Invalid username or password.', {
                        position: 'top-center',
                        autoClose: 3000,
                    });
                }
                setIsSubmitting(false)

            } finally {
                setIsSubmitting(false);
            }
        }
    };

    return (
        <div
            className="vh-100 d-flex align-items-center justify-content-center position-relative"
            style={{
                backgroundImage: `url(${loginImage})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
            }}
        >
            <div className="position-absolute top-0 start-0 w-100 h-100 bg-dark bg-opacity-50 z-1"></div>

            <div className="position-relative z-2 w-100 p-3" style={{ maxWidth: '420px' }}>
                <div
                    className="card border-0 shadow-lg p-4 p-sm-5 rounded-3"
                    style={{
                        background: 'rgba(255, 255, 255, 0.95)',
                        backdropFilter: 'blur(5px)',
                    }}
                >
                    <div className="text-center mb-4">
                        <img src={logo} alt="Company Logo" style={{ maxWidth: '150px' }} className="h-auto" />
                    </div>
                    <h2 className="text-center fw-bold mb-2">Welcome Back</h2>
                    <p className="text-center text-muted mb-4">Please enter your credentials to log in.</p>

                    <form onSubmit={handleLogin} noValidate>
                        <div className="mb-3">
                            <div className="position-relative">
                                <FaEnvelope className="position-absolute top-50 start-0 translate-middle-y ms-3 text-primary" />
                                <input
                                    name = 'username'
                                    type="username"
                                    className={`form-control ps-5 py-2 ${errors.username ? 'is-invalid' : ''}`}
                                    placeholder="Username"
                                    value={username}
                                    onChange={(e) => {
                                        setEmail(e.target.value);
                                        if (errors.username) validateField('username', e.target.value);
                                    }}
                                    onBlur={() => validateField('username', username)}
                                    required
                                />
                            </div>
                            {errors.username && <div className="invalid-feedback d-block">{errors.username}</div>}
                        </div>

                        <div className="mb-4">
                            <div className="position-relative">
                                <FaLock className="position-absolute top-50 start-0 translate-middle-y ms-3 text-primary" />
                                <input
                                    name='password'
                                    type="password"
                                    className={`form-control ps-5 py-2 ${errors.password ? 'is-invalid' : ''}`}
                                    placeholder="Password"
                                    value={password}
                                    onChange={(e) => {
                                        setPassword(e.target.value);
                                        if (errors.password) validateField('password', e.target.value);
                                    }}
                                    onBlur={() => validateField('password', password)}
                                    required
                                />
                            </div>
                            {errors.password && <div className="invalid-feedback d-block">{errors.password}</div>}
                        </div>
                        <button
                            type="submit"
                            className="btn btn-primary w-100 fw-bold py-2"
                            disabled={!username || !password || isSubmitting}
                        >
                            {isSubmitting ? 'LOGGING IN...' : 'LOG IN'}
                        </button>
                    </form>
                </div>
            </div>
            <ToastContainer />
        </div>
    );
};

export default Login;
