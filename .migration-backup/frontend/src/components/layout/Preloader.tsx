import React from 'react';
import './Preloader.css';

const Preloader: React.FC = () => (
  <div className="preloader">
    <div className="preloader-content">
      <div className="spinner"></div>
      <p>Loading Concierge...</p>
    </div>
  </div>
);

export default Preloader;