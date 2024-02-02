import React from "react";
import { BrowserRouter } from "react-router-dom"; // Import BrowserRouter
import Body from "./components/Body";
import { Provider } from "react-redux";
import store from "./rtk/store";

const App = () => {
  return (
    <div className="w-screen min-h-screen">
      <Provider store={store}>
      
          <Body />
        
      </Provider>
    </div>
  );
};

export default App;
