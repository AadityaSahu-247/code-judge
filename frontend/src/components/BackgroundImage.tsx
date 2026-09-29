import React from 'react';

export const BackgroundImage: React.FC = () => {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none bg-[#0a0a0a]">
      <img
        src="/custom-bg.png"
        alt=""
        className="absolute inset-0 w-full h-full object-cover z-10"
      />
      {/* Dark vignette overlay for contrast */}
      <div
        className="absolute inset-0 z-20"
        style={{
          background: 'radial-gradient(circle at center, rgba(10,10,10,0.30) 0%, rgba(10,10,10,0.70) 100%)',
        }}
      />
    </div>
  );
};
