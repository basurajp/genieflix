import React, { useState } from "react";
import Header from "./Header";

const Login = () => {
  const [issSingnin, setissSingnin] = useState(true);

  const handleSignupSignIn = () => {
    setissSingnin(!issSingnin);
  };

  return (
    <div className="  ">
      <Header />
      <div className="absolute">
        <img
          className="h-[70vh] object-cover lg:h-full"
          src="https://assets.nflxext.com/ffe/siteui/vlv3/16006346-87f9-4226-bc25-a1fb346a2b0c/9662d0fd-0547-4665-b887-771617268815/IN-en-20240115-popsignuptwoweeks-perspective_alpha_website_medium.jpg"
          alt="bgimge"
        />
      </div>
      <form className="p-10 bg-black absolute lg:mt-20 lg:h-auto   m-auto right-0 left-0 h-full  bg-opacity-90 lg:w-3/12 text-white rounded-lg">
        <h1 className="font-bold text-3xl py-4 mt-6">
          {issSingnin ? "Sign In" : "Sign up"}{" "}
        </h1>
        {!issSingnin && (
          <input
            type="text"
            placeholder="email"
            className="my-2 py-2 px-3 w-full bg-gray-700 rounded-md  "
          />
        )}
        <input
          type="text"
          placeholder="email"
          className="my-2 py-2 px-3 w-full bg-gray-700 rounded-md  "
        />
        <input
          type="password"
          className="my-2 py-2 w-full bg-gray-700  px-3 rounded-md"
          placeholder="password"
        />
        <button className="px-4 py-3 my-2 w-full bg-red-700 rounded-lg ">
          {issSingnin ? "Sign in " : " Sign up  "}
        </button>
        <h2 onClick={handleSignupSignIn} className="text-sm py-2">
          {issSingnin ? "New to NetFlix" : "already a user"}{" "}
          <span className="font-semibold ml-2 cursor-pointer">
            {issSingnin ? "sigup now" : "sign in "}
          </span>{" "}
        </h2>
      </form>
    </div>
  );
};

export default Login;
