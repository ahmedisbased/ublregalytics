import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaEnvelope, FaLock } from 'react-icons/fa';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import loginImage from '../../assets/images/login-image.jpg';
import logo from '../../assets/images/ubl-logo.png';
import { type UserRole } from '../../types/auth';
import { loginUser } from '../../services/authService';

const Login = () => {
    const extractUserName = (address: string) => {
        const localPart = address.split('@')[0] ?? '';
        return localPart.trim();
    };

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
    const navigate = useNavigate();

    const validateField = (name: 'email' | 'password', value: string) => {
        let error = '';
        switch (name) {
            case 'email':
                if (!value) {
                    error = 'Email address is required.';
                } else if (!/\S+@\S+\.\S+/.test(value)) {
                    error = 'Please enter a valid email address.';
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
        const isEmailValid = validateField('email', email);
        const isPasswordValid = validateField('password', password);

        if (isEmailValid && isPasswordValid) {

            try {
                setIsSubmitting(true);
                const trimmedEmail = email.trim();
                const response = await loginUser({ email: trimmedEmail, password });

                if (response.success && response.role) {
                    const normalizedRole: UserRole = response.role === 'ADMIN' ? 'superAdmin' : 'standard';
                    const userName = extractUserName(trimmedEmail);

                    localStorage.setItem('userEmail', trimmedEmail);
                    if (userName) {
                        localStorage.setItem('userName', userName);
                    } else {
                        localStorage.removeItem('userName');
                    }
                    localStorage.setItem('userRole', normalizedRole);

                    toast.success('Login successful!', {
                        position: 'top-center',
                        autoClose: 1500,
                    });

                    setTimeout(() => {
                        navigate('/xml-generator');
                    }, 2000);
                } else {
                    toast.error('Invalid email or password.', {
                        position: 'top-center',
                        autoClose: 3000,
                    });
                }
            } catch (error) {
                toast.error('Unable to login right now. Please try again.', {
                    position: 'top-center',
                    autoClose: 3000,
                });
                console.log(error)
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
                                    type="email"
                                    className={`form-control ps-5 py-2 ${errors.email ? 'is-invalid' : ''}`}
                                    placeholder="Email Address"
                                    value={email}
                                    onChange={(e) => {
                                        setEmail(e.target.value);
                                        if (errors.email) validateField('email', e.target.value);
                                    }}
                                    onBlur={() => validateField('email', email)}
                                    required
                                />
                            </div>
                            {errors.email && <div className="invalid-feedback d-block">{errors.email}</div>}
                        </div>

                        <div className="mb-4">
                            <div className="position-relative">
                                <FaLock className="position-absolute top-50 start-0 translate-middle-y ms-3 text-primary" />
                                <input
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
                            disabled={!email || !password || isSubmitting}
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
