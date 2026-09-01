import { Link } from 'react-router-dom';
import { FaHome } from 'react-icons/fa';
import './notfound.scss';

const NotFound = () => {
    return (
        <div className="not-found-container">
            <div className="not-found-content text-center">
                <h1 className="display-1">404</h1>
                <h2 className="mb-3">Page Not Found</h2>
                <p className="lead text-muted mb-4">
                    Sorry, the page you are looking for does not exist. It might have been moved or deleted.
                </p>
                <Link to="/home" className="btn btn-primary btn-lg">
                    <FaHome className="me-2" />
                    Go to Homepage
                </Link>
            </div>
        </div>
    );
};

export default NotFound;
