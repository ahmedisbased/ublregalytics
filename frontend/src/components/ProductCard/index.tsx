interface ProductCardProps {
    title: string;
    description: string;
    icon: React.ReactNode;
}

const ProductCard: React.FC<ProductCardProps> = ({ title, description, icon }) => {
    return (
        <div className="card border border-secondary rounded p-3 shadow-sm">
            <div className="bg-primary d-flex align-items-center justify-content-center rounded-circle mb-2 text-white" style={{ width: "40px", height: "40px" }}>
                {icon}
            </div>
            <h5 className="fw-bold py-3">{title}</h5>
            <p className="text-muted">{description}</p>
        </div>
    );
};

export default ProductCard;
