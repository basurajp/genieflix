import React, { useEffect } from "react";
import { onAuthStateChanged, signOut } from "firebase/auth";
import { auth } from "../utils/firebase";
import { useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { addUser, removeUser } from "../rtk/userSlice"; // Assuming you have a removeUser action in your userSlice
import { API_OPTION, SUPPORTED_LANGUAGES } from "../utils/constant";
import { addNowPlayingMovies } from "../rtk/movieSlice";
import { toggleGptSearchView } from "../rtk/gptSlice";
import { changeLanguage } from "../rtk/configSlice";

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

  const handleGptSearchClick = () => {
    dispatch(toggleGptSearchView());
  };

  const handleLanguageChange = (e)=>{
    dispatch(changeLanguage(e.target.value))
  }

  return (
    <div className="absolute bg-gradient-to-b from-black px-6 lg:px-10 lg:pr-24 py-4 z-10  w-screen flex items-center justify-between">
      <img
        className="w-28 lg:w-40"
        src="https://i.ibb.co/fYn5BbH/png-transparent-netflix-streaming-media-television-show-logo-netflix-television-text-trademark-thumb.png "
        alt="logo img"
      />
      <div className="">
        {user && (
          <>
            <select onChange={handleLanguageChange} className="bg-gray-600 py-1 text-white mr-1 rounded-lg">
              {SUPPORTED_LANGUAGES.map((langData, index) => (
                <option key={langData.identifier} value={langData.identifier}>{langData.name}</option>
              ))}
            </select>
            <button
              onClick={handleGptSearchClick}
              className="py-1 mr-2 px-2 text-sm bg-purple-400 text-white rounded-lg"
            >
              Gpt Search{" "}
            </button>

            <button
              onClick={handleSignOut}
              className="lg:px-2 lg:py-1 text-sm p-1 bg-red-600 text-white font-semibold rounded-lg"
            >
              Sign out
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default Header;
