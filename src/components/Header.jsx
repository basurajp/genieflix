import React from "react";
import { signOut } from "firebase/auth";
import { auth } from "../utils/firebase";
import { useNavigate } from "react-router-dom";

const Header = () => {
  const navigate = useNavigate();

  const handleSignOut = () => {
    signOut(auth)
      .then(() => {
        // Sign-out successful.
        navigate("/");
      })
      .catch((error) => {
        console.log(error);
      });
  };
  return (
    <div className="absolute bg-gradient-to-b from-black px-2 lg:px-10 lg:pr-24 py-4 z-10  w-screen flex items-center justify-between">
      <img
        className="w-32 lg:w-40"
        src="https://i.ibb.co/fYn5BbH/png-transparent-netflix-streaming-media-television-show-logo-netflix-television-text-trademark-thumb.png "
        alt="logo imgr"
      />
      <div className="">
        <button
          onClick={handleSignOut}
          className="px-2 py-1 bg-red-600 text-white font-semibold rounded-lg"
        >
          Sign out{" "}
        </button>
      </div>
    </div>
  );
};

export default Header;
