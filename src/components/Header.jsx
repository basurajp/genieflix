import React, { useEffect } from "react";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "../utils/firebase";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { addUser, removeUser } from "../rtk/userSlice"; // Assuming you have a removeUser action in your userSlice
import { API_OPTION } from "../utils/constant";
import { addNowPlayingMovies } from "../rtk/movieSlice";

const Header = () => {
  const navigate = useNavigate();
  const user = useSelector((store) => store.user);
  const dispatch = useDispatch();


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

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (user) {
        const { uid, email, displayName } = auth.currentUser;

        dispatch(addUser({ uid: uid, email: email, displayName: displayName }));
        navigate("/browse");
      } else {
        dispatch(removeUser());
        navigate("/");
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  return (
    <div className="absolute bg-gradient-to-b from-black px-6 lg:px-10 lg:pr-24 py-4 z-10  w-screen flex items-center justify-between">
      <img
        className="w-28 lg:w-40"
        src="https://i.ibb.co/fYn5BbH/png-transparent-netflix-streaming-media-television-show-logo-netflix-television-text-trademark-thumb.png "
        alt="logo img"
      />
      <div className="">
        {user && (
          <button
            onClick={handleSignOut}
            className="lg:px-2 lg:py-1 text-sm p-1 bg-red-600 text-white font-semibold rounded-lg"
          >
            Sign out
          </button>
        )}
      </div>
    </div>
  );
};

export default Header;
