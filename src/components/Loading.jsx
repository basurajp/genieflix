import React from 'react';
import ReactLoading from 'react-loading';

const Loading = () => (
  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
    <h1>Loading...</h1>
    <ReactLoading type="spin" color="white" height={50} width={50} />
  </div>
);

export default Loading;
